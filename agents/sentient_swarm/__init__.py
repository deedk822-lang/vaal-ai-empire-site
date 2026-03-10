"""
Vaal AI Empire - Enterprise Swarm System

Production-grade multi-agent system using your configured API stack:
- GLM5_API_KEY (Primary LLM)
- KIMI_API_KEY (Fallback LLM)
- DASHSCOPE_API_KEY (Secondary LLM)
- GRAFANA_API_KEY + PROMETHEUS_API_KEY (Observability)
- OPENTELEMETRY_API_KEY (Distributed tracing)
- CODERABBIT_API_KEY (Code review automation)
- OLLAMA_API_KEY (Local inference)
- VERCEL_TOKEN (Deployment)

Features:
- Parallel agent execution (true swarm)
- Multi-provider LLM fallback chain
- Real-time observability
- Automatic code review integration
- One-click deployment
"""

__version__ = "2026.2.0-enterprise"

from .agents import (
    AmbientAgent,
    CodeReviewAgent,
    EmpathyAgent,
    MXAgent,
    PerformanceAgent,
    SentientUIAgent,
)
from .api_clients import (
    GrafanaClient,
    LLMProvider,
    OpenTelemetryClient,
    PrometheusClient,
    UnifiedLLMClient,
    VercelClient,
)
from .observability import (
    DistributedTracer,
    EnterpriseMetrics,
    StructuredLogger,
)
from .resilience import (
    Bulkhead,
    CircuitBreaker,
    CircuitState,
    FallbackChain,
    FallbackStrategy,
    RetryPolicy,
)
from .swarm_orchestrator import SwarmConfig, SwarmOrchestrator

__all__ = [
    "SwarmOrchestrator",
    "SwarmConfig",
    "SentientUIAgent",
    "MXAgent",
    "EmpathyAgent",
    "PerformanceAgent",
    "AmbientAgent",
    "CodeReviewAgent",
    "UnifiedLLMClient",
    "LLMProvider",
    "GrafanaClient",
    "PrometheusClient",
    "OpenTelemetryClient",
    "VercelClient",
    "EnterpriseMetrics",
    "DistributedTracer",
    "StructuredLogger",
    "CircuitBreaker",
    "CircuitState",
    "FallbackChain",
    "FallbackStrategy",
    "Bulkhead",
    "RetryPolicy",
]
