from dataclasses import dataclass
from typing import Optional

@dataclass
class APIConfig:
    provider: str = "gemini"  # "gpt4", "claude", or "gemini"
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    cache_dir: str = ".cache"
