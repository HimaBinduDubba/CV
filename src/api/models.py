from dataclasses import dataclass
from typing import Dict, Any, Optional
import json

@dataclass
class APIResponse:
    provider: str
    raw_response: Dict[str, Any]
    structured_data: Optional[Dict[str, Any]] = None
    usage_tokens: int = 0
    estimated_cost: float = 0.0
    confidence: float = 1.0
    error: Optional[str] = None

    @property
    def raw_text(self) -> str:
        """Text form consumed by the extraction parser."""
        if self.structured_data is not None:
            return json.dumps(self.structured_data)
        text = self.raw_response.get("text")
        if isinstance(text, str):
            return text
        return json.dumps(self.raw_response)

    @property
    def confidence_score(self) -> float:
        return self.confidence
