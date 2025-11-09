"""
Retry logic with exponential backoff for LLM API calls.

Features:
- Exponential backoff with jitter
- Configurable max retries
- Retry on specific HTTP status codes
- Logging of retry attempts
"""

import time
import random
import logging
from typing import Callable, Any, TypeVar, Optional
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')

class RetryError(Exception):
    """Raised when all retry attempts are exhausted."""
    pass

def exponential_backoff_with_jitter(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True
) -> float:
    """
    Calculate delay for exponential backoff with optional jitter.
    
    Args:
        attempt: Current attempt number (0-indexed)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        jitter: Whether to add random jitter
    
    Returns:
        Delay in seconds
    """
    delay = min(base_delay * (2 ** attempt), max_delay)
    
    if jitter:
        # Add random jitter: ±25% of delay
        jitter_amount = delay * 0.25
        delay = delay + random.uniform(-jitter_amount, jitter_amount)
    
    return max(0, delay)

def should_retry_on_exception(exc: Exception, retryable_exceptions: tuple = None) -> bool:
    """
    Determine if an exception should trigger a retry.
    
    Args:
        exc: Exception to check
        retryable_exceptions: Tuple of exception types to retry on
    
    Returns:
        True if should retry, False otherwise
    """
    if retryable_exceptions is None:
        # Default retryable exceptions
        import requests
        retryable_exceptions = (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
            requests.exceptions.HTTPError,
        )
    
    # Check if exception is retryable
    if isinstance(exc, retryable_exceptions):
        # For HTTPError, only retry on specific status codes
        if hasattr(exc, 'response') and exc.response is not None:
            status_code = exc.response.status_code
            # Retry on 429 (rate limit), 500, 502, 503, 504 (server errors)
            return status_code in (429, 500, 502, 503, 504)
        return True
    
    return False

def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    retryable_exceptions: tuple = None,
    on_retry: Optional[Callable[[int, Exception], None]] = None
):
    """
    Decorator for retrying a function with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        jitter: Whether to add random jitter
        retryable_exceptions: Tuple of exception types to retry on
        on_retry: Callback function called on each retry (attempt, exception)
    
    Example:
        @retry_with_backoff(max_retries=3, base_delay=1.0)
        def call_api():
            return requests.get("https://api.example.com")
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    last_exception = exc
                    
                    # Check if we should retry
                    if attempt >= max_retries:
                        logger.error(
                            f"All {max_retries} retry attempts exhausted for {func.__name__}. "
                            f"Last error: {exc}"
                        )
                        raise RetryError(
                            f"Failed after {max_retries} retries: {exc}"
                        ) from exc
                    
                    if not should_retry_on_exception(exc, retryable_exceptions):
                        logger.warning(
                            f"Non-retryable exception in {func.__name__}: {exc}"
                        )
                        raise
                    
                    # Calculate delay
                    delay = exponential_backoff_with_jitter(
                        attempt, base_delay, max_delay, jitter
                    )
                    
                    logger.warning(
                        f"Retry attempt {attempt + 1}/{max_retries} for {func.__name__} "
                        f"after {delay:.2f}s. Error: {exc}"
                    )
                    
                    # Call on_retry callback if provided
                    if on_retry:
                        on_retry(attempt + 1, exc)
                    
                    # Wait before retrying
                    time.sleep(delay)
            
            # This should never be reached, but just in case
            raise RetryError(
                f"Failed after {max_retries} retries: {last_exception}"
            ) from last_exception
        
        return wrapper
    return decorator

def retry_function(
    func: Callable[..., T],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    retryable_exceptions: tuple = None,
    on_retry: Optional[Callable[[int, Exception], None]] = None,
    *args,
    **kwargs
) -> T:
    """
    Retry a function with exponential backoff (non-decorator version).
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        jitter: Whether to add random jitter
        retryable_exceptions: Tuple of exception types to retry on
        on_retry: Callback function called on each retry (attempt, exception)
        *args: Arguments to pass to func
        **kwargs: Keyword arguments to pass to func
    
    Returns:
        Result of func(*args, **kwargs)
    
    Example:
        result = retry_function(
            requests.get,
            max_retries=3,
            base_delay=1.0,
            url="https://api.example.com"
        )
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            last_exception = exc
            
            # Check if we should retry
            if attempt >= max_retries:
                logger.error(
                    f"All {max_retries} retry attempts exhausted for {func.__name__}. "
                    f"Last error: {exc}"
                )
                raise RetryError(
                    f"Failed after {max_retries} retries: {exc}"
                ) from exc
            
            if not should_retry_on_exception(exc, retryable_exceptions):
                logger.warning(
                    f"Non-retryable exception in {func.__name__}: {exc}"
                )
                raise
            
            # Calculate delay
            delay = exponential_backoff_with_jitter(
                attempt, base_delay, max_delay, jitter
            )
            
            logger.warning(
                f"Retry attempt {attempt + 1}/{max_retries} for {func.__name__} "
                f"after {delay:.2f}s. Error: {exc}"
            )
            
            # Call on_retry callback if provided
            if on_retry:
                on_retry(attempt + 1, exc)
            
            # Wait before retrying
            time.sleep(delay)
    
    # This should never be reached, but just in case
    raise RetryError(
        f"Failed after {max_retries} retries: {last_exception}"
    ) from last_exception

