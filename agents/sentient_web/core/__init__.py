"""
Core infrastructure for +AAA Digital Preeminence implementation.

This module provides enterprise-grade:
- Circuit breakers for API resilience
- Real code generation and validation
- Actual performance benchmarking
- Security scanning
- Comprehensive observability
"""

from .api_client import CircuitBreaker, GLM5Client, RetryPolicy
from .benchmark import AXEAccessibilityRunner, LighthouseRunner, RealBenchmarkRunner
from .code_generator import CodeGenerator, CSSGenerator, JSGenerator
from .observability import MetricsCollector, StructuredLogger
from .resilience import FallbackChain, GracefulDegradation
from .validator import CodeValidator, SecurityScanner

__all__ = [
    "GLM5Client",
    "CircuitBreaker",
    "RetryPolicy",
    "CodeGenerator",
    "CSSGenerator",
    "JSGenerator",
    "RealBenchmarkRunner",
    "LighthouseRunner",
    "AXEAccessibilityRunner",
    "CodeValidator",
    "SecurityScanner",
    "FallbackChain",
    "GracefulDegradation",
    "MetricsCollector",
    "StructuredLogger",
]
