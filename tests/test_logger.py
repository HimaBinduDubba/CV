import pytest
import logging
import json
from datetime import datetime
from src.dimension_extractor.logger import setup_logger, ErrorLog, log_error, APIUsageLog, log_api_usage
from hypothesis import given, strategies as st

def test_setup_logger(tmp_path):
    log_file = tmp_path / "test.log"
    logger = setup_logger(name="test_logger", log_file=str(log_file), level=logging.INFO)
    
    logger.info("Test message")
    
    assert log_file.exists()
    with open(log_file, "r") as f:
        content = f.read()
        data = json.loads(content.strip())
        assert data["message"] == "Test message"
        assert data["level"] == "INFO"

def test_log_error(tmp_path):
    log_file = tmp_path / "test_error.log"
    logger = setup_logger(name="test_error_logger", log_file=str(log_file), level=logging.WARNING)
    
    err = ErrorLog(
        timestamp=datetime.now(),
        error_type="ValueError",
        severity="error",
        message="Invalid value",
        context={"file": "test.pdf"}
    )
    
    log_error(logger, err)
    
    with open(log_file, "r") as f:
        content = f.read()
        data = json.loads(content.strip())
        assert data["message"] == "Invalid value"
        assert data["level"] == "ERROR"
        assert data["error_type"] == "ValueError"
        assert data["severity"] == "error"
        assert data["context"] == {"file": "test.pdf"}

def test_log_api_usage(tmp_path):
    log_file = tmp_path / "test_api.log"
    logger = setup_logger(name="test_api_logger", log_file=str(log_file), level=logging.INFO)
    
    usage = APIUsageLog(provider="gpt4", total_tokens=100)
    log_api_usage(logger, usage, context={"api_key": "secret123"})
    
    with open(log_file, "r") as f:
        content = f.read()
        data = json.loads(content.strip())
        assert "api_usage" in data
        assert data["api_usage"]["provider"] == "gpt4"
        assert data["api_usage"]["total_tokens"] == 100
        # Check redaction
        assert data["context"]["api_key"] == "***REDACTED***"

# Feature: dimension-extraction-system, Property 17: Error Logging Completeness
@given(
    error_type=st.text(),
    severity=st.sampled_from(["warning", "error", "critical"]),
    message=st.text(),
    stack_trace=st.one_of(st.none(), st.text())
)
def test_property_error_logging_completeness(error_type, severity, message, stack_trace):
    err = ErrorLog(
        timestamp=datetime.now(),
        error_type=error_type,
        severity=severity,
        message=message,
        context={"key": "value"},
        stack_trace=stack_trace
    )
    from src.dimension_extractor.logger import JsonFormatter
    record = logging.LogRecord(
        name="test", level=logging.ERROR, pathname="", lineno=0,
        msg=message, args=(), exc_info=None
    )
    record.error_log = err
    formatter = JsonFormatter()
    output = formatter.format(record)
    parsed = json.loads(output)
    
    assert parsed["error_type"] == error_type
    assert parsed["severity"] == severity
    assert parsed["message"] == message
    assert parsed["context"] == {"key": "value"}
    assert parsed.get("stack_trace") == stack_trace
