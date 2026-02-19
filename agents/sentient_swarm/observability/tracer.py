"""
Distributed tracing with OpenTelemetry.
Uses OPENTELEMETRY_API_KEY.
"""

import time
import uuid
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class Span:
    trace_id: str
    span_id: str
    parent_id: Optional[str]
    name: str
    start_time: float
    end_time: Optional[float] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict] = field(default_factory=list)
    status: str = "ok"


class DistributedTracer:
    """Distributed tracer compatible with OpenTelemetry."""
    
    def __init__(self, service_name: str = "sentient-swarm"):
        self.service_name = service_name
        self.spans: List[Span] = []
        self.current_trace: Optional[str] = None
    
    def start_trace(self, name: str, **attributes) -> str:
        """Start a new distributed trace."""
        trace_id = str(uuid.uuid4())
        self.current_trace = trace_id
        
        span = self.start_span(name, **attributes)
        return trace_id
    
    def start_span(self, name: str, parent_id: Optional[str] = None, **attributes) -> str:
        """Start a span within the current trace."""
        span_id = str(uuid.uuid4())[:16]
        
        span = Span(
            trace_id=self.current_trace or str(uuid.uuid4()),
            span_id=span_id,
            parent_id=parent_id,
            name=name,
            start_time=time.time(),
            attributes=attributes
        )
        
        self.spans.append(span)
        return span_id
    
    def end_span(self, span_id: str, **attributes):
        """End a span."""
        for span in self.spans:
            if span.span_id == span_id:
                span.end_time = time.time()
                span.attributes.update(attributes)
                break
    
    def add_event(self, span_id: str, name: str, **attributes):
        """Add event to a span."""
        for span in self.spans:
            if span.span_id == span_id:
                span.events.append({
                    "name": name,
                    "timestamp": time.time(),
                    "attributes": attributes
                })
                break
    
    def get_trace(self, trace_id: str) -> List[Span]:
        """Get all spans for a trace."""
        return [s for s in self.spans if s.trace_id == trace_id]
    
    def export_otlp(self) -> Dict[str, Any]:
        """Export in OTLP format."""
        return {
            "resourceSpans": [{
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": self.service_name}}
                    ]
                },
                "scopeSpans": [{
                    "spans": [
                        {
                            "traceId": s.trace_id.replace("-", ""),
                            "spanId": s.span_id,
                            "parentSpanId": s.parent_id.replace("-", "") if s.parent_id else None,
                            "name": s.name,
                            "startTimeUnixNano": int(s.start_time * 1e9),
                            "endTimeUnixNano": int(s.end_time * 1e9) if s.end_time else None,
                            "attributes": [
                                {"key": k, "value": {"stringValue": str(v)}}
                                for k, v in s.attributes.items()
                            ],
                            "events": [
                                {
                                    "name": e["name"],
                                    "timeUnixNano": int(e["timestamp"] * 1e9),
                                    "attributes": [
                                        {"key": k, "value": {"stringValue": str(v)}}
                                        for k, v in e["attributes"].items()
                                    ]
                                }
                                for e in s.events
                            ],
                            "status": {"code": s.status}
                        }
                        for s in self.spans
                    ]
                }]
            }]
        }
    
    def clear(self):
        """Clear all spans."""
        self.spans.clear()
