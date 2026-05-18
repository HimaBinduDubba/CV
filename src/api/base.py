from abc import ABC, abstractmethod
from typing import Any, Dict
from PIL.Image import Image
from .models import APIResponse

class APIVisionAdapter(ABC):
    @abstractmethod
    def call_api(self, prompt: str, images: list[Image]) -> APIResponse:
        pass

    @abstractmethod
    def format_request(self, prompt: str, images: list[Image]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def parse_response(self, raw_response: Any) -> APIResponse:
        pass
