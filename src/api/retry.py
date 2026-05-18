import logging
from typing import Callable, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, RetryError

logger = logging.getLogger(__name__)

class RateLimitError(Exception):
    pass

class AuthError(Exception):
    pass

class TimeoutError(Exception):
    pass

class RetryHandler:
    def __init__(self, max_attempts: int = 3):
        self.max_attempts = max_attempts

    def call_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        @retry(
            retry=(
                retry_if_exception_type(RateLimitError) |
                retry_if_exception_type(TimeoutError)
            ),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            stop=stop_after_attempt(self.max_attempts),
            reraise=True
        )
        def _execute():
            try:
                return func(*args, **kwargs)
            except AuthError as e:
                # Fast fail for auth errors
                logger.error(f"Authentication failed: {e}")
                raise e
            except Exception as e:
                logger.warning(f"API call failed with {type(e).__name__}: {e}. Retrying...")
                raise e
                
        try:
            return _execute()
        except RetryError as e:
            logger.error(f"Failed after {self.max_attempts} attempts.")
            raise e.last_attempt.exception()
