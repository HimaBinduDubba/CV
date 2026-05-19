import unittest
from pathlib import Path

from src.api.models import APIResponse
from dimension_extractor.extractor import DimensionExtractor
from dimension_extractor.models import (
    AssemblyResult,
    Datum,
    Dimension,
    GDTCallout,
    GDTSymbol,
    MaterialCondition,
    RelationshipType,
    Tolerance,
    ToleranceType,
)
from dimension_extractor.scoring import ConfidenceScorer
from dimension_extractor.validation import DataValidator


class FakePDFConverter:
    def convert(self, pdf_path: Path):
        return ["page-image"]


class FakeRouter:
    def __init__(self, raw_text: str):
        self.raw_text = raw_text

    def extract_from_image(self, prompt: str, images):
        return APIResponse(provider="test", raw_response={"text": self.raw_text}, confidence=0.91)


class Developer3CoreTests(unittest.TestCase):
    def test_data_model_instantiation_and_enum_values(self):
        tolerance = Tolerance(ToleranceType.BILATERAL, plus=0.1, minus=0.1, unit="mm")
        dimension = Dimension(
            id="D1",
            nominal_value=10.0,
            unit="mm",
            measured_feature="bolt protrusion height",
            part_id="bolt",
            tolerance=tolerance,
        )

        self.assertAlmostEqual(dimension.tolerance.max_deviation(dimension.nominal_value), 0.1)
        self.assertEqual(ToleranceType.UNILATERAL.value, "unilateral")
        self.assertEqual(RelationshipType.BOLTED.value, "bolted")

    def test_validator_flags_tolerance_larger_than_nominal_and_missing_tolerance(self):
        validator = DataValidator()
        bad = Dimension(
            id="D2",
            nominal_value=1.0,
            unit="mm",
            measured_feature="thin wall",
            part_id="case",
            tolerance=Tolerance(ToleranceType.BILATERAL, plus=2.0, minus=2.0),
        )
        missing = Dimension(id="D3", nominal_value=5.0, unit="mm", measured_feature="height", part_id="case")

        bad_result = validator.validate_dimension(bad)
        missing_result = validator.validate_dimension(missing)

        self.assertFalse(bad_result.is_valid)
        self.assertIn("smaller than nominal", " ".join(bad_result.errors))
        self.assertTrue(missing_result.is_valid)
        self.assertIn("missing explicit tolerance", " ".join(missing_result.warnings))

    def test_validator_checks_datum_references_and_unit_consistency(self):
        validator = DataValidator()
        callout = GDTCallout(
            id="G1",
            symbol_type=GDTSymbol.POSITION,
            tolerance_zone=0.2,
            material_condition=None,
            datum_references=["A", "C"],
            controlled_feature="hole",
            part_id="case",
        )
        dimensions = [
            Dimension(id="D1", nominal_value=1.0, unit="mm", measured_feature="height", part_id="case"),
            Dimension(id="D2", nominal_value=2.0, unit="inch", measured_feature="width", part_id="case"),
        ]

        datum_result = validator.validate_datum_references([callout], [Datum("A", "A", "face", "case")])
        unit_result = validator.validate_units(dimensions)

        self.assertFalse(datum_result.is_valid)
        self.assertIn("undefined datum C", " ".join(datum_result.errors))
        self.assertTrue(unit_result.is_valid)
        self.assertTrue(unit_result.warnings)

    def test_confidence_scorer_clamps_and_reduces_for_validation_failure(self):
        scorer = ConfidenceScorer()
        dimension = Dimension(id="D1", nominal_value=10.0, unit="mm", measured_feature="height", part_id="case")
        valid_score = scorer.score_dimension(dimension, 2.5, DataValidator().validate_dimension(dimension))
        failed_score = scorer.score_dimension(
            dimension,
            0.9,
            DataValidator().validate_dimension(
                Dimension(id="D2", nominal_value=-1.0, unit="mm", measured_feature="height", part_id="case")
            ),
        )

        self.assertGreaterEqual(valid_score, 0.0)
        self.assertLessEqual(valid_score, 1.0)
        self.assertLess(failed_score, valid_score)
        self.assertTrue(dimension.requires_human_review)

    def test_parse_llm_response_and_process_pdf(self):
        raw = """
        ```json
        {
          "dimensions": [
            {
              "id": "D1",
              "nominal_value": 12.5,
              "unit": "mm",
              "measured_feature": "bolt protrusion height",
              "part_id": "BOLT",
              "tolerance": {"type": "bilateral", "plus": 0.1, "minus": 0.1, "unit": "mm"},
              "confidence_score": 0.95
            }
          ],
          "gdt_callouts": [
            {
              "id": "G1",
              "symbol_type": "position",
              "tolerance_zone": 0.2,
              "datum_references": ["A"],
              "controlled_feature": "bolt hole",
              "part_id": "BOLT",
              "confidence_score": 0.88
            }
          ],
          "datums": [{"id": "DA", "label": "A", "feature_description": "mounting face", "part_id": "BOLT"}],
          "material_specs": [{"material_type": "steel", "material_grade": "8.8", "part_id": "BOLT"}]
        }
        ```
        """
        extractor = DimensionExtractor(api_router=FakeRouter(raw), pdf_converter=FakePDFConverter())

        result = extractor.process_pdf(Path("bolt.pdf"))

        self.assertEqual(result.part_id, "BOLT")
        self.assertEqual(len(result.dimensions), 1)
        self.assertEqual(result.dimensions[0].unit, "mm")
        self.assertTrue(result.validation.is_valid)
        self.assertGreater(result.confidence_score, 0.7)

    def test_parse_gemini_material_condition_variants(self):
        raw = """
        {
          "dimensions": [],
          "gdt_callouts": [
            {
              "id": "G1",
              "characteristic": "Position",
              "tolerance_value": 0.01,
              "material_condition": "RFS",
              "datums": ["A"],
              "feature": "bolt hole"
            },
            {
              "id": "G2",
              "characteristic": "Position",
              "tolerance_value": 0.02,
              "material_condition": "IN FREE STATE",
              "datums": ["A"],
              "feature": "free-state profile"
            }
          ]
        }
        """
        extractor = DimensionExtractor()

        callouts = extractor._parse_gdt_response(raw)

        self.assertEqual(callouts[0].material_condition, MaterialCondition.RFS)
        self.assertIsNone(callouts[1].material_condition)

    def test_parse_drawing_links_accepts_empty_list(self):
        extractor = DimensionExtractor()

        self.assertEqual(extractor._parse_drawing_links([]), {})

    def test_process_batch_isolates_failures(self):
        extractor = DimensionExtractor(api_router=FakeRouter("{}"), pdf_converter=FakePDFConverter())

        result = extractor.process_batch([Path("ok.pdf"), Path("bad.txt")])

        self.assertEqual(len(result.successful), 1)
        self.assertIn(Path("bad.txt"), result.failed)
        self.assertAlmostEqual(result.progress_percent, 100.0)

    def test_identify_dimensional_chain_calculates_worst_case(self):
        extraction = DimensionExtractor()
        part_result = type("Part", (), {})()
        part_result.confidence_score = 0.9
        part_result.dimensions = [
            Dimension(
                id="D1",
                nominal_value=10.0,
                unit="mm",
                measured_feature="bolt protrusion height",
                part_id="bolt",
                tolerance=Tolerance(ToleranceType.BILATERAL, plus=0.2, minus=0.2),
            ),
            Dimension(
                id="D2",
                nominal_value=2.0,
                unit="mm",
                measured_feature="recess depth",
                part_id="case",
                tolerance=Tolerance(ToleranceType.BILATERAL, plus=0.1, minus=0.1),
            ),
        ]
        assembly = AssemblyResult(source_file=Path("assembly.png"), confidence_score=0.8)

        chains = extraction.identify_dimensional_chains([part_result], assembly)

        self.assertEqual(len(chains), 1)
        self.assertAlmostEqual(chains[0].total_nominal, 8.0)
        self.assertAlmostEqual(chains[0].worst_case_max, 8.3)
        self.assertAlmostEqual(chains[0].worst_case_min, 7.7)


if __name__ == "__main__":
    unittest.main()
