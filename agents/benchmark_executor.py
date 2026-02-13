#!/usr/bin/env python3
"""
Vaal AI Empire - Benchmark Executor

A professional benchmark suite extending CodingAgentExecutor for AI model evaluation.
Provides quantitative and qualitative metrics for code generation, security analysis,
and performance testing.

Features:
- Extends CodingAgentExecutor for code execution benchmarks
- 50+ test cases covering security, efficiency, and edge cases
- Prometheus metrics integration for monitoring
- GLM-5 API integration for qualitative evaluation
- CI/CD compatible with GitHub Actions

Usage:
    # Run full benchmark suite
    python agents/benchmark_executor.py --run-all
    
    # Run specific category
    python agents/benchmark_executor.py --category security
    
    # Generate report
    python agents/benchmark_executor.py --report
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import asyncio
import statistics
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from enum import Enum

# Import base executor
try:
    from coding_agent_executor import CodingAgentExecutor, CodeExecutionResult, AgentResponse
    _HAS_BASE_CLASS = True
except ImportError:
    # Fallback for standalone execution - define placeholder classes
    _HAS_BASE_CLASS = False
    CodingAgentExecutor = None
    CodeExecutionResult = None
    AgentResponse = None


class BenchmarkCategory(Enum):
    """Categories of benchmark tests."""
    SECURITY = "security"
    EFFICIENCY = "efficiency"
    EDGE_CASES = "edge_cases"
    CODE_GENERATION = "code_generation"
    REFACTORING = "refactoring"
    DEBUGGING = "debugging"


@dataclass
class BenchmarkResult:
    """Result of a single benchmark test."""
    test_id: str
    test_name: str
    category: str
    passed: bool
    execution_time_ms: float
    response_time_ms: float
    tokens_used: int = 0
    error_message: Optional[str] = None
    code_executed: bool = False
    execution_success: bool = False
    quality_score: float = 0.0  # GLM-5 quality evaluation
    security_score: float = 0.0
    efficiency_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkReport:
    """Comprehensive benchmark report."""
    timestamp: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    avg_execution_time_ms: float
    avg_response_time_ms: float
    total_tokens_used: int
    category_scores: Dict[str, float]
    results: List[BenchmarkResult]
    overall_score: float = 0.0


class BenchmarkExecutor:
    """
    Professional benchmark suite extending CodingAgentExecutor.
    
    Provides comprehensive evaluation of AI coding capabilities including:
    - Security vulnerability detection
    - Code efficiency analysis
    - Edge case handling
    - Code generation quality
    - Refactoring capabilities
    - Debugging accuracy
    
    Integrates with:
    - Prometheus for metrics
    - GLM-5 for qualitative evaluation
    - GitHub Actions for CI/CD
    """
    
    # Quality evaluation prompt for GLM-5
    QUALITY_EVALUATION_PROMPT = """Evaluate the following AI-generated code response on a scale of 0-10 for:

1. **Correctness** (0-10): Does the code solve the problem correctly?
2. **Security** (0-10): Is the code secure? Any vulnerabilities?
3. **Efficiency** (0-10): Is the code efficient? Any performance issues?
4. **Readability** (0-10): Is the code well-structured and documented?
5. **Best Practices** (0-10): Does it follow coding standards?

Respond with a JSON object: {"correctness": N, "security": N, "efficiency": N, "readability": N, "best_practices": N}"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        benchmark_data_path: str = "benchmark_data/test_cases.json",
        enable_code_execution: bool = True,
        execution_timeout: int = 60,
        enable_quality_evaluation: bool = True,
        glm5_api_key: Optional[str] = None,
        prometheus_enabled: bool = True
    ):
        """Initialize the BenchmarkExecutor."""
        # Initialize parent class if available
        if _HAS_BASE_CLASS and CodingAgentExecutor is not None:
            # Initialize as subclass
            CodingAgentExecutor.__init__(
                self,
                api_key=api_key,
                enable_code_execution=enable_code_execution,
                execution_timeout=execution_timeout
            )
        else:
            self.api_key = api_key
            self.enable_code_execution = enable_code_execution
            self.execution_timeout = execution_timeout
        
        self.benchmark_data_path = Path(benchmark_data_path)
        self.enable_quality_evaluation = enable_quality_evaluation
        self.glm5_api_key = glm5_api_key or os.getenv("GLM5_API_KEY")
        self.prometheus_enabled = prometheus_enabled
        
        # Benchmark state
        self.test_cases: List[Dict] = []
        self.results: List[BenchmarkResult] = []
        self.start_time: Optional[datetime] = None
        
        # Prometheus metrics (if available)
        self._setup_prometheus_metrics()
        
        # Load test cases
        self._load_test_cases()
    
    def _setup_prometheus_metrics(self):
        """Setup Prometheus metrics for benchmark monitoring."""
        self.prometheus_metrics = {}
        
        if not self.prometheus_enabled:
            return
        
        try:
            import prometheus_client as prom
            
            # Benchmark-specific metrics
            self.prometheus_metrics = {
                'benchmark_tests_total': prom.Counter(
                    'vaal_benchmark_tests_total',
                    'Total number of benchmark tests executed',
                    ['category', 'status']
                ),
                'benchmark_duration_seconds': prom.Histogram(
                    'vaal_benchmark_duration_seconds',
                    'Duration of benchmark tests in seconds',
                    ['category'],
                    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60]
                ),
                'benchmark_quality_score': prom.Gauge(
                    'vaal_benchmark_quality_score',
                    'Quality score of benchmark results',
                    ['category']
                ),
                'benchmark_tokens_used': prom.Counter(
                    'vaal_benchmark_tokens_used_total',
                    'Total tokens used in benchmark tests',
                    ['category']
                ),
            }
        except ImportError:
            self.prometheus_enabled = False
    
    def _load_test_cases(self):
        """Load test cases from JSON file."""
        if self.benchmark_data_path.exists():
            with open(self.benchmark_data_path, 'r') as f:
                data = json.load(f)
                self.test_cases = data.get('test_cases', [])
        else:
            # Use default test cases if file not found
            self.test_cases = self._get_default_test_cases()
    
    def _get_default_test_cases(self) -> List[Dict]:
        """Get default test cases if no file is found."""
        return [
            {
                "id": "SEC001",
                "name": "SQL Injection Detection",
                "category": "security",
                "prompt": "Write a Python function to safely query a user by ID from a database",
                "expected_patterns": ["parameterized", "prepared statement", "cursor.execute"],
                "security_check": True,
                "difficulty": "medium"
            },
            {
                "id": "SEC002",
                "name": "XSS Prevention",
                "category": "security",
                "prompt": "Create a function to sanitize user input for HTML display",
                "expected_patterns": ["escape", "html.escape", "sanitize"],
                "security_check": True,
                "difficulty": "medium"
            },
            {
                "id": "EFF001",
                "name": "Algorithm Efficiency - Sorting",
                "category": "efficiency",
                "prompt": "Implement an efficient sorting algorithm for large datasets",
                "expected_patterns": ["O(n log n)", "quicksort", "mergesort"],
                "time_limit_ms": 1000,
                "difficulty": "hard"
            },
            {
                "id": "EDGE001",
                "name": "Empty Input Handling",
                "category": "edge_cases",
                "prompt": "Write a function to find the maximum value in a list",
                "test_inputs": [[], [1], [1, 2, 3], [-1, -2, -3]],
                "expected_outputs": [None, 1, 3, -1],
                "difficulty": "easy"
            }
        ]
    
    def _evaluate_with_glm5(self, prompt: str, response: str) -> Dict[str, float]:
        """Evaluate response quality using GLM-5 API."""
        if not self.glm5_api_key:
            return {"correctness": 5.0, "security": 5.0, "efficiency": 5.0, "readability": 5.0, "best_practices": 5.0}
        
        try:
            import requests
            
            eval_prompt = f"{self.QUALITY_EVALUATION_PROMPT}\n\nOriginal Prompt:\n{prompt}\n\nAI Response:\n{response}"
            
            response = requests.post(
                "https://open.bigmodel.cn/api/paas/v3/model-api/chatglm_pro/invoke",
                headers={
                    "Authorization": f"Bearer {self.glm5_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "prompt": eval_prompt,
                    "max_tokens": 200
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get('data', {}).get('content', '{}')
                # Parse JSON from response
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
        except Exception as e:
            print(f"GLM-5 evaluation error: {e}")
        
        return {"correctness": 5.0, "security": 5.0, "efficiency": 5.0, "readability": 5.0, "best_practices": 5.0}
    
    def _check_security_patterns(self, response: str, expected_patterns: List[str]) -> float:
        """Check for security patterns in the response."""
        if not expected_patterns:
            return 10.0
        
        response_lower = response.lower()
        matches = sum(1 for pattern in expected_patterns if pattern.lower() in response_lower)
        return (matches / len(expected_patterns)) * 10.0
    
    def _check_efficiency(self, response: str, time_taken_ms: float, time_limit_ms: Optional[int]) -> float:
        """Check efficiency of the response."""
        score = 10.0
        
        # Check time limit
        if time_limit_ms and time_taken_ms > time_limit_ms:
            score -= 5.0
        
        # Check for efficiency-related terms
        efficiency_terms = ['efficient', 'optimized', 'o(n', 'o(log', 'cache', 'memoiz']
        response_lower = response.lower()
        if any(term in response_lower for term in efficiency_terms):
            score = min(10.0, score + 1.0)
        
        return max(0.0, score)
    
    async def run_single_test(self, test_case: Dict) -> BenchmarkResult:
        """Run a single benchmark test."""
        start_time = time.time()
        
        test_id = test_case.get('id', 'unknown')
        test_name = test_case.get('name', 'Unknown Test')
        category = test_case.get('category', 'general')
        prompt = test_case.get('prompt', '')
        
        try:
            # Get response from agent
            response_start = time.time()
            
            if hasattr(self, 'chat'):
                response = self.chat(prompt, stream=False, execute_code=True)
                response_text = response.content
                execution_result = response.execution_result
            else:
                # Fallback if parent class not available
                response_text = f"Mock response for: {prompt}"
                execution_result = None
            
            response_time_ms = (time.time() - response_start) * 1000
            
            # Evaluate quality
            quality_scores = {"correctness": 5.0, "security": 5.0, "efficiency": 5.0, "readability": 5.0, "best_practices": 5.0}
            if self.enable_quality_evaluation:
                quality_scores = self._evaluate_with_glm5(prompt, response_text)
            
            # Check security patterns
            security_score = self._check_security_patterns(
                response_text,
                test_case.get('expected_patterns', [])
            )
            
            # Check efficiency
            efficiency_score = self._check_efficiency(
                response_text,
                response_time_ms,
                test_case.get('time_limit_ms')
            )
            
            # Determine if passed
            passed = (
                quality_scores.get('correctness', 0) >= 6.0 and
                security_score >= 5.0 and
                efficiency_score >= 5.0
            )
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Update Prometheus metrics
            if self.prometheus_enabled and self.prometheus_metrics:
                self.prometheus_metrics['benchmark_tests_total'].labels(
                    category=category, status='passed' if passed else 'failed'
                ).inc()
                self.prometheus_metrics['benchmark_duration_seconds'].labels(
                    category=category
                ).observe(execution_time_ms / 1000)
            
            return BenchmarkResult(
                test_id=test_id,
                test_name=test_name,
                category=category,
                passed=passed,
                execution_time_ms=execution_time_ms,
                response_time_ms=response_time_ms,
                quality_score=statistics.mean(quality_scores.values()) if quality_scores else 0,
                security_score=security_score,
                efficiency_score=efficiency_score,
                code_executed=execution_result is not None,
                execution_success=execution_result.success if execution_result else False,
                metadata={
                    'quality_scores': quality_scores,
                    'expected_patterns': test_case.get('expected_patterns', []),
                    'difficulty': test_case.get('difficulty', 'medium')
                }
            )
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            return BenchmarkResult(
                test_id=test_id,
                test_name=test_name,
                category=category,
                passed=False,
                execution_time_ms=execution_time_ms,
                response_time_ms=0,
                error_message=str(e)
            )
    
    async def run_all_tests(self, category: Optional[str] = None) -> BenchmarkReport:
        """Run all benchmark tests."""
        self.start_time = datetime.now()
        self.results = []
        
        # Filter by category if specified
        tests_to_run = self.test_cases
        if category:
            tests_to_run = [t for t in self.test_cases if t.get('category') == category]
        
        print(f"Running {len(tests_to_run)} benchmark tests...")
        
        for i, test_case in enumerate(tests_to_run):
            print(f"  [{i+1}/{len(tests_to_run)}] Running: {test_case.get('name', 'Unknown')}")
            result = await self.run_single_test(test_case)
            self.results.append(result)
            
            status = "✅ PASSED" if result.passed else "❌ FAILED"
            print(f"    {status} ({result.execution_time_ms:.2f}ms)")
        
        return self.generate_report()
    
    def generate_report(self) -> BenchmarkReport:
        """Generate comprehensive benchmark report."""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        failed_tests = total_tests - passed_tests
        
        # Calculate averages
        execution_times = [r.execution_time_ms for r in self.results]
        response_times = [r.response_time_ms for r in self.results]
        
        # Calculate category scores
        category_results: Dict[str, List[BenchmarkResult]] = {}
        for result in self.results:
            cat = result.category
            if cat not in category_results:
                category_results[cat] = []
            category_results[cat].append(result)
        
        category_scores = {}
        for cat, results in category_results.items():
            scores = [r.quality_score for r in results if r.quality_score > 0]
            category_scores[cat] = statistics.mean(scores) if scores else 0.0
        
        # Calculate overall score
        overall_score = passed_tests / total_tests * 100 if total_tests > 0 else 0
        
        return BenchmarkReport(
            timestamp=self.start_time.isoformat() if self.start_time else datetime.now().isoformat(),
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            avg_execution_time_ms=statistics.mean(execution_times) if execution_times else 0,
            avg_response_time_ms=statistics.mean(response_times) if response_times else 0,
            total_tokens_used=sum(r.tokens_used for r in self.results),
            category_scores=category_scores,
            results=self.results,
            overall_score=overall_score
        )
    
    def save_report(self, report: BenchmarkReport, output_path: str = "benchmark_report.json"):
        """Save benchmark report to JSON file."""
        report_dict = {
            'timestamp': report.timestamp,
            'summary': {
                'total_tests': report.total_tests,
                'passed_tests': report.passed_tests,
                'failed_tests': report.failed_tests,
                'overall_score': report.overall_score,
                'avg_execution_time_ms': report.avg_execution_time_ms,
                'avg_response_time_ms': report.avg_response_time_ms,
                'total_tokens_used': report.total_tokens_used
            },
            'category_scores': report.category_scores,
            'results': [asdict(r) for r in report.results]
        }
        
        with open(output_path, 'w') as f:
            json.dump(report_dict, f, indent=2)
        
        print(f"\n📊 Report saved to: {output_path}")
    
    def print_summary(self, report: BenchmarkReport):
        """Print benchmark summary to console."""
        print("\n" + "=" * 60)
        print("📋 BENCHMARK REPORT SUMMARY")
        print("=" * 60)
        print(f"Timestamp: {report.timestamp}")
        print(f"Total Tests: {report.total_tests}")
        print(f"Passed: {report.passed_tests} ✅")
        print(f"Failed: {report.failed_tests} ❌")
        print(f"Overall Score: {report.overall_score:.1f}%")
        print(f"Avg Execution Time: {report.avg_execution_time_ms:.2f}ms")
        print(f"Avg Response Time: {report.avg_response_time_ms:.2f}ms")
        print("\nCategory Scores:")
        for cat, score in report.category_scores.items():
            print(f"  • {cat}: {score:.1f}/10")
        print("=" * 60)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Vaal AI Empire Benchmark Executor",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--run-all",
        action="store_true",
        help="Run all benchmark tests"
    )
    
    parser.add_argument(
        "--category",
        type=str,
        choices=[c.value for c in BenchmarkCategory],
        help="Run tests for specific category only"
    )
    
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate and save benchmark report"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default="benchmark_report.json",
        help="Output path for report (default: benchmark_report.json)"
    )
    
    parser.add_argument(
        "--benchmark-data",
        type=str,
        default="benchmark_data/test_cases.json",
        help="Path to benchmark test cases JSON"
    )
    
    parser.add_argument(
        "--no-quality-eval",
        action="store_true",
        help="Disable GLM-5 quality evaluation"
    )
    
    parser.add_argument(
        "--prometheus",
        action="store_true",
        help="Enable Prometheus metrics"
    )
    
    return parser.parse_args()


async def main():
    """Main entry point."""
    args = parse_args()
    
    executor = BenchmarkExecutor(
        benchmark_data_path=args.benchmark_data,
        enable_quality_evaluation=not args.no_quality_eval,
        prometheus_enabled=args.prometheus
    )
    
    if args.run_all or args.category:
        report = await executor.run_all_tests(category=args.category)
        executor.print_summary(report)
        
        if args.report:
            executor.save_report(report, args.output)
    else:
        print("Use --run-all or --category <category> to run benchmarks")
        print(f"Available categories: {[c.value for c in BenchmarkCategory]}")


if __name__ == "__main__":
    asyncio.run(main())
