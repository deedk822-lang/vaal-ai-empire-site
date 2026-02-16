"""
Enterprise metrics collection with Prometheus/Grafana export.
"""

import time
from collections import defaultdict
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class MetricValue:
    name: str
    value: float
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)


class EnterpriseMetrics:
    """
    Metrics collector with Prometheus-compatible export.
    Uses PROMETHEUS_API_KEY and GRAFANA_API_KEY.
    """
    
    def __init__(self, namespace: str = "sentient_swarm"):
        self.namespace = namespace
        self.counters: Dict[str, List[MetricValue]] = defaultdict(list)
        self.gauges: Dict[str, List[MetricValue]] = defaultdict(list)
        self.histograms: Dict[str, List[MetricValue]] = defaultdict(list)
        
        # Buckets for histograms (Prometheus defaults)
        self.buckets = [.005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10]
    
    def counter(self, name: str, value: float = 1, labels: Optional[Dict[str, str]] = None):
        """Record counter increment."""
        full_name = f"{self.namespace}_{name}_total"
        self.counters[full_name].append(MetricValue(
            name=full_name,
            value=value,
            timestamp=time.time(),
            labels=labels or {}
        ))
    
    def gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record gauge value."""
        full_name = f"{self.namespace}_{name}"
        self.gauges[full_name].append(MetricValue(
            name=full_name,
            value=value,
            timestamp=time.time(),
            labels=labels or {}
        ))
    
    def histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record histogram observation."""
        full_name = f"{self.namespace}_{name}_seconds"
        self.histograms[full_name].append(MetricValue(
            name=full_name,
            value=value,
            timestamp=time.time(),
            labels=labels or {}
        ))
    
    def timer(self, name: str):
        """Context manager for timing."""
        return TimerContext(self, name)
    
    def export_prometheus(self) -> str:
        """Export in Prometheus text format."""
        lines = []
        
        # Counters
        for name, values in self.counters.items():
            if not values:
                continue
            lines.append(f"# TYPE {name} counter")
            total = sum(v.value for v in values)
            lines.append(f"{name} {total}")
        
        # Gauges - only export latest
        for name, values in self.gauges.items():
            if not values:
                continue
            lines.append(f"# TYPE {name} gauge")
            latest = values[-1]
            if latest.labels:
                label_str = ",".join([f'{k}="{v}"' for k, v in latest.labels.items()])
                lines.append(f'{name}{{{label_str}}} {latest.value}')
            else:
                lines.append(f"{name} {latest.value}")
        
        # Histograms
        for name, values in self.histograms.items():
            if not values:
                continue
            
            lines.append(f"# TYPE {name} histogram")
            
            vals = [v.value for v in values]
            total = sum(vals)
            count = len(vals)
            
            # Buckets
            for bucket in self.buckets:
                bucket_count = sum(1 for v in vals if v <= bucket)
                lines.append(f'{name}_bucket{{le="{bucket}"}} {bucket_count}')
            
            # +Inf bucket
            lines.append(f'{name}_bucket{{le="+Inf"}} {count}')
            lines.append(f"{name}_sum {total}")
            lines.append(f"{name}_count {count}")
        
        return "\n".join(lines)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        return {
            "counters": {
                k: sum(v.value for v in vals)
                for k, vals in self.counters.items()
            },
            "gauges": {
                k: vals[-1].value if vals else 0
                for k, vals in self.gauges.items()
            },
            "histograms": {
                k: {
                    "count": len(vals),
                    "avg": sum(v.value for v in vals) / len(vals) if vals else 0
                }
                for k, vals in self.histograms.items()
            }
        }


class TimerContext:
    """Context manager for timing operations."""
    
    def __init__(self, metrics: EnterpriseMetrics, name: str):
        self.metrics = metrics
        self.name = name
        self.start = None
    
    def __enter__(self):
        self.start = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start
        self.metrics.histogram(self.name, duration)
