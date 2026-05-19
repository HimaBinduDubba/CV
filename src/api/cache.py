import json
import hashlib
import os
from io import BytesIO
from typing import Any, Optional, Dict
from PIL.Image import Image

class ResponseCache:
    def __init__(self, cache_dir: str = ".cache"):
        self.cache_dir = cache_dir
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
            
    def _generate_key(self, prompt: str, images: list[Image]) -> str:
        hash_obj = hashlib.sha256()
        hash_obj.update(prompt.encode('utf-8'))
        for img in images:
            img_metadata = f"{img.size}_{img.mode}"
            hash_obj.update(img_metadata.encode('utf-8'))
            image_bytes = BytesIO()
            img.save(image_bytes, format="PNG")
            hash_obj.update(image_bytes.getvalue())
        return hash_obj.hexdigest()

    def get(self, prompt: str, images: list[Image]) -> Optional[Dict[str, Any]]:
        key = self._generate_key(prompt, images)
        filepath = os.path.join(self.cache_dir, f"{key}.json")
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    return json.load(f)
            except Exception:
                return None
        return None

    def set(self, prompt: str, images: list[Image], data: Dict[str, Any]) -> None:
        key = self._generate_key(prompt, images)
        filepath = os.path.join(self.cache_dir, f"{key}.json")
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            pass

    def invalidate_all(self) -> None:
        for filename in os.listdir(self.cache_dir):
            if filename.endswith(".json"):
                os.remove(os.path.join(self.cache_dir, filename))
