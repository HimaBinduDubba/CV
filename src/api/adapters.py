import json
from typing import Any, Dict
from PIL.Image import Image
from .base import APIVisionAdapter
from .models import APIResponse
import google.generativeai as genai

class GeminiVisionAdapter(APIVisionAdapter):
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

    def call_api(self, prompt: str, images: list[Image]) -> APIResponse:
        # Assuming images are PIL Image objects which genai can handle directly
        contents = [prompt] + images
        
        try:
            response = self.model.generate_content(
                contents,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                )
            )
            return self.parse_response(response)
        except Exception as e:
            return APIResponse(
                provider="gemini",
                raw_response={"error": str(e)},
                error=str(e),
                confidence=0.0
            )

    def format_request(self, prompt: str, images: list[Image]) -> Dict[str, Any]:
        return {"prompt": prompt, "images_count": len(images)}

    def parse_response(self, raw_response: Any) -> APIResponse:
        try:
            text = raw_response.text
            structured_data = json.loads(text)
            
            # Simple token estimation
            usage_metadata = getattr(raw_response, 'usage_metadata', None)
            tokens = usage_metadata.total_token_count if usage_metadata else 0
            
            return APIResponse(
                provider="gemini",
                raw_response={"text": text},
                structured_data=structured_data,
                usage_tokens=tokens,
                confidence=1.0 # Base confidence, validator adjusts later
            )
        except Exception as e:
            return APIResponse(
                provider="gemini",
                raw_response={"error": str(e), "object": str(raw_response)},
                error=f"Failed to parse response: {e}",
                confidence=0.0
            )

class GPT4VisionAdapter(APIVisionAdapter):
    def __init__(self, api_key: str):
        pass
        
    def call_api(self, prompt: str, images: list[Image]) -> APIResponse:
        raise NotImplementedError("GPT-4 adapter not fully implemented.")
        
    def format_request(self, prompt: str, images: list[Image]) -> Dict[str, Any]:
        pass
        
    def parse_response(self, raw_response: Any) -> APIResponse:
        pass

class ClaudeVisionAdapter(APIVisionAdapter):
    def __init__(self, api_key: str):
        pass
        
    def call_api(self, prompt: str, images: list[Image]) -> APIResponse:
        raise NotImplementedError("Claude adapter not fully implemented.")
        
    def format_request(self, prompt: str, images: list[Image]) -> Dict[str, Any]:
        pass
        
    def parse_response(self, raw_response: Any) -> APIResponse:
        pass
