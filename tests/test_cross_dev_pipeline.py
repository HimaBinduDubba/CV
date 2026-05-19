from pathlib import Path

from PIL import Image

from src.api.models import APIResponse
from src.api.router import APIRouter
from src.config import APIConfig
from src.dimension_extractor.extractor import DimensionExtractor
from src.dimension_extractor.pdf_converter import PDFConverter


class FakePDFConverter(PDFConverter):
    def convert_pdf_to_images(self, pdf_path: Path):
        return [Image.new("RGB", (10, 10), "white")]


class FakeAdapter:
    def __init__(self, structured_data):
        self.structured_data = structured_data
        self.calls = 0

    def call_api(self, prompt, images):
        self.calls += 1
        assert isinstance(prompt, str)
        assert len(images) == 1
        assert hasattr(images[0], "size")
        return APIResponse(
            provider="gemini",
            raw_response={"text": "{}"},
            structured_data=self.structured_data,
            usage_tokens=12,
            estimated_cost=0.01,
            confidence=0.93,
        )


def test_pdf_converter_api_router_and_extractor_work_together(tmp_path):
    cache_dir = tmp_path / "cache"
    payload = {
        "dimensions": [
            {
                "id": "D1",
                "nominal_value": 12.5,
                "unit": "mm",
                "measured_feature": "bolt protrusion height",
                "part_id": "BOLT",
                "tolerance": {"type": "bilateral", "plus": 0.1, "minus": 0.1, "unit": "mm"},
                "confidence_score": 0.95,
            }
        ],
        "gdt_callouts": [],
        "datums": [],
        "material_specs": [],
    }
    router = APIRouter(APIConfig(provider="gemini", gemini_api_key="fake", cache_dir=str(cache_dir)))
    router.adapter = FakeAdapter(payload)
    extractor = DimensionExtractor(api_router=router, pdf_converter=FakePDFConverter())

    result = extractor.process_pdf(tmp_path / "drawing.pdf")

    assert result.part_id == "BOLT"
    assert result.dimensions[0].nominal_value == 12.5
    assert router.total_requests == 1
    assert router.total_tokens == 12


def test_assembly_png_flows_through_api_router(tmp_path):
    png_path = tmp_path / "assembly.png"
    Image.new("RGB", (10, 10), "white").save(png_path)
    payload = {
        "part_ids": ["BOLT", "CASE"],
        "drawing_links": {"BOLT": "AS3580-Bolt.pdf"},
        "relationships": [
            {
                "part1_id": "BOLT",
                "part2_id": "CASE",
                "mating_surface1": "thread",
                "mating_surface2": "case hole",
                "relationship_type": "bolted",
                "confidence_score": 0.91,
            }
        ],
    }
    router = APIRouter(APIConfig(provider="gemini", gemini_api_key="fake", cache_dir=str(tmp_path / "cache")))
    router.adapter = FakeAdapter(payload)
    extractor = DimensionExtractor(api_router=router, pdf_converter=FakePDFConverter())

    result = extractor.process_assembly_diagram(png_path)

    assert result.part_ids == ["BOLT", "CASE"]
    assert result.relationships[0].part1_id == "BOLT"
    assert result.drawing_links["BOLT"] == "AS3580-Bolt.pdf"
