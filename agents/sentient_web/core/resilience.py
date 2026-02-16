"""
+AAA Resilience patterns for fault tolerance.

Implements:
- Fallback chains with graceful degradation
- Bulkhead pattern for resource isolation
- Timeout management
- Health checks
- Self-healing capabilities
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar, Generic
from datetime import datetime, timedelta
import time


T = TypeVar('T')


class HealthStatus(Enum):
    """Health check status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Health check result."""
    component: str
    status: HealthStatus
    message: str
    timestamp: datetime
    latency_ms: float
    metadata: Dict[str, Any]


class FallbackStrategy(ABC, Generic[T]):
    """Abstract fallback strategy."""
    
    @abstractmethod
    async def execute(self, original_error: Exception) -> T:
        """Execute fallback logic."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if fallback is available."""
        pass


class LocalTemplateFallback(FallbackStrategy[str]):
    """Fallback to local templates when API fails."""
    
    def __init__(self):
        self.templates = {
            'css': self._css_template(),
            'js': self._js_template(),
            'html': self._html_template(),
        }
        self._available = True
    
    def is_available(self) -> bool:
        return self._available
    
    async def execute(self, original_error: Exception) -> str:
        """Return fallback template."""
        logging.warning(f"Using local template fallback due to: {original_error}")
        
        # Return appropriate template based on error context
        return self.templates.get('css', '')  # Default to CSS
    
    def _css_template(self) -> str:
        return """/* FALLBACK CSS - API UNAVAILABLE */
.glass-fallback {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
}
"""
    
    def _js_template(self) -> str:
        return """// FALLBACK JS - API UNAVAILABLE
console.warn('Running in fallback mode');
function initFallback() { return { mode: 'fallback' }; }
"""
    
    def _html_template(self) -> str:
        return """<!-- FALLBACK HTML - API UNAVAILABLE -->
<div class="glass-fallback">
  <p>Component rendered in fallback mode</p>
</div>
"""


class CachedResponseFallback(FallbackStrategy[Any]):
    """Fallback to cached responses."""
    
    def __init__(self, cache_ttl_seconds: float = 3600):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = cache_ttl_seconds
        self._available = True
    
    def is_available(self) -> bool:
        return len(self.cache) > 0
    
    def cache_response(self, key: str, response: Any):
        """Cache a successful response."""
        self.cache[key] = {
            'data': response,
            'timestamp': time.time()
        }
    
    async def execute(self, original_error: Exception) -> Any:
        """Return most recent valid cached response."""
        logging.warning(f"Using cached response fallback due to: {original_error}")
        
        # Find most recent valid cache entry
        now = time.time()
        valid_entries = [
            (k, v) for k, v in self.cache.items()
            if now - v['timestamp'] < self.cache_ttl
        ]
        
        if not valid_entries:
            raise Exception("No valid cached responses available")
        
        # Return most recent
        most_recent = max(valid_entries, key=lambda x: x[1]['timestamp'])
        return most_recent[1]['data']


class SimplifiedGenerationFallback(FallbackStrategy[str]):
    """Fallback to simplified code generation."""
    
    def __init__(self):
        self._available = True
    
    def is_available(self) -> bool:
        return self._available
    
    async def execute(self, original_error: Exception) -> str:
        """Generate minimal but functional code."""
        logging.warning(f"Using simplified generation fallback due to: {original_error}")
        
        # Return minimal but valid CSS
        return """
/* Simplified fallback - minimal but functional */
.component {
  padding: 16px;
  margin: 8px 0;
  background: #f5f5f5;
  border-radius: 4px;
}
"""


class FallbackChain(Generic[T]):
    """
    Chain of fallback strategies.
    
    Tries each fallback in order until one succeeds.
    """
    
    def __init__(self, strategies: List[FallbackStrategy[T]]):
        self.strategies = strategies
        self.metrics = {
            'total_fallbacks': 0,
            'successful_fallbacks': 0,
            'failed_fallbacks': 0,
            'by_strategy': {}
        }
    
    async def execute(self, original_error: Exception) -> T:
        """Execute fallback chain."""
        self.metrics['total_fallbacks'] += 1
        
        for strategy in self.strategies:
            strategy_name = strategy.__class__.__name__
            
            if not strategy.is_available():
                logging.debug(f"Fallback {strategy_name} not available, skipping")
                continue
            
            try:
                result = await strategy.execute(original_error)
                
                # Record success
                self.metrics['successful_fallbacks'] += 1
                self.metrics['by_strategy'][strategy_name] = \
                    self.metrics['by_strategy'].get(strategy_name, 0) + 1
                
                logging.info(f"Fallback succeeded: {strategy_name}")
                return result
                
            except Exception as e:
                logging.warning(f"Fallback {strategy_name} failed: {e}")
                continue
        
        # All fallbacks exhausted
        self.metrics['failed_fallbacks'] += 1
        raise Exception(f"All fallback strategies exhausted for: {original_error}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get fallback chain metrics."""
        return {
            **self.metrics,
            'success_rate': (
                self.metrics['successful_fallbacks'] / self.metrics['total_fallbacks'] * 100
                if self.metrics['total_fallbacks'] > 0 else 0
            )
        }


class Bulkhead:
    """
    Bulkhead pattern for resource isolation.
    
    Limits concurrent operations to prevent resource exhaustion.
    """
    
    def __init__(
        self,
        name: str,
        max_concurrent: int = 10,
        max_queue: int = 100,
        timeout_seconds: float = 30.0
    ):
        self.name = name
        self.max_concurrent = max_concurrent
        self.max_queue = max_queue
        self.timeout = timeout_seconds
        
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.queue_size = 0
        self.metrics = {
            'executed': 0,
            'queued': 0,
            'rejected': 0,
            'timeouts': 0,
        }
        self._lock = asyncio.Lock()
    
    async def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with bulkhead protection."""
        # Check queue capacity
        async with self._lock:
            if self.queue_size >= self.max_queue:
                self.metrics['rejected'] += 1
                raise BulkheadFullError(
                    f"Bulkhead '{self.name}' queue full ({self.max_queue})"
                )
            self.queue_size += 1
            self.metrics['queued'] += 1
            queued = True
        
        try:
            async with self.semaphore:
                async with self._lock:
                    if queued:
                        self.queue_size -= 1
                        queued = False
                self.metrics['executed'] += 1
                
                # Execute with timeout
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=self.timeout
                )
                
        except asyncio.TimeoutError:
            self.metrics['timeouts'] += 1
            raise BulkheadTimeoutError(
                f"Bulkhead '{self.name}' operation timed out after {self.timeout}s"
            )
        finally:
            async with self._lock:
                if queued:
                    self.queue_size -= 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get bulkhead metrics."""
        return {
            'name': self.name,
            'max_concurrent': self.max_concurrent,
            'max_queue': self.max_queue,
            'current_queue': self.queue_size,
            'utilization': (
                (self.max_concurrent - self.semaphore._value) / self.max_concurrent * 100
            ),
            **self.metrics
        }


class BulkheadFullError(Exception):
    """Raised when bulkhead queue is full."""
    pass


class BulkheadTimeoutError(Exception):
    """Raised when bulkhead operation times out."""
    pass


class HealthChecker:
    """
    Health checking system for components.
    
    Monitors component health and triggers recovery actions.
    """
    
    def __init__(self, check_interval_seconds: float = 30.0):
        self.check_interval = check_interval_seconds
        self.checks: Dict[str, Callable[[], HealthCheck]] = {}
        self.results: Dict[str, HealthCheck] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    def register_check(
        self,
        name: str,
        check_func: Callable[[], HealthCheck]
    ):
        """Register a health check."""
        self.checks[name] = check_func
    
    async def start(self):
        """Start health check loop."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._check_loop())
        logging.info("Health checker started")
    
    async def stop(self):
        """Stop health check loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logging.info("Health checker stopped")
    
    async def _check_loop(self):
        """Main health check loop."""
        while self._running:
            try:
                await self.run_checks()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"Health check loop error: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def run_checks(self) -> Dict[str, HealthCheck]:
        """Run all health checks."""
        for name, check_func in self.checks.items():
            try:
                start = time.time()
                result = check_func()
                result.latency_ms = (time.time() - start) * 1000
                self.results[name] = result
            except Exception as e:
                self.results[name] = HealthCheck(
                    component=name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check failed: {e}",
                    timestamp=datetime.now(),
                    latency_ms=0,
                    metadata={}
                )
        
        return self.results
    
    def get_overall_health(self) -> HealthStatus:
        """Get overall system health."""
        if not self.results:
            return HealthStatus.UNKNOWN
        
        statuses = [r.status for r in self.results.values()]
        
        if any(s == HealthStatus.UNHEALTHY for s in statuses):
            return HealthStatus.UNHEALTHY
        elif any(s == HealthStatus.DEGRADED for s in statuses):
            return HealthStatus.DEGRADED
        elif all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY
        
        return HealthStatus.UNKNOWN
    
    def get_report(self) -> Dict[str, Any]:
        """Get comprehensive health report."""
        return {
            'overall': self.get_overall_health().value,
            'timestamp': datetime.now().isoformat(),
            'components': {
                name: {
                    'status': check.status.value,
                    'message': check.message,
                    'latency_ms': check.latency_ms,
                    'metadata': check.metadata
                }
                for name, check in self.results.items()
            }
        }


class GracefulDegradation:
    """
    Manages graceful degradation of service capabilities.
    
    Reduces functionality under load or failure rather than failing completely.
    """
    
    def __init__(self):
        self.features: Dict[str, Dict[str, Any]] = {
            'ai_generation': {'enabled': True, 'priority': 1},
            'real_time_benchmarks': {'enabled': True, 'priority': 2},
            'detailed_logging': {'enabled': True, 'priority': 3},
            'advanced_analytics': {'enabled': True, 'priority': 4},
            'historical_reports': {'enabled': True, 'priority': 5},
        }
        self.degradation_level = 0  # 0 = full, 1 = reduced, 2 = minimal
    
    def degrade(self, level: int):
        """Set degradation level."""
        self.degradation_level = level
        
        if level == 0:
            # Full functionality
            for feature in self.features:
                self.features[feature]['enabled'] = True
        elif level == 1:
            # Reduced - disable lower priority features
            for name, config in self.features.items():
                config['enabled'] = config['priority'] <= 3
        elif level >= 2:
            # Minimal - only critical features
            for name, config in self.features.items():
                config['enabled'] = config['priority'] == 1
        
        logging.warning(f"Service degraded to level {level}")
    
    def is_enabled(self, feature: str) -> bool:
        """Check if feature is enabled."""
        return self.features.get(feature, {}).get('enabled', False)
    
    def get_status(self) -> Dict[str, Any]:
        """Get degradation status."""
        return {
            'level': self.degradation_level,
            'features': {
                name: config['enabled']
                for name, config in self.features.items()
            }
        }
