"""Dimension extraction orchestration for Developer 3 responsibilities."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Protocol

from PIL import Image

from .models import (
    AssemblyRelationship,
    AssemblyResult,
    BatchResult,
    ChainLink,
    Datum,
    Dimension,
    DimensionalChain,
    ExtractionResult,
    GDTCallout,
    GDTSymbol,
    MaterialCondition,
    MaterialSpec,
    RelationshipType,
    Tolerance,
    ToleranceType,
    ValidationResult,
)
from .scoring import ConfidenceScorer
from .validation import DataValidator


class APIRouterLike(Protocol):
    def extract_from_image(self, prompt: str, images: list[Any]) -> Any:
        ...


class PDFConverterLike(Protocol):
    def convert(self, pdf_path: Path) -> list[Any]:
        ...


class DimensionExtractor:
    """Main orchestrator for parsing, validation, scoring, and chain discovery."""

    def __init__(
        self,
        config: Any | None = None,
        api_router: APIRouterLike | None = None,
        validator: DataValidator | None = None,
        confidence_scorer: ConfidenceScorer | None = None,
        pdf_converter: PDFConverterLike | None = None,
        cache: Any | None = None,
    ) -> None:
        self.config = config
        self.api_router = api_router
        self.validator = validator or DataValidator()
        self.confidence_scorer = confidence_scorer or ConfidenceScorer()
        self.pdf_converter = pdf_converter
        self.cache = cache

    def process_pdf(self, pdf_path: Path) -> ExtractionResult:
        if self.pdf_converter is None:
            raise RuntimeError("PDF converter dependency is required to process PDFs")
        if self.api_router is None:
            raise RuntimeError("API router dependency is required to process PDFs")

        pages = self.pdf_converter.convert(Path(pdf_path))
        raw_responses: list[str] = []
        dimensions: list[Dimension] = []
        gdt_callouts: list[GDTCallout] = []
        datums: list[Datum] = []
        material_specs: list[MaterialSpec] = []
        prompt = self._build_dimension_prompt(Path(pdf_path).name)

        for page in pages:
            response = self._call_api_router(prompt, [page])
            raw_text = self._response_text(response)
            raw_responses.append(raw_text)
            dimensions.extend(self._parse_dimension_response(raw_text))
            gdt_callouts.extend(self._parse_gdt_response(raw_text))
            datums.extend(self._parse_datum_response(raw_text))
            material_specs.extend(self._parse_material_response(raw_text))

        part_id = self._infer_part_id(pdf_path, dimensions, material_specs)
        validation = self._validate_part(dimensions, gdt_callouts, datums)
        for dimension in dimensions:
            dimension_validation = self.validator.validate_dimension(dimension)
            self.confidence_scorer.score_dimension(dimension, dimension.confidence_score, dimension_validation)

        result = ExtractionResult(
            source_file=Path(pdf_path),
            part_id=part_id,
            dimensions=dimensions,
            gdt_callouts=gdt_callouts,
            datums=datums,
            material_specs=material_specs,
            validation=validation,
            raw_responses=raw_responses,
        )
        self.confidence_scorer.score_extraction_result(result)
        return result

    def process_assembly_diagram(self, png_path: Path) -> AssemblyResult:
        if self.api_router is None:
            raise RuntimeError("API router dependency is required to process assembly diagrams")
        with Image.open(png_path) as image:
            response = self._call_api_router(self._build_assembly_prompt(), [image.copy()])
        raw_text = self._response_text(response)
        payload = self._extract_json_object(raw_text)
        relationships = self._parse_assembly_relationships(payload)
        part_ids = list(dict.fromkeys(payload.get("part_ids", []) + [p for r in relationships for p in (r.part1_id, r.part2_id)]))
        drawing_links = self._parse_drawing_links(payload.get("drawing_links", {}))
        scores = [relationship.confidence_score for relationship in relationships] or [self._response_confidence(response)]
        return AssemblyResult(
            source_file=Path(png_path),
            part_ids=part_ids,
            relationships=relationships,
            drawing_links=drawing_links,
            confidence_score=sum(scores) / len(scores),
            raw_response=raw_text,
        )

    def process_batch(self, file_paths: list[Path]) -> BatchResult:
        result = BatchResult(total_files=len(file_paths))
        for file_path in file_paths:
            path = Path(file_path)
            try:
                if path.suffix.lower() == ".png":
                    result.successful.append(self.process_assembly_diagram(path))
                elif path.suffix.lower() == ".pdf":
                    result.successful.append(self.process_pdf(path))
                else:
                    raise ValueError(f"Unsupported file type: {path.suffix}")
            except Exception as exc:  # Keep batch processing moving after isolated failures.
                result.failed[path] = str(exc)
        return result

    def identify_dimensional_chains(
        self,
        parts: list[ExtractionResult],
        assembly: AssemblyResult,
    ) -> list[DimensionalChain]:
        candidate_dimensions = [
            dimension
            for part in parts
            for dimension in part.dimensions
            if self._is_chain_candidate(dimension)
        ]
        if not candidate_dimensions:
            return []

        ranked = sorted(candidate_dimensions, key=lambda dimension: abs(dimension.nominal_value), reverse=True)
        links = [
            ChainLink(
                dimension_id=dimension.id,
                contribution_sign=self._contribution_sign(dimension, assembly),
                contribution_rank=index + 1,
            )
            for index, dimension in enumerate(ranked)
        ]

        dimension_by_id = {dimension.id: dimension for dimension in ranked}
        total_nominal = sum(dimension_by_id[link.dimension_id].nominal_value * link.contribution_sign for link in links)
        worst_case_max = 0.0
        worst_case_min = 0.0
        for link in links:
            dimension = dimension_by_id[link.dimension_id]
            deviation = dimension.tolerance.max_deviation(dimension.nominal_value) if dimension.tolerance else 0.0
            signed_nominal = dimension.nominal_value * link.contribution_sign
            worst_case_max += signed_nominal + deviation
            worst_case_min += signed_nominal - deviation

        return [
            DimensionalChain(
                chain_id="bolt_protrusion_depth_primary",
                target_measurement="bolt_protrusion_depth",
                contributing_dimensions=links,
                total_nominal=total_nominal,
                worst_case_max=worst_case_max,
                worst_case_min=worst_case_min,
                confidence_score=min([part.confidence_score for part in parts] + [assembly.confidence_score]),
            )
        ]

    def _build_dimension_prompt(self, drawing_name: str = "drawing") -> str:
        return (
            "Extract all nominal dimensions, tolerances, GD&T callouts, datums, and material specifications "
            f"from engineering drawing {drawing_name}. Return only JSON with keys dimensions, gdt_callouts, "
            "datums, and material_specs. Preserve source units exactly. Include confidence_score for every item. "
            "For tolerances use type values bilateral, unilateral, limit, or missing. Example dimension: "
            '{"id":"D1","nominal_value":12.5,"unit":"mm","measured_feature":"boss height","part_id":"PART-A",'
            '"tolerance":{"type":"bilateral","plus":0.1,"minus":0.1,"unit":"mm"},"confidence_score":0.92}.'
        )

    def _build_assembly_prompt(self) -> str:
        return (
            "Extract part identifiers, drawing file links, mating surfaces, and assembly relationships from this PNG. "
            "Return only JSON with keys part_ids, drawing_links, and relationships. Relationship type must be one of "
            "bolted, pressed, welded, adhesive, contact, threaded, or clearance."
        )

    def _call_api_router(self, prompt: str, images: list[Any]) -> Any:
        """Call the Dev 2 router while keeping old test doubles usable."""
        try:
            return self.api_router.extract_from_image(prompt, images)
        except TypeError:
            if len(images) != 1:
                raise
            return self.api_router.extract_from_image(images[0], prompt)

    @staticmethod
    def _response_text(response: Any) -> str:
        if hasattr(response, "raw_text"):
            return str(response.raw_text)
        structured_data = getattr(response, "structured_data", None)
        if structured_data is not None:
            return json.dumps(structured_data)
        raw_response = getattr(response, "raw_response", None)
        if isinstance(raw_response, dict):
            text = raw_response.get("text")
            if isinstance(text, str):
                return text
            return json.dumps(raw_response)
        if isinstance(raw_response, str):
            return raw_response
        raise ValueError("API response did not contain parseable text or structured data")

    @staticmethod
    def _response_confidence(response: Any) -> float:
        if hasattr(response, "confidence_score"):
            return float(response.confidence_score)
        return float(getattr(response, "confidence", 0.0))

    def _parse_dimension_response(self, raw_text: str) -> list[Dimension]:
        payload = self._extract_json_object(raw_text)
        dimensions: list[Dimension] = []
        for item in payload.get("dimensions", []):
            tolerance_data = item.get("tolerance")
            nominal_value = self._dimension_nominal(item, tolerance_data)
            if nominal_value is None:
                continue
            dimensions.append(
                Dimension(
                    id=str(item.get("id", f"D{len(dimensions) + 1}")),
                    nominal_value=nominal_value,
                    unit=str(item.get("unit") or (tolerance_data or {}).get("unit") or ""),
                    measured_feature=str(item.get("measured_feature", "")),
                    part_id=str(item.get("part_id") or ""),
                    tolerance=self._parse_tolerance_response(tolerance_data) if tolerance_data else None,
                    source_page=item.get("source_page"),
                    source_zone=item.get("source_zone"),
                    drawing_number=item.get("drawing_number"),
                    datum_references=[str(value) for value in item.get("datum_references", [])],
                    confidence_score=float(item.get("confidence_score", 0.5)),
                    context=dict(item.get("context", {})),
                )
            )
        return dimensions

    def _parse_tolerance_response(self, tolerance_data: dict[str, Any] | str | None) -> Tolerance | None:
        if tolerance_data is None:
            return None
        if isinstance(tolerance_data, str):
            tolerance_data = self._extract_json_object(tolerance_data)
        tolerance_type = ToleranceType(str(tolerance_data.get("type", tolerance_data.get("tolerance_type", "missing"))))
        return Tolerance(
            tolerance_type=tolerance_type,
            plus=self._optional_float(tolerance_data.get("plus")),
            minus=self._optional_float(tolerance_data.get("minus")),
            lower_limit=self._optional_float(tolerance_data.get("lower_limit", tolerance_data.get("min"))),
            upper_limit=self._optional_float(tolerance_data.get("upper_limit", tolerance_data.get("max"))),
            unit=tolerance_data.get("unit"),
            confidence_score=float(tolerance_data.get("confidence_score", 1.0)),
        )

    def _parse_gdt_response(self, raw_text: str) -> list[GDTCallout]:
        payload = self._extract_json_object(raw_text)
        callouts: list[GDTCallout] = []
        for item in payload.get("gdt_callouts", []):
            symbol_value = item.get("symbol_type") or item.get("characteristic") or item.get("type")
            tolerance_zone = self._optional_float(item.get("tolerance_zone", item.get("tolerance_value")))
            if not symbol_value or tolerance_zone is None:
                continue
            controlled_feature = (
                item.get("controlled_feature")
                or item.get("feature_controlled")
                or item.get("feature")
                or item.get("measured_feature")
                or ""
            )
            callouts.append(
                GDTCallout(
                    id=str(item.get("id", f"GDT{len(callouts) + 1}")),
                    symbol_type=self._gdt_symbol(symbol_value),
                    tolerance_zone=tolerance_zone,
                    material_condition=self._optional_enum(MaterialCondition, item.get("material_condition")),
                    datum_references=[str(value) for value in item.get("datum_references", item.get("datums", []))],
                    controlled_feature=str(controlled_feature),
                    part_id=str(item.get("part_id") or ""),
                    confidence_score=float(item.get("confidence_score", 0.5)),
                )
            )
        return callouts

    def _parse_datum_response(self, raw_text: str) -> list[Datum]:
        payload = self._extract_json_object(raw_text)
        datums: list[Datum] = []
        for item in payload.get("datums", []):
            label = item.get("label") or item.get("name") or item.get("datum_id") or item.get("datum_letter") or item.get("feature_identifier") or item.get("id")
            if not label:
                continue
            feature_description = (
                item.get("feature_description")
                or item.get("feature_referenced")
                or item.get("location_reference")
                or item.get("description")
                or ""
            )
            datums.append(
                Datum(
                    id=str(item.get("id", label)),
                    label=str(label),
                    feature_description=str(feature_description),
                    part_id=str(item.get("part_id") or ""),
                    confidence_score=float(item.get("confidence_score", 0.5)),
                )
            )
        return datums

    def _parse_material_response(self, raw_text: str) -> list[MaterialSpec]:
        payload = self._extract_json_object(raw_text)
        specs: list[MaterialSpec] = []
        for item in payload.get("material_specs", []):
            material_type = item.get("material_type") or item.get("material") or item.get("material_name") or item.get("specification") or item.get("spec_name")
            if not material_type:
                continue
            specs.append(
                MaterialSpec(
                    material_type=str(material_type),
                    material_grade=item.get("material_grade") or item.get("grade") or item.get("specifications") or item.get("spec_number"),
                    surface_finish=item.get("surface_finish"),
                    heat_treatment=item.get("heat_treatment"),
                    part_id=str(item.get("part_id") or ""),
                    confidence_score=float(item.get("confidence_score", 0.5)),
                )
            )
        return specs

    def _parse_assembly_relationships(self, payload: dict[str, Any]) -> list[AssemblyRelationship]:
        relationships: list[AssemblyRelationship] = []
        for item in payload.get("relationships", []):
            mating_surfaces = item.get("mating_surfaces") or []
            relationships.append(
                AssemblyRelationship(
                    part1_id=str(item.get("part1_id", item.get("part1", ""))),
                    part2_id=str(item.get("part2_id", item.get("part2", ""))),
                    mating_surface1=str(item.get("mating_surface1") or (mating_surfaces[0] if len(mating_surfaces) > 0 else "")),
                    mating_surface2=str(item.get("mating_surface2") or (mating_surfaces[1] if len(mating_surfaces) > 1 else "")),
                    relationship_type=RelationshipType(str(item.get("relationship_type", item.get("type", "contact")))),
                    confidence_score=float(item.get("confidence_score", 0.5)),
                )
            )
        return relationships

    @staticmethod
    def _parse_drawing_links(raw_links: Any) -> dict[str, str]:
        if isinstance(raw_links, dict):
            return {str(key): str(value) for key, value in raw_links.items()}
        links: dict[str, str] = {}
        if isinstance(raw_links, list):
            for item in raw_links:
                if isinstance(item, dict):
                    part_id = item.get("part_id") or item.get("part") or item.get("label")
                    drawing = item.get("drawing") or item.get("drawing_file") or item.get("file")
                    if part_id and drawing:
                        links[str(part_id)] = str(drawing)
        return links

    def _validate_part(
        self,
        dimensions: list[Dimension],
        gdt_callouts: list[GDTCallout],
        datums: list[Datum],
    ) -> ValidationResult:
        dimension_results = [self.validator.validate_dimension(dimension) for dimension in dimensions]
        datum_result = self.validator.validate_datum_references(gdt_callouts, [datum.label for datum in datums])
        unit_result = self.validator.validate_units(dimensions)
        return ValidationResult.combine(*dimension_results, datum_result, unit_result)

    @staticmethod
    def _extract_json_object(raw_text: str) -> dict[str, Any]:
        try:
            loaded = json.loads(raw_text)
            if isinstance(loaded, dict):
                return loaded
        except json.JSONDecodeError:
            pass

        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, flags=re.DOTALL)
        if fenced:
            return json.loads(fenced.group(1))

        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(raw_text[start : end + 1])
        raise ValueError("Could not parse JSON object from LLM response")

    @staticmethod
    def _optional_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _dimension_nominal(cls, item: dict[str, Any], tolerance_data: dict[str, Any] | str | None) -> float | None:
        nominal = cls._optional_float(item.get("nominal_value"))
        if nominal is not None:
            return nominal
        if isinstance(tolerance_data, dict):
            lower = cls._optional_float(tolerance_data.get("lower_limit", tolerance_data.get("min")))
            upper = cls._optional_float(tolerance_data.get("upper_limit", tolerance_data.get("max")))
            if lower is not None and upper is not None:
                return (lower + upper) / 2.0
        return None

    @staticmethod
    def _gdt_symbol(value: Any) -> GDTSymbol:
        normalized = str(value).strip().lower().replace(" ", "_").replace("-", "_")
        aliases = {
            "geometric_control": GDTSymbol.POSITION,
            "clearance_envelope": GDTSymbol.PROFILE_OF_SURFACE,
        }
        if normalized in aliases:
            return aliases[normalized]
        try:
            return GDTSymbol(normalized)
        except ValueError:
            return GDTSymbol.POSITION

    @staticmethod
    def _optional_enum(enum_type: type[Any], value: Any) -> Any | None:
        if value is None:
            return None
        normalized = str(value).strip().lower().replace(" ", "_").replace("-", "_")
        if enum_type is MaterialCondition:
            aliases = {
                "mmc": MaterialCondition.MMC,
                "maximum_material_condition": MaterialCondition.MMC,
                "lmc": MaterialCondition.LMC,
                "least_material_condition": MaterialCondition.LMC,
                "rfs": MaterialCondition.RFS,
                "regardless_of_feature_size": MaterialCondition.RFS,
                "regardless_of_size": MaterialCondition.RFS,
            }
            return aliases.get(normalized)
        try:
            return enum_type(str(value))
        except ValueError:
            return None

    @staticmethod
    def _infer_part_id(pdf_path: Path, dimensions: list[Dimension], material_specs: list[MaterialSpec]) -> str:
        for dimension in dimensions:
            if dimension.part_id:
                return dimension.part_id
        for material_spec in material_specs:
            if material_spec.part_id:
                return material_spec.part_id
        return Path(pdf_path).stem

    @staticmethod
    def _is_chain_candidate(dimension: Dimension) -> bool:
        text = f"{dimension.id} {dimension.measured_feature} {dimension.context}".lower()
        keywords = ("bolt", "protrusion", "stack", "height", "thickness", "depth")
        return any(keyword in text for keyword in keywords)

    @staticmethod
    def _contribution_sign(dimension: Dimension, assembly: AssemblyResult) -> int:
        text = f"{dimension.measured_feature} {dimension.context}".lower()
        if any(word in text for word in ("hole", "counterbore", "recess", "subtract", "clearance")):
            return -1
        if any(relationship.relationship_type is RelationshipType.CLEARANCE for relationship in assembly.relationships):
            return -1 if "clearance" in text else 1
        return 1

