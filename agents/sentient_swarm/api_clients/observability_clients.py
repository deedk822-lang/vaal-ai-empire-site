"""
Observability clients using your configured API keys:
- GRAFANA_API_KEY
- PROMETHEUS_API_KEY  
- OPENTELEMETRY_API_KEY
"""

import os
import json
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class MetricPoint:
    name: str
    value: float
    timestamp: float
    labels: Dict[str, str]


class GrafanaClient:
    """Client for Grafana Cloud annotations and dashboards."""
    
    def __init__(self, api_key: Optional[str] = None, url: Optional[str] = None):
        self.api_key = api_key or os.getenv('GRAFANA_API_KEY')
        self.url = url or os.getenv('GRAFANA_URL', 'https://vaalai.grafana.net')
        self.metrics_buffer: List[MetricPoint] = []
    
    async def annotate(self, text: str, tags: Optional[List[str]] = None) -> bool:
        """Create annotation in Grafana."""
        if not self.api_key:
            return False
        
        try:
            import aiohttp
            
            annotation = {
                "text": text,
                "tags": tags or ["swarm", "deployment"],
                "time": int(time.time() * 1000)
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.url}/api/annotations",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=annotation
                ) as resp:
                    return resp.status == 200
        except Exception as e:
            print(f"Grafana annotation failed: {e}")
            return False
    
    def buffer_metric(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Buffer metric for batch sending."""
        self.metrics_buffer.append(MetricPoint(
            name=name,
            value=value,
            timestamp=time.time(),
            labels=labels or {}
        ))
    
    async def flush_metrics(self) -> bool:
        """Send buffered metrics to Grafana."""
        if not self.metrics_buffer or not self.api_key:
            return False
        
        # In production, this would send to Grafana Cloud
        # For now, just clear buffer
        self.metrics_buffer.clear()
        return True


class PrometheusClient:
    """Client for Prometheus remote write."""
    
    def __init__(self, api_key: Optional[str] = None, url: Optional[str] = None):
        self.api_key = api_key or os.getenv('PROMETHEUS_API_KEY')
        self.url = url or os.getenv('PROMETHEUS_URL', 'https://prometheus-prod-01-eu-west-0.grafana.net/api/prom')
        self.metrics: Dict[str, List[MetricPoint]] = {}
    
    def record(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a metric."""
        if name not in self.metrics:
            self.metrics[name] = []
        
        self.metrics[name].append(MetricPoint(
            name=name,
            value=value,
            timestamp=time.time(),
            labels=labels or {}
        ))
    
    def counter(self, name: str, value: float = 1, labels: Optional[Dict[str, str]] = None):
        """Increment counter."""
        self.record(name, value, labels)
    
    def gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set gauge."""
        self.record(name, value, labels)
    
    def histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record histogram observation."""
        self.record(f"{name}_bucket", value, labels)
    
    def export_prometheus_format(self) -> str:
        """Export metrics in Prometheus text format."""
        lines = []
        
        for name, points in self.metrics.items():
            if not points:
                continue
            
            # Type annotation (simplified)
            lines.append(f"# TYPE {name} gauge")
            
            # Latest value for each label set
            latest = {}
            for p in points:
                label_key = json.dumps(p.labels, sort_keys=True)
                latest[label_key] = p
            
            for label_key, point in latest.items():
                if point.labels:
                    label_str = ",".join([f'{k}="{v}"' for k, v in point.labels.items()])
                    lines.append(f'{name}{{{label_str}}} {point.value}')
                else:
                    lines.append(f'{name} {point.value}')
        
        return "\n".join(lines)
    
    async def remote_write(self) -> bool:
        """Send metrics to Prometheus remote write endpoint."""
        if not self.api_key:
            return False
        
        # Convert to Prometheus remote write format
        # This is a simplified version - production would use protobuf
        try:
            import aiohttp
            
            data = self.export_prometheus_format()
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.url}/push",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "text/plain"
                    },
                    data=data
                ) as resp:
                    return resp.status == 200
        except Exception as e:
            print(f"Prometheus remote write failed: {e}")
            return False
    
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        return {
            name: {
                "count": len(points),
                "latest": points[-1].value if points else 0,
                "min": min(p.value for p in points) if points else 0,
                "max": max(p.value for p in points) if points else 0,
            }
            for name, points in self.metrics.items()
        }


class OpenTelemetryClient:
    """Client for OpenTelemetry traces."""
    
    def __init__(self, api_key: Optional[str] = None, endpoint: Optional[str] = None):
        self.api_key = api_key or os.getenv('OPENTELEMETRY_API_KEY')
        self.endpoint = endpoint or os.getenv('OTEL_ENDPOINT', 'https://tempo-eu-west-0.grafana.net')
        self.traces: List[Dict] = []
    
    def start_span(self, name: str, parent_id: Optional[str] = None, **attributes) -> str:
        """Start a new span."""
        import uuid
        
        span_id = str(uuid.uuid4())[:16]
        
        span = {
            "trace_id": str(uuid.uuid4()),
            "span_id": span_id,
            "parent_span_id": parent_id,
            "name": name,
            "start_time": int(time.time() * 1e9),  # nanoseconds
            "attributes": attributes,
            "status": "ok"
        }
        
        self.traces.append(span)
        return span_id
    
    def end_span(self, span_id: str, **attributes):
        """End a span."""
        for span in self.traces:
            if span.get("span_id") == span_id:
                span["end_time"] = int(time.time() * 1e9)
                span["attributes"].update(attributes)
                break
    
    def add_event(self, span_id: str, name: str, **attributes):
        """Add event to span."""
        for span in self.traces:
            if span.get("span_id") == span_id:
                if "events" not in span:
                    span["events"] = []
                span["events"].append({
                    "name": name,
                    "timestamp": int(time.time() * 1e9),
                    "attributes": attributes
                })
                break
    
    async def export(self) -> bool:
        """Export traces to OTLP endpoint."""
        if not self.api_key or not self.traces:
            return False
        
        try:
            import aiohttp
            
            # OTLP JSON format
            payload = {
                "resourceSpans": [{
                    "resource": {
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": "sentient-swarm"}}
                        ]
                    },
                    "scopeSpans": [{
                        "spans": self.traces
                    }]
                }]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.endpoint}/v1/traces",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload
                ) as resp:
                    if resp.status == 200:
                        self.traces.clear()
                        return True
                    return False
        except Exception as e:
            print(f"OTel export failed: {e}")
            return False
    
    def get_traces(self) -> List[Dict]:
        """Get all traces."""
        return self.traces.copy()
