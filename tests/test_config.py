import pytest
import os
import json
from unittest.mock import patch
from src.dimension_extractor.config import ExtractorConfig, APIConfig

def test_api_config_from_env_missing_key():
    with patch.dict(os.environ, {"LLM_PROVIDER": "gpt4"}, clear=True):
        with pytest.raises(ValueError, match="API key for provider gpt4 is not set"):
            APIConfig.from_env()

def test_api_config_from_env_success():
    with patch.dict(os.environ, {"LLM_PROVIDER": "claude", "CLAUDE_API_KEY": "test_key"}, clear=True):
        config = APIConfig.from_env()
        assert config.provider == "claude"
        assert config.api_key == "test_key"

def test_extractor_config_from_env():
    with patch.dict(os.environ, {
        "LLM_PROVIDER": "gemini", 
        "GEMINI_API_KEY": "gem_key",
        "CACHE_DIR": "/tmp/cache",
        "PDF_DPI": "400"
    }, clear=True):
        config = ExtractorConfig.load_from_env()
        assert config.api_config.provider == "gemini"
        assert config.cache_dir == "/tmp/cache"
        assert config.dpi == 400

def test_extractor_config_load_from_file(tmp_path):
    config_file = tmp_path / "config.json"
    with open(config_file, "w") as f:
        json.dump({
            "api_provider": "gpt4",
            "api_key": "file_key",
            "cache_dir": "./my_cache",
            "dpi": 250
        }, f)
        
    config = ExtractorConfig.load_from_file(str(config_file))
    assert config.api_config.provider == "gpt4"
    assert config.api_config.api_key == "file_key"
    assert config.cache_dir == "./my_cache"
    assert config.dpi == 250
