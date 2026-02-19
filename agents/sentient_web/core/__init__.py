"""
Core infrastructure for +AAA Digital Preeminence implementation.

This module provides enterprise-grade:
- Circuit breakers for API resilience
- Real code generation and validation
- Actual performance benchmarking
- Security scanning
- Comprehensive observability
"""

from .api_client import GLM5Client, CircuitBreaker, RetryPolicy
from .code_generator import CodeGenerator, CSSGenerator, JSGenerator
from .benchmark import RealBenchmarkRunner, LighthouseRunner, AXEAccessibilityRunner
from .validator import CodeValidator, SecurityScanner
from .resilience import FallbackChain, GracefulDegradation
from .observability import MetricsCollector, StructuredLogger

__all__ = [
    'GLM5Client',
    'CircuitBreaker',
    'RetryPolicy',
    'CodeGenerator',
    'CSSGenerator',
    'JSGenerator',
    'RealBenchmarkRunner',
    'LighthouseRunner',
    'AXEAccessibilityRunner',
    'CodeValidator',
    'SecurityScanner',
    'FallbackChain',
    'GracefulDegradation',
    'MetricsCollector',
    'StructuredLogger',
]
