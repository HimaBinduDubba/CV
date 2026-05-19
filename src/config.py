from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Optional

@dataclass
class APIConfig:
    provider: str = "gemini"  # "gpt4", "claude", or "gemini"
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.5-flash"
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    cache_dir: str = ".cache"

    @classmethod
    def from_env(cls) -> "APIConfig":
        provider = os.getenv("LLM_PROVIDER", "gemini").lower()
        return cls(
            provider=provider,
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            cache_dir=os.getenv("CACHE_DIR", ".cache"),
        ).validate()

    @classmethod
    def from_file(cls, file_path: str | Path) -> "APIConfig":
        with open(file_path, "r") as file:
            data = json.load(file)
        provider = data.get("provider", data.get("api_provider", "gemini")).lower()
        api_key = data.get("api_key")
        return cls(
            provider=provider,
            gemini_api_key=data.get("gemini_api_key") or (api_key if provider == "gemini" else None),
            gemini_model=data.get("gemini_model", "gemini-2.5-flash"),
            openai_api_key=data.get("openai_api_key") or (api_key if provider == "gpt4" else None),
            anthropic_api_key=data.get("anthropic_api_key") or (api_key if provider == "claude" else None),
            cache_dir=data.get("cache_dir", ".cache"),
        ).validate()

    def validate(self) -> "APIConfig":
        if self.provider == "gemini" and not self.gemini_api_key:
            raise ValueError("Gemini API key is required. Set GEMINI_API_KEY or config.local.json.")
        if self.provider == "gpt4" and not self.openai_api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY or config.local.json.")
        if self.provider == "claude" and not self.anthropic_api_key:
            raise ValueError("Anthropic API key is required. Set ANTHROPIC_API_KEY or config.local.json.")
        if self.provider not in {"gemini", "gpt4", "claude"}:
            raise ValueError(f"Unknown API provider: {self.provider}")
        return self
