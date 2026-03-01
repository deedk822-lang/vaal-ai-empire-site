"""
Enterprise metrics collection with Prometheus/Grafana export.
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


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
        self.buckets = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]

    def counter(
        self, name: str, value: float = 1, labels: Optional[Dict[str, str]] = None
    ):
        """Record counter increment."""
        full_name = f"{self.namespace}_{name}_total"
        self.counters[full_name].append(
            MetricValue(
                name=full_name, value=value, timestamp=time.time(), labels=labels or {}
            )
        )

    def gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record gauge value."""
        full_name = f"{self.namespace}_{name}"
        self.gauges[full_name].append(
            MetricValue(
                name=full_name, value=value, timestamp=time.time(), labels=labels or {}
            )
        )

    def histogram(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ):
        """Record histogram observation."""
        full_name = f"{self.namespace}_{name}_seconds"
        self.histograms[full_name].append(
            MetricValue(
                name=full_name, value=value, timestamp=time.time(), labels=labels or {}
            )
        )

    def timer(self, name: str):
        """Context manager for timing."""
        return TimerContext(self, name)

    def _format_labels(self, labels: Dict[str, str]) -> str:
        """Format labels for Prometheus."""
        if not labels:
            return ""
        return ",".join([f'{k}="{v}"' for k, v in labels.items()])

    def export_prometheus(self) -> str:
        """Export in Prometheus text format with proper label handling."""
        lines = []

        # Counters - group by label set
        for name, values in self.counters.items():
            if not values:
                continue
            lines.append(f"# TYPE {name} counter")

            # Group by label set
            by_labels: Dict[str, float] = defaultdict(float)
            for v in values:
                label_key = self._format_labels(v.labels)
                by_labels[label_key] += v.value

            for label_str, total in by_labels.items():
                if label_str:
                    lines.append(f"{name}{{{label_str}}} {total}")
                else:
                    lines.append(f"{name} {total}")

        # Gauges - group by label set, use latest
        for name, values in self.gauges.items():
            if not values:
                continue
            lines.append(f"# TYPE {name} gauge")

            # Group by label set, keep latest
            by_labels: Dict[str, MetricValue] = {}
            for v in values:
                label_key = self._format_labels(v.labels)
                by_labels[label_key] = v  # Later values overwrite earlier

            for label_str, v in by_labels.items():
                if label_str:
                    lines.append(f"{name}{{{label_str}}} {v.value}")
                else:
                    lines.append(f"{name} {v.value}")

        # Histograms - group by label set
        for name, values in self.histograms.items():
            if not values:
                continue
            lines.append(f"# TYPE {name} histogram")

            # Group by label set
            by_labels: Dict[str, List[float]] = defaultdict(list)
            for v in values:
                label_key = self._format_labels(v.labels)
                by_labels[label_key].append(v.value)

            for label_str, vals in by_labels.items():
                total = sum(vals)
                count = len(vals)

                # Buckets
                for bucket in self.buckets:
                    bucket_count = sum(1 for v in vals if v <= bucket)
                    if label_str:
                        lines.append(
                            f'{name}_bucket{{{label_str},le="{bucket}"}} {bucket_count}'
                        )
                    else:
                        lines.append(f'{name}_bucket{{le="{bucket}"}} {bucket_count}')

                # +Inf bucket
                if label_str:
                    lines.append(f'{name}_bucket{{{label_str},le="+Inf"}} {count}')
                    lines.append(f"{name}_sum{{{label_str}}} {total}")
                    lines.append(f"{name}_count{{{label_str}}} {count}")
                else:
                    lines.append(f'{name}_bucket{{le="+Inf"}} {count}')
                    lines.append(f"{name}_sum {total}")
                    lines.append(f"{name}_count {count}")

        return "\n".join(lines)

    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        return {
            "counters": {
                k: sum(v.value for v in vals) for k, vals in self.counters.items()
            },
            "gauges": {
                k: vals[-1].value if vals else 0 for k, vals in self.gauges.items()
            },
            "histograms": {
                k: {
                    "count": len(vals),
                    "avg": sum(v.value for v in vals) / len(vals) if vals else 0,
                }
                for k, vals in self.histograms.items()
            },
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
