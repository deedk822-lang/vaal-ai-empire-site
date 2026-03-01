"""
Digital Preeminence 2026 - +AAA Sentient Web Agents

Production-grade implementation with enterprise reliability:
- Real GLM-5 API integration with circuit breakers
- Actual file generation (CSS/JS/HTML/JSON)
- Live benchmarking with Lighthouse/axe-core
- Comprehensive observability (metrics, logs, traces)
- Fault tolerance and automatic fallbacks

Example:
    import asyncio
    from agents.sentient_web import DigitalPreeminenceOrchestrator

    async def main():
        orchestrator = DigitalPreeminenceOrchestrator()

        try:
            report = await orchestrator.achieve_preeminence({
                'project': 'my-site',
                'target': 'sentient_web',
                'run_benchmarks': True,
                'benchmark_url': 'http://localhost:8080'
            })

            print(f"Score: {report.overall_score}/100")
            print(f"Status: {report.award_status}")

            # Access observability
            print(orchestrator.get_metrics_report())

        finally:
            await orchestrator.cleanup()

    asyncio.run(main())
"""

__version__ = "2026.1.0+aaa"
__author__ = "Vaal AI Empire"

# Core infrastructure
from .core.api_client import (
    APIResponse,
    CircuitBreaker,
    CircuitBreakerOpenError,
    GLM5Client,
    RetryPolicy,
)
from .core.benchmark import (
    AXEAccessibilityRunner,
    BenchmarkMetric,
    BenchmarkResult,
    LighthouseRunner,
    RealBenchmarkRunner,
)
from .core.code_generator import (
    CodeGenerator,
    CSSGenerator,
    GeneratedFile,
    GenerationResult,
    JSGenerator,
)
from .core.observability import (
    MetricsCollector,
    StructuredLogger,
    Tracer,
    measure_performance,
)
from .core.resilience import (
    Bulkhead,
    BulkheadFullError,
    BulkheadTimeoutError,
    CachedResponseFallback,
    FallbackChain,
    FallbackStrategy,
    GracefulDegradation,
    HealthCheck,
    HealthChecker,
    HealthStatus,
    LocalTemplateFallback,
    SimplifiedGenerationFallback,
)
from .core.validator import (
    CodeValidator,
    SecurityScanner,
    ValidationIssue,
    ValidationResult,
)

# Main orchestrator
from .orchestrator import (
    AmbientAgent,
    DigitalPreeminenceOrchestrator,
    EmpathyAgent,
    GLM5AwardEvaluator,
    MXAgent,
    PerfAgent,
    PreeminenceReport,
    SentientUIAgent,
    SwarmResult,
)

__all__ = [
    # Core API
    "GLM5Client",
    "CircuitBreaker",
    "CircuitBreakerOpenError",
    "RetryPolicy",
    "APIResponse",
    # Code Generation
    "CodeGenerator",
    "CSSGenerator",
    "JSGenerator",
    "GeneratedFile",
    "GenerationResult",
    # Benchmarking
    "RealBenchmarkRunner",
    "LighthouseRunner",
    "AXEAccessibilityRunner",
    "BenchmarkResult",
    "BenchmarkMetric",
    # Validator
    "CodeValidator",
    "SecurityScanner",
    "ValidationIssue",
    "ValidationResult",
    # Resilience
    "FallbackChain",
    "FallbackStrategy",
    "LocalTemplateFallback",
    "CachedResponseFallback",
    "SimplifiedGenerationFallback",
    "Bulkhead",
    "BulkheadFullError",
    "BulkheadTimeoutError",
    "HealthChecker",
    "HealthStatus",
    "HealthCheck",
    "GracefulDegradation",
    # Observability
    "StructuredLogger",
    "MetricsCollector",
    "Tracer",
    "measure_performance",
    # Agents
    "DigitalPreeminenceOrchestrator",
    "SentientUIAgent",
    "MXAgent",
    "EmpathyAgent",
    "PerfAgent",
    "AmbientAgent",
    "GLM5AwardEvaluator",
    "SwarmResult",
    "PreeminenceReport",
]
