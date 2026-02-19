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

__version__ = '2026.2.0-enterprise'

from .swarm_orchestrator import SwarmOrchestrator, SwarmConfig
from .agents import (
    SentientUIAgent,
    MXAgent,
    EmpathyAgent,
    PerformanceAgent,
    AmbientAgent,
    CodeReviewAgent,
)
from .api_clients import (
    UnifiedLLMClient,
    LLMProvider,
    GrafanaClient,
    PrometheusClient,
    OpenTelemetryClient,
    VercelClient,
)
from .observability import (
    EnterpriseMetrics,
    DistributedTracer,
    StructuredLogger,
)
from .resilience import (
    CircuitBreaker,
    CircuitState,
    FallbackChain,
    FallbackStrategy,
    Bulkhead,
    RetryPolicy,
)

__all__ = [
    'SwarmOrchestrator',
    'SwarmConfig',
    'SentientUIAgent',
    'MXAgent',
    'EmpathyAgent',
    'PerformanceAgent',
    'AmbientAgent',
    'CodeReviewAgent',
    'UnifiedLLMClient',
    'LLMProvider',
    'GrafanaClient',
    'PrometheusClient',
    'OpenTelemetryClient',
    'VercelClient',
    'EnterpriseMetrics',
    'DistributedTracer',
    'StructuredLogger',
    'CircuitBreaker',
    'CircuitState',
    'FallbackChain',
    'FallbackStrategy',
    'Bulkhead',
    'RetryPolicy',
]
