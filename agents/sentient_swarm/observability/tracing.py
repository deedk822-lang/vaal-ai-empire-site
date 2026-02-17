"""
Distributed tracing using OPENTELEMETRY_API_KEY.
"""

import os
import uuid
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class Span:
    trace_id: str
    span_id: str
    parent_id: Optional[str]
    operation: str
    start_time: float
    end_time: Optional[float] = None
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict] = field(default_factory=list)


class DistributedTracer:
    """Distributed tracing for swarm operations."""
    
    def __init__(self, service_name: str = "sentient-swarm"):
        self.service_name = service_name
        self.spans: List[Span] = []
        self.otlp_key = os.getenv('OPENTELEMETRY_API_KEY')
    
    def start_trace(self, operation: str, **tags) -> str:
        """Start a new trace."""
        trace_id = str(uuid.uuid4())
        span = Span(
            trace_id=trace_id,
            span_id=str(uuid.uuid4())[:8],
            parent_id=None,
            operation=operation,
            start_time=time.time(),
            tags=tags
        )
        self.spans.append(span)
        return trace_id
    
    def start_span(self, operation: str, parent_id: Optional[str] = None, **tags) -> str:
        """Start a child span."""
        span_id = str(uuid.uuid4())[:8]
        span = Span(
            trace_id=self._get_current_trace_id(),
            span_id=span_id,
            parent_id=parent_id,
            operation=operation,
            start_time=time.time(),
            tags=tags
        )
        self.spans.append(span)
        return span_id
    
    def end_span(self, span_id: str):
        """End a span."""
        for span in self.spans:
            if span.span_id == span_id:
                span.end_time = time.time()
                break
    
    def _get_current_trace_id(self) -> str:
        """Get current trace ID."""
        for span in reversed(self.spans):
            if span.parent_id is None:
                return span.trace_id
        return str(uuid.uuid4())
    
    def get_trace(self, trace_id: str) -> List[Span]:
        """Get all spans for a trace."""
        return [s for s in self.spans if s.trace_id == trace_id]
    
    def export_jaeger(self) -> List[Dict]:
        """Export in Jaeger format."""
        return [
            {
                "traceID": s.trace_id,
                "spanID": s.span_id,
                "parentSpanID": s.parent_id,
                "operationName": s.operation,
                "startTime": int(s.start_time * 1e6),
                "duration": int((s.end_time - s.start_time) * 1e6) if s.end_time else 0,
                "tags": [{"key": k, "value": v} for k, v in s.tags.items()]
            }
            for s in self.spans
        ]
