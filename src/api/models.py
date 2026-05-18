from dataclasses import dataclass, field
from typing import Dict, Any, Optional

@dataclass
class APIResponse:
    provider: str
    raw_response: Dict[str, Any]
    structured_data: Optional[Dict[str, Any]] = None
    usage_tokens: int = 0
    estimated_cost: float = 0.0
    confidence: float = 1.0
    error: Optional[str] = None
