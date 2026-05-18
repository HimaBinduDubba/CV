from dataclasses import dataclass
from typing import Optional
import os
import json

@dataclass
class APIConfig:
    provider: str
    api_key: str

    @classmethod
    def from_env(cls) -> "APIConfig":
        provider = os.getenv("LLM_PROVIDER", "gpt4")
        api_key = os.getenv(f"{provider.upper()}_API_KEY", "")
        if not api_key:
            raise ValueError(f"API key for provider {provider} is not set in environment.")
        return cls(provider=provider, api_key=api_key)

@dataclass
class ExtractorConfig:
    api_config: APIConfig
    cache_dir: str
    dpi: int

    @classmethod
    def load_from_env(cls) -> "ExtractorConfig":
        return cls(
            api_config=APIConfig.from_env(),
            cache_dir=os.getenv("CACHE_DIR", ".cache"),
            dpi=int(os.getenv("PDF_DPI", "300"))
        )

    @classmethod
    def load_from_file(cls, file_path: str) -> "ExtractorConfig":
        with open(file_path, "r") as f:
            data = json.load(f)
        
        provider = data.get("api_provider", "gpt4")
        api_key = data.get("api_key", os.getenv(f"{provider.upper()}_API_KEY", ""))
        
        if not api_key:
            raise ValueError(f"API key for provider {provider} is not set.")
            
        api_config = APIConfig(provider=provider, api_key=api_key)
        
        return cls(
            api_config=api_config,
            cache_dir=data.get("cache_dir", ".cache"),
            dpi=data.get("dpi", 300)
        )
