import pytest
from pathlib import Path
from src.dimension_extractor.report_generator import HumanReviewReport

@pytest.fixture
def sample_output():
    return {
        "metadata": {
            "overall_confidence": 0.85
        },
        "parts": [
            {
                "part_id": "P1",
                "dimensions": [
                    {"id": "D1", "nominal_value": 10.5, "unit": "mm", "confidence_score": 0.9},
                    {"id": "D2", "nominal_value": 2.0, "unit": "mm", "confidence_score": 0.6}
                ]
            }
        ]
    }

def test_generate_html_report(sample_output, tmp_path):
    report_generator = HumanReviewReport(confidence_threshold=0.8)
    out_path = tmp_path / "report.html"
    
    report_generator.generate_html_report(sample_output, out_path)
    
    assert out_path.exists()
    content = out_path.read_text()
    
    assert "Extraction Review Report" in content
    assert "Overall Confidence: 0.85" in content
    # D2 should be in the report because confidence < 0.8
    assert "Dimension D2" in content
    assert "Confidence: 0.6" in content
    # D1 should not be highlighted as low confidence
    assert "Dimension D1" not in content
