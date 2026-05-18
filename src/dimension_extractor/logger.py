import logging
from logging.handlers import RotatingFileHandler
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional
import json

@dataclass
class ErrorLog:
    timestamp: datetime
    error_type: str
    severity: str
    message: str
    context: Dict[str, Any]
    stack_trace: Optional[str] = None

@dataclass
class APIUsageLog:
    provider: str
    request_count: int = 1
    response_count: int = 1
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0

def redact_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
    redacted = data.copy()
    for key, value in redacted.items():
        if isinstance(value, dict):
            redacted[key] = redact_sensitive_data(value)
        elif any(sensitive in key.lower() for sensitive in ['api_key', 'authorization', 'secret', 'password', 'token']):
            redacted[key] = "***REDACTED***"
    return redacted

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "name": record.name
        }
        if hasattr(record, "error_log") and isinstance(record.error_log, ErrorLog):
            err: ErrorLog = record.error_log
            log_record.update({
                "error_type": err.error_type,
                "severity": err.severity,
                "context": err.context,
                "stack_trace": err.stack_trace
            })
        if hasattr(record, "api_usage"):
            log_record["api_usage"] = record.api_usage
        if hasattr(record, "context"):
            log_record["context"] = record.context
        return json.dumps(log_record)

def setup_logger(name: str = "dimension_extractor", log_file: str = "extractor.log", level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.handlers:
        return logger

    ch = logging.StreamHandler()
    ch.setLevel(level)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)

    fh = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
    fh.setLevel(level)
    json_formatter = JsonFormatter()
    fh.setFormatter(json_formatter)

    logger.addHandler(ch)
    logger.addHandler(fh)

    return logger

def log_error(logger: logging.Logger, error: ErrorLog):
    """Utility to log structured error"""
    level_map = {
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL
    }
    lvl = level_map.get(error.severity.lower(), logging.ERROR)
    logger.log(lvl, error.message, extra={"error_log": error})

def log_api_usage(logger: logging.Logger, usage: APIUsageLog, context: Optional[Dict[str, Any]] = None):
    """Utility to log API usage with sensitive data redaction"""
    safe_context = redact_sensitive_data(context) if context else {}
    usage_dict = {
        "provider": usage.provider,
        "requests": usage.request_count,
        "responses": usage.response_count,
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens,
        "total_tokens": usage.total_tokens,
        "estimated_cost": usage.estimated_cost
    }
    logger.info(f"API Usage for {usage.provider}: {usage.total_tokens} tokens", extra={
        "api_usage": usage_dict,
        "context": safe_context
    })
