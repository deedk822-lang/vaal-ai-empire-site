"""
Bulkhead pattern for resource isolation.
"""

import asyncio
from typing import Any, Callable


class Bulkhead:
    """
    Limits concurrent operations to prevent resource exhaustion.
    """
    
    def __init__(
        self,
        name: str,
        max_concurrent: int = 10,
        max_queue: int = 100,
        timeout: float = 30.0
    ):
        self.name = name
        self.max_concurrent = max_concurrent
        self.max_queue = max_queue
        self.timeout = timeout
        
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.queue_size = 0
        self._queue_lock = asyncio.Lock()
    
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute with bulkhead protection."""
        async with self._queue_lock:
            if self.queue_size >= self.max_queue:
                raise BulkheadFull(f"Bulkhead '{self.name}' queue full")
            self.queue_size += 1
            queued = True
        
        try:
            async with self.semaphore:
                async with self._queue_lock:
                    if queued:
                        self.queue_size -= 1
                        queued = False
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=self.timeout
                )
        except asyncio.TimeoutError as err:
            raise BulkheadTimeout(f"Bulkhead '{self.name}' timeout") from err
        finally:
            async with self._queue_lock:
                if queued:
                    self.queue_size -= 1


class BulkheadFull(Exception):
    pass


class BulkheadTimeout(Exception):
    pass
