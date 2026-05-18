import pytest
import os
import shutil
from PIL import Image
from hypothesis import given, strategies as st
from unittest.mock import Mock, patch

from src.config import APIConfig
from src.api.models import APIResponse
from src.api.queue import QueueManager
from src.api.cache import ResponseCache
from src.api.retry import RetryHandler, AuthError, RateLimitError, TimeoutError
from src.api.router import APIRouter

@pytest.fixture
def temp_cache_dir():
    cache_dir = ".test_cache"
    yield cache_dir
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)

def test_queue_manager_basic():
    qm = QueueManager()
    qm.add_file("file1.pdf")
    qm.add_file("file2.pdf")
    
    assert qm.total_files == 2
    assert qm.get_next() == "file1.pdf"
    assert qm.in_progress == "file1.pdf"
    
    qm.mark_completed("file1.pdf")
    assert "file1.pdf" in qm.completed
    assert qm.in_progress is None
    
    assert qm.get_progress() == 50.0
    
    assert qm.get_next() == "file2.pdf"
    qm.mark_failed("file2.pdf", "Error occurred")
    assert "file2.pdf" in qm.failed
    
    assert qm.get_progress() == 100.0

@given(st.lists(st.text(min_size=1, max_size=10), unique=True, min_size=1, max_size=20))
def test_queue_progress_calculation(files):
    qm = QueueManager()
    for f in files:
        qm.add_file(f)
        
    for i, f in enumerate(files):
        qm.get_next()
        if i % 2 == 0:
            qm.mark_completed(f)
        else:
            qm.mark_failed(f, "Error")
            
    assert qm.get_progress() == 100.0

def test_response_cache(temp_cache_dir):
    cache = ResponseCache(cache_dir=temp_cache_dir)
    img = Image.new('RGB', (10, 10))
    prompt = "Extract dimensions"
    
    data = {"dimension": 10}
    
    # Cache miss
    assert cache.get(prompt, [img]) is None
    
    # Set and get
    cache.set(prompt, [img], data)
    assert cache.get(prompt, [img]) == data
    
    # Invalidate
    cache.invalidate_all()
    assert cache.get(prompt, [img]) is None

def test_retry_handler_success():
    handler = RetryHandler(max_attempts=3)
    mock_func = Mock(return_value="success")
    
    result = handler.call_with_retry(mock_func)
    assert result == "success"
    assert mock_func.call_count == 1

def test_retry_handler_auth_error():
    handler = RetryHandler(max_attempts=3)
    mock_func = Mock(side_effect=AuthError("Invalid key"))
    
    with pytest.raises(AuthError):
        handler.call_with_retry(mock_func)
        
    assert mock_func.call_count == 1  # Should fail fast without retry

def test_api_router_flow(temp_cache_dir):
    config = APIConfig(provider="gemini", gemini_api_key="fake_key", cache_dir=temp_cache_dir)
    router = APIRouter(config)
    
    # Mock adapter
    mock_response = APIResponse(provider="gemini", raw_response={}, structured_data={"extracted": True}, usage_tokens=10)
    router.adapter = Mock()
    router.adapter.call_api.return_value = mock_response
    
    img = Image.new('RGB', (10, 10))
    
    # Call 1 (miss)
    resp1 = router.extract_from_image("test prompt", [img])
    assert resp1.structured_data == {"extracted": True}
    assert router.adapter.call_api.call_count == 1
    assert router.total_requests == 1
    
    # Call 2 (hit)
    resp2 = router.extract_from_image("test prompt", [img])
    assert resp2.structured_data == {"extracted": True}
    assert router.adapter.call_api.call_count == 1 # Adapter not called again
    assert router.total_requests == 1 # Did not route a real request
