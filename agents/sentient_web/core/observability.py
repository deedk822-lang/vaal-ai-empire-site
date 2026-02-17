"""
Observability stack for monitoring and debugging.

Implements +AAA observability with:
- Structured logging (JSON)
- Metrics collection (Prometheus-compatible)
- Distributed tracing
- Performance profiling
"""

import json
import logging
import time
import uuid
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from functools import wraps


class StructuredLogger:
    """
    Structured JSON logger for machine-readable logs.
    
    Compatible with log aggregation systems (ELK, Datadog, etc.)
    """
    
    LEVELS = {
        'DEBUG': 10,
        'INFO': 20,
        'WARNING': 30,
        'ERROR': 40,
        'CRITICAL': 50
    }
    
    def __init__(self, name: str, level: str = 'INFO'):
        self.name = name
        self.level = self.LEVELS.get(level, 20)
        
        # Setup Python logger
        self._logger = logging.getLogger(name)
        self._logger.setLevel(self.level)
        
        # JSON formatter
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(message)s'))
        self._logger.handlers = [handler]
    
    def _log(self, level: str, message: str, **kwargs):
        """Log structured message."""
        if self.LEVELS.get(level, 0) < self.level:
            return
        
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': level,
            'logger': self.name,
            'message': message,
            'trace_id': kwargs.get('trace_id', str(uuid.uuid4())[:8]),
            'service': 'sentient-web-agents',
            **kwargs
        }
        
        # Add to Python logger
        log_method = getattr(self._logger, level.lower(), self._logger.info)
        log_method(json.dumps(log_entry, default=str))
    
    def debug(self, message: str, **kwargs):
        self._log('DEBUG', message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self._log('INFO', message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log('WARNING', message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log('ERROR', message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self._log('CRITICAL', message, **kwargs)
    
    def log_exception(self, exception: Exception, **kwargs):
        """Log exception with stack trace."""
        import traceback
        self.error(
            str(exception),
            exception_type=type(exception).__name__,
            stack_trace=traceback.format_exc(),
            **kwargs
        )


@dataclass
class MetricValue:
    """Single metric value with timestamp."""
    value: float
    timestamp: float
    labels: Dict[str, str]


class MetricsCollector:
    """
    Prometheus-compatible metrics collector.
    
    Supports counters, gauges, and histograms.
    """
    
    def __init__(self, namespace: str = 'sentient_web'):
        self.namespace = namespace
        self.counters: Dict[str, List[MetricValue]] = defaultdict(list)
        self.gauges: Dict[str, List[MetricValue]] = defaultdict(list)
        self.histograms: Dict[str, List[MetricValue]] = defaultdict(list)
        self.histogram_buckets = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
    
    def counter(self, name: str, value: float = 1, labels: Optional[Dict[str, str]] = None):
        """Increment counter."""
        full_name = f"{self.namespace}_{name}"
        self.counters[full_name].append(MetricValue(
            value=value,
            timestamp=time.time(),
            labels=labels or {}
        ))
    
    def gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set gauge value."""
        full_name = f"{self.namespace}_{name}"
        self.gauges[full_name].append(MetricValue(
            value=value,
            timestamp=time.time(),
            labels=labels or {}
        ))
    
    def histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record histogram observation."""
        full_name = f"{self.namespace}_{name}"
        self.histograms[full_name].append(MetricValue(
            value=value,
            timestamp=time.time(),
            labels=labels or {}
        ))
    
    @contextmanager
    def timer(self, name: str, labels: Optional[Dict[str, str]] = None):
        """Context manager for timing operations."""
        start = time.time()
        try:
            yield
        finally:
            duration = time.time() - start
            self.histogram(name, duration, labels)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics as dict."""
        return {
            'counters': {
                name: {
                    'total': sum(m.value for m in values),
                    'samples': len(values)
                }
                for name, values in self.counters.items()
            },
            'gauges': {
                name: {
                    'latest': values[-1].value if values else 0,
                    'samples': len(values)
                }
                for name, values in self.gauges.items()
            },
            'histograms': {
                name: self._calculate_histogram(values)
                for name, values in self.histograms.items()
            }
        }
    
    def _calculate_histogram(self, values: List[MetricValue]) -> Dict[str, Any]:
        """Calculate histogram statistics."""
        if not values:
            return {'count': 0, 'sum': 0, 'buckets': {}}
        
        vals = [v.value for v in values]
        buckets = {b: sum(1 for v in vals if v <= b) for b in self.histogram_buckets}
        
        return {
            'count': len(vals),
            'sum': sum(vals),
            'min': min(vals),
            'max': max(vals),
            'mean': sum(vals) / len(vals),
            'buckets': buckets
        }
    
    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        
        # Counters
        for name, values in self.counters.items():
            total = sum(m.value for m in values)
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name}_total {total}")
        
        # Gauges
        for name, values in self.gauges.items():
            latest = values[-1].value if values else 0
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {latest}")
        
        # Histograms
        for name, values in self.histograms.items():
            hist = self._calculate_histogram(values)
            lines.append(f"# TYPE {name} histogram")
            lines.append(f"{name}_count {hist['count']}")
            lines.append(f"{name}_sum {hist['sum']}")
            for bucket, count in hist['buckets'].items():
                lines.append(f'{name}_bucket{{le="{bucket}"}} {count}')
        
        return '\n'.join(lines)


class Tracer:
    """
    Distributed tracing for request flow tracking.
    
    Tracks spans across service boundaries.
    """
    
    def __init__(self, service_name: str = 'sentient-web'):
        self.service_name = service_name
        self.spans: List[Dict[str, Any]] = []
        self._current_trace: Optional[str] = None
    
    def start_trace(self, operation: str, **tags) -> str:
        """Start a new trace."""
        trace_id = str(uuid.uuid4())
        self._current_trace = trace_id
        
        span = {
            'trace_id': trace_id,
            'span_id': str(uuid.uuid4())[:8],
            'parent_id': None,
            'operation': operation,
            'service': self.service_name,
            'start_time': time.time(),
            'tags': tags,
            'logs': []
        }
        
        self.spans.append(span)
        return trace_id
    
    def start_span(self, operation: str, parent_id: Optional[str] = None, **tags) -> str:
        """Start a child span."""
        span_id = str(uuid.uuid4())[:8]
        
        span = {
            'trace_id': self._current_trace,
            'span_id': span_id,
            'parent_id': parent_id,
            'operation': operation,
            'service': self.service_name,
            'start_time': time.time(),
            'tags': tags,
            'logs': []
        }
        
        self.spans.append(span)
        return span_id
    
    def end_span(self, span_id: str, **tags):
        """End a span."""
        for span in self.spans:
            if span['span_id'] == span_id:
                span['end_time'] = time.time()
                span['duration_ms'] = (span['end_time'] - span['start_time']) * 1000
                span['tags'].update(tags)
                break
    
    def log_event(self, span_id: str, event: str, **fields):
        """Log event within a span."""
        for span in self.spans:
            if span['span_id'] == span_id:
                span['logs'].append({
                    'timestamp': time.time(),
                    'event': event,
                    'fields': fields
                })
                break
    
    @contextmanager
    def span(self, operation: str, **tags):
        """Context manager for spans."""
        span_id = self.start_span(operation, **tags)
        try:
            yield span_id
        finally:
            self.end_span(span_id)
    
    def get_trace(self, trace_id: str) -> List[Dict[str, Any]]:
        """Get all spans for a trace."""
        return [s for s in self.spans if s.get('trace_id') == trace_id]
    
    def export_jaeger(self) -> List[Dict[str, Any]]:
        """Export in Jaeger-compatible format."""
        return [
            {
                'traceID': s['trace_id'],
                'spanID': s['span_id'],
                'parentSpanID': s.get('parent_id'),
                'operationName': s['operation'],
                'startTime': int(s['start_time'] * 1e6),
                'duration': int(s.get('duration_ms', 0) * 1000),
                'tags': [{'key': k, 'value': v} for k, v in s.get('tags', {}).items()],
                'logs': [
                    {
                        'timestamp': int(l['timestamp'] * 1e6),
                        'fields': [{'key': k, 'value': v} for k, v in l['fields'].items()]
                    }
                    for l in s.get('logs', [])
                ]
            }
            for s in self.spans
        ]


def measure_performance(metric_name: str, collector: MetricsCollector):
    """Decorator to measure function performance."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with collector.timer(metric_name, {'function': func.__name__}):
                return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            with collector.timer(metric_name, {'function': func.__name__}):
                return func(*args, **kwargs)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


# Import asyncio for decorator
import asyncio
