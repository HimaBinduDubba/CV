import logging
from typing import Dict, Any, Optional
from PIL.Image import Image
from ..config import APIConfig
from .models import APIResponse
from .base import APIVisionAdapter
from .adapters import GeminiVisionAdapter, GPT4VisionAdapter, ClaudeVisionAdapter
from .retry import RetryHandler
from .cache import ResponseCache

logger = logging.getLogger(__name__)

class APIRouter:
    def __init__(self, config: APIConfig):
        self.config = config
        self.retry_handler = RetryHandler(max_attempts=3)
        self.cache = ResponseCache(cache_dir=config.cache_dir)
        
        self.total_requests = 0
        self.total_tokens = 0
        self.total_estimated_cost = 0.0
        
        self.adapter = self._get_adapter(config)

    def _get_adapter(self, config: APIConfig) -> APIVisionAdapter:
        if config.provider == "gemini":
            if not config.gemini_api_key:
                raise ValueError("Gemini API key is required but not provided.")
            return GeminiVisionAdapter(api_key=config.gemini_api_key)
        elif config.provider == "gpt4":
            if not config.openai_api_key:
                raise ValueError("OpenAI API key is required but not provided.")
            return GPT4VisionAdapter(api_key=config.openai_api_key)
        elif config.provider == "claude":
            if not config.anthropic_api_key:
                raise ValueError("Anthropic API key is required but not provided.")
            return ClaudeVisionAdapter(api_key=config.anthropic_api_key)
        else:
            raise ValueError(f"Unknown API provider: {config.provider}")

    def extract_from_image(self, prompt: str, images: list[Image]) -> APIResponse:
        cached_data = self.cache.get(prompt, images)
        if cached_data:
            logger.info("Cache hit for prompt.")
            return APIResponse(**cached_data)
            
        logger.info(f"Routing request to {self.config.provider}...")
        
        def _call():
            return self.adapter.call_api(prompt, images)
            
        try:
            response: APIResponse = self.retry_handler.call_with_retry(_call)
            
            self.total_requests += 1
            self.total_tokens += response.usage_tokens
            self.total_estimated_cost += response.estimated_cost
            
            if not response.error and response.structured_data:
                cache_dict = {
                    "provider": response.provider,
                    "raw_response": response.raw_response,
                    "structured_data": response.structured_data,
                    "usage_tokens": response.usage_tokens,
                    "estimated_cost": response.estimated_cost,
                    "confidence": response.confidence,
                    "error": response.error
                }
                self.cache.set(prompt, images, cache_dict)
                
            return response
            
        except Exception as e:
            logger.error(f"API request failed: {e}")
            return APIResponse(
                provider=self.config.provider,
                raw_response={},
                error=str(e),
                confidence=0.0
            )

    def get_usage_stats(self) -> Dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens,
            "total_estimated_cost": self.total_estimated_cost
        }
