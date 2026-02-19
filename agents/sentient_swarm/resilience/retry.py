"""
Retry policies with exponential backoff.
"""

import asyncio
import random
from functools import wraps
from typing import Callable, Tuple, Type


class RetryPolicy:
    """Configurable retry policy."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff."""
        delay = min(self.base_delay * (self.exponential_base**attempt), self.max_delay)
        if self.jitter:
            delay *= 0.5 + random.random()
        return delay

    async def execute(self, func: Callable, *args, **kwargs):
        """Execute with retry."""
        last_error = None

        for attempt in range(self.max_attempts):
            try:
                return await func(*args, **kwargs)
            except self.retryable_exceptions as e:
                last_error = e
                if attempt < self.max_attempts - 1:
                    delay = self.calculate_delay(attempt)
                    await asyncio.sleep(delay)

        raise last_error


def with_retry(policy: RetryPolicy = None):
    """Decorator for retry."""
    if policy is None:
        policy = RetryPolicy()

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await policy.execute(func, *args, **kwargs)

        return wrapper

    return decorator
