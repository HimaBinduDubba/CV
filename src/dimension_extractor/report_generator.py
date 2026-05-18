from pathlib import Path
from typing import Dict, Any

class HumanReviewReport:
    def __init__(self, confidence_threshold: float = 0.8):
        self.confidence_threshold = confidence_threshold

    def generate_html_report(self, extraction_output: Dict[str, Any], output_path: Path):
        html_content = [
            "<html>",
            "<head><title>Human Review Report</title></head>",
            "<body>",
            "<h1>Extraction Review Report</h1>"
        ]
        
        metadata = extraction_output.get("metadata", {})
        overall_confidence = metadata.get("overall_confidence", 1.0)
        
        html_content.append(f"<p>Overall Confidence: {overall_confidence}</p>")
        
        html_content.append("<h2>Low Confidence Extractions</h2><ul>")
        
        has_low_confidence = False
        parts = extraction_output.get("parts", [])
        for part in parts:
            for dim in part.get("dimensions", []):
                conf = dim.get("confidence_score", 1.0)
                if conf < self.confidence_threshold:
                    has_low_confidence = True
                    html_content.append(f"<li>Part {part.get('part_id')}, Dimension {dim.get('id')}: {dim.get('nominal_value')} {dim.get('unit')} (Confidence: {conf})</li>")
                    
        if not has_low_confidence:
            html_content.append("<li>No low confidence extractions found.</li>")
            
        html_content.append("</ul></body></html>")
        
        with open(output_path, "w") as f:
            f.write("\n".join(html_content))
