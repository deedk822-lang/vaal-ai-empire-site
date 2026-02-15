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

Environment Variables:
    DASHSCOPE_API_KEY: API key for DashScope/Aliyun
    GLM5_API_KEY: API key for GLM-5 evaluation
    BENCHMARK_OUTPUT_DIR: Directory for benchmark results
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import statistics
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# Import base executor - handle both direct execution and import
# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Track whether we have the base class available
_HAS_BASE_CLASS = False
CodingAgentExecutor = None
AgentResult = None

# Try multiple import paths for the base executor
try:
    # Try direct import first (when running from agents directory)
    from coding_agent_executor import CodingAgentExecutor, AgentResult
    _HAS_BASE_CLASS = True
except ImportError:
    try:
        # Try relative import
        from .coding_agent_executor import CodingAgentExecutor, AgentResult
        _HAS_BASE_CLASS = True
    except ImportError:
        # Define minimal base classes if import fails
        @dataclass
        class AgentResult:
            response: str
            executed: bool = False
        
        class CodingAgentExecutor:
            """Minimal fallback implementation for standalone benchmark execution."""
            
            def __init__(self, api_key: Optional[str] = None) -> None:
                self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
            
            @property
            def has_api_key(self) -> bool:
                return bool(self.api_key)
            
            def respond(self, message: str, execute: bool = False) -> AgentResult:
                """Generate a mock response for benchmarking purposes."""
                return AgentResult(
                    response=f"[Benchmark Mode] Received request: {message[:50]}...",
                    executed=False
                )


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
    quality_score: float = 0.0
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


class BenchmarkExecutor(CodingAgentExecutor):
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
    
    Example:
        executor = BenchmarkExecutor(
            api_key="your-api-key",
            glm5_api_key="your-glm5-key"
        )
        report = asyncio.run(executor.run_all_tests())
        executor.save_report(report, "results.json")
    """
    
    # GLM-5 Quality evaluation prompt template
    QUALITY_EVALUATION_PROMPT = """You are an expert code reviewer. Evaluate the following AI-generated code response on a scale of 0-10 for:

1. **Correctness** (0-10): Does the code solve the problem correctly?
2. **Security** (0-10): Is the code secure? Any vulnerabilities?
3. **Efficiency** (0-10): Is the code efficient? Any performance issues?
4. **Readability** (0-10): Is the code well-structured and documented?
5. **Best Practices** (0-10): Does it follow coding standards?

Original Prompt:
{prompt}

AI Response:
{response}

Respond ONLY with a JSON object in this exact format:
{{"correctness": N, "security": N, "efficiency": N, "readability": N, "best_practices": N}}"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        benchmark_data_path: str = "benchmark_data/test_cases.json",
        enable_code_execution: bool = True,
        execution_timeout: int = 60,
        enable_quality_evaluation: bool = True,
        glm5_api_key: Optional[str] = None,
        prometheus_enabled: bool = False
    ):
        """
        Initialize the BenchmarkExecutor.
        
        Args:
            api_key: API key for the main AI service
            benchmark_data_path: Path to test cases JSON file
            enable_code_execution: Whether to execute generated code
            execution_timeout: Timeout for code execution in seconds
            enable_quality_evaluation: Whether to use GLM-5 for evaluation
            glm5_api_key: API key for GLM-5 evaluation service
            prometheus_enabled: Whether to enable Prometheus metrics
        """
        # Initialize parent class
        super().__init__(api_key=api_key)
        
        self.benchmark_data_path = Path(benchmark_data_path)
        self.enable_code_execution = enable_code_execution
        self.execution_timeout = execution_timeout
        self.enable_quality_evaluation = enable_quality_evaluation
        self.glm5_api_key = glm5_api_key or os.getenv("GLM5_API_KEY")
        self.prometheus_enabled = prometheus_enabled
        
        # Benchmark state
        self.test_cases: List[Dict[str, Any]] = []
        self.results: List[BenchmarkResult] = []
        self.start_time: Optional[datetime] = None
        
        # Setup Prometheus metrics
        self._setup_prometheus_metrics()
        
        # Load test cases
        self._load_test_cases()
    
    def _setup_prometheus_metrics(self) -> None:
        """Setup Prometheus metrics for benchmark monitoring."""
        self.prometheus_metrics: Dict[str, Any] = {}
        
        if not self.prometheus_enabled:
            return
        
        try:
            from prometheus_client import Counter, Histogram, Gauge, start_http_server
            
            # Benchmark-specific metrics
            self.prometheus_metrics = {
                'benchmark_tests_total': Counter(
                    'vaal_benchmark_tests_total',
                    'Total number of benchmark tests executed',
                    ['category', 'status']
                ),
                'benchmark_duration_seconds': Histogram(
                    'vaal_benchmark_duration_seconds',
                    'Duration of benchmark tests in seconds',
                    ['category'],
                    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0]
                ),
                'benchmark_quality_score': Gauge(
                    'vaal_benchmark_quality_score',
                    'Quality score of benchmark results',
                    ['category', 'test_id']
                ),
                'benchmark_security_score': Gauge(
                    'vaal_benchmark_security_score',
                    'Security score of benchmark results',
                    ['test_id']
                ),
                'benchmark_tokens_used': Counter(
                    'vaal_benchmark_tokens_used_total',
                    'Total tokens used in benchmark tests',
                    ['category']
                ),
            }
            
            # Start Prometheus HTTP server
            try:
                start_http_server(9090)
                print("📊 Prometheus metrics server started on port 9090")
            except OSError:
                print("⚠️  Prometheus server port 9090 already in use")
                
        except ImportError:
            print("⚠️  prometheus_client not installed, disabling Prometheus metrics")
            self.prometheus_enabled = False
    
    def _load_test_cases(self) -> None:
        """Load test cases from JSON file."""
        if self.benchmark_data_path.exists():
            try:
                with open(self.benchmark_data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.test_cases = data.get('test_cases', [])
                    print(f"✅ Loaded {len(self.test_cases)} test cases from {self.benchmark_data_path}")
            except (json.JSONDecodeError, IOError) as e:
                print(f"⚠️  Error loading test cases: {e}")
                self.test_cases = self._get_default_test_cases()
        else:
            print(f"⚠️  Test cases file not found: {self.benchmark_data_path}")
            self.test_cases = self._get_default_test_cases()
    
    def _get_default_test_cases(self) -> List[Dict[str, Any]]:
        """Get default test cases if no file is found."""
        return [
            {
                "id": "SEC001",
                "name": "SQL Injection Prevention",
                "category": "security",
                "prompt": "Write a Python function to safely query a user by ID from a database",
                "expected_patterns": ["parameterized", "prepared statement", "cursor.execute"],
                "security_check": True,
                "difficulty": "medium"
            },
            {
                "id": "EFF001",
                "name": "Fibonacci with Memoization",
                "category": "efficiency",
                "prompt": "Write an efficient Fibonacci function using memoization",
                "expected_patterns": ["memo", "cache", "lru_cache", "dynamic programming"],
                "time_limit_ms": 1000,
                "difficulty": "medium"
            },
            {
                "id": "EDGE001",
                "name": "Empty Input Handling",
                "category": "edge_cases",
                "prompt": "Write a function to find the maximum value in a list that handles empty lists",
                "expected_patterns": ["if not", "len(", "return None"],
                "difficulty": "easy"
            }
        ]
    
    def _evaluate_with_glm5(
        self, 
        prompt: str, 
        response: str,
        max_retries: int = 3
    ) -> Dict[str, float]:
        """
        Evaluate response quality using GLM-5 API.
        
        Args:
            prompt: Original test prompt
            response: AI-generated response to evaluate
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dictionary with quality scores for each dimension
        """
        if not self.glm5_api_key:
            return {"correctness": 5.0, "security": 5.0, "efficiency": 5.0, 
                   "readability": 5.0, "best_practices": 5.0}
        
        try:
            import requests
            
            eval_prompt = self.QUALITY_EVALUATION_PROMPT.format(
                prompt=prompt,
                response=response
            )
            
            for attempt in range(max_retries):
                try:
                    resp = requests.post(
                        "https://open.bigmodel.cn/api/paas/v3/model-api/chatglm_pro/invoke",
                        headers={
                            "Authorization": f"Bearer {self.glm5_api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "prompt": eval_prompt,
                            "max_tokens": 200,
                            "temperature": 0.1
                        },
                        timeout=30
                    )
                    
                    if resp.status_code == 200:
                        result = resp.json()
                        content = result.get('data', {}).get('content', '{}')
                        
                        # Extract JSON from response
                        json_match = re.search(r'\{[^}]+\}', content)
                        if json_match:
                            scores = json.loads(json_match.group())
                            return {
                                "correctness": float(scores.get('correctness', 5.0)),
                                "security": float(scores.get('security', 5.0)),
                                "efficiency": float(scores.get('efficiency', 5.0)),
                                "readability": float(scores.get('readability', 5.0)),
                                "best_practices": float(scores.get('best_practices', 5.0))
                            }
                    
                    time.sleep(1 * (attempt + 1))  # Exponential backoff
                    
                except requests.RequestException as e:
                    if attempt == max_retries - 1:
                        print(f"GLM-5 API error after {max_retries} attempts: {e}")
                    time.sleep(1 * (attempt + 1))
                    
        except ImportError:
            print("⚠️  requests library not available for GLM-5 evaluation")
        except Exception as e:
            print(f"GLM-5 evaluation error: {e}")
        
        return {"correctness": 5.0, "security": 5.0, "efficiency": 5.0, 
               "readability": 5.0, "best_practices": 5.0}
    
    def _check_security_patterns(
        self, 
        response: str, 
        expected_patterns: List[str],
        forbidden_patterns: Optional[List[str]] = None
    ) -> Tuple[float, List[str]]:
        """
        Check for security patterns in the response.
        
        Args:
            response: AI-generated code response
            expected_patterns: Patterns that should be present
            forbidden_patterns: Patterns that should NOT be present
            
        Returns:
            Tuple of (score, list of issues found)
        """
        response_lower = response.lower()
        issues: List[str] = []
        
        # Check expected patterns
        matches = 0
        for pattern in expected_patterns:
            if pattern.lower() in response_lower:
                matches += 1
            else:
                issues.append(f"Missing expected pattern: {pattern}")
        
        base_score = (matches / len(expected_patterns)) * 10.0 if expected_patterns else 10.0
        
        # Check forbidden patterns
        if forbidden_patterns:
            for pattern in forbidden_patterns:
                if pattern.lower() in response_lower:
                    issues.append(f"Found forbidden pattern: {pattern}")
                    base_score -= 2.0
        
        return max(0.0, base_score), issues
    
    def _check_efficiency(
        self, 
        response: str, 
        time_taken_ms: float, 
        time_limit_ms: Optional[int]
    ) -> float:
        """
        Check efficiency of the response.
        
        Args:
            response: AI-generated code response
            time_taken_ms: Actual execution time
            time_limit_ms: Expected time limit
            
        Returns:
            Efficiency score (0-10)
        """
        score = 10.0
        
        # Check time limit
        if time_limit_ms and time_taken_ms > time_limit_ms:
            score -= 5.0 * min(1.0, (time_taken_ms - time_limit_ms) / time_limit_ms)
        
        # Check for efficiency-related terms
        efficiency_terms = ['efficient', 'optimized', 'o(n', 'o(log', 'cache', 
                          'memoiz', 'generator', 'yield', 'vectorized']
        response_lower = response.lower()
        
        if any(term in response_lower for term in efficiency_terms):
            score = min(10.0, score + 0.5)
        
        # Check for inefficient patterns
        inefficient_patterns = ['for.*in.*:\n.*for.*in.*:', 'while True:', 'recursion']
        for pattern in inefficient_patterns:
            if re.search(pattern, response_lower):
                score -= 1.0
        
        return max(0.0, score)
    
    async def run_single_test(self, test_case: Dict[str, Any]) -> BenchmarkResult:
        """
        Run a single benchmark test.
        
        Args:
            test_case: Test case dictionary with test parameters
            
        Returns:
            BenchmarkResult with test results
        """
        start_time = time.time()
        
        test_id = test_case.get('id', 'unknown')
        test_name = test_case.get('name', 'Unknown Test')
        category = test_case.get('category', 'general')
        prompt = test_case.get('prompt', '')
        
        try:
            # Get response from agent
            response_start = time.time()
            
            # Use parent class's respond method
            agent_result = self.respond(message=prompt, execute=self.enable_code_execution)
            response_text = agent_result.response
            
            response_time_ms = (time.time() - response_start) * 1000
            
            # Evaluate quality with GLM-5
            quality_scores = {"correctness": 5.0, "security": 5.0, "efficiency": 5.0, 
                            "readability": 5.0, "best_practices": 5.0}
            if self.enable_quality_evaluation:
                quality_scores = self._evaluate_with_glm5(prompt, response_text)
            
            # Check security patterns
            security_score, security_issues = self._check_security_patterns(
                response_text,
                test_case.get('expected_patterns', []),
                test_case.get('forbidden_patterns', [])
            )
            
            # Check efficiency
            efficiency_score = self._check_efficiency(
                response_text,
                response_time_ms,
                test_case.get('time_limit_ms')
            )
            
            # Calculate overall quality score
            quality_score = statistics.mean(quality_scores.values()) if quality_scores else 0.0
            
            # Determine if passed
            passed = (
                quality_scores.get('correctness', 0) >= 6.0 and
                security_score >= 5.0 and
                efficiency_score >= 5.0
            )
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Update Prometheus metrics
            if self.prometheus_enabled and self.prometheus_metrics:
                try:
                    self.prometheus_metrics['benchmark_tests_total'].labels(
                        category=category, status='passed' if passed else 'failed'
                    ).inc()
                    self.prometheus_metrics['benchmark_duration_seconds'].labels(
                        category=category
                    ).observe(execution_time_ms / 1000)
                    self.prometheus_metrics['benchmark_quality_score'].labels(
                        category=category, test_id=test_id
                    ).set(quality_score)
                    self.prometheus_metrics['benchmark_security_score'].labels(
                        test_id=test_id
                    ).set(security_score)
                except Exception as e:
                    print(f"Error updating Prometheus metrics: {e}")
            
            return BenchmarkResult(
                test_id=test_id,
                test_name=test_name,
                category=category,
                passed=passed,
                execution_time_ms=execution_time_ms,
                response_time_ms=response_time_ms,
                quality_score=quality_score,
                security_score=security_score,
                efficiency_score=efficiency_score,
                code_executed=self.enable_code_execution,
                execution_success=agent_result.executed,
                metadata={
                    'quality_scores': quality_scores,
                    'expected_patterns': test_case.get('expected_patterns', []),
                    'security_issues': security_issues,
                    'difficulty': test_case.get('difficulty', 'medium'),
                    'tags': test_case.get('tags', [])
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
        """
        Run all benchmark tests.
        
        Args:
            category: Optional category filter (runs all if None)
            
        Returns:
            BenchmarkReport with comprehensive results
        """
        self.start_time = datetime.now()
        self.results = []
        
        # Filter by category if specified
        tests_to_run = self.test_cases
        if category:
            tests_to_run = [t for t in self.test_cases if t.get('category') == category]
            print(f"\n🔍 Running {len(tests_to_run)} tests from category: {category}")
        else:
            print(f"\n🔍 Running all {len(tests_to_run)} benchmark tests...")
        
        for i, test_case in enumerate(tests_to_run, 1):
            print(f"  [{i}/{len(tests_to_run)}] {test_case.get('id', '???')}: {test_case.get('name', 'Unknown')}", end=" ")
            
            try:
                result = await self.run_single_test(test_case)
                self.results.append(result)
                
                status = "✅ PASS" if result.passed else "❌ FAIL"
                print(f"{status} ({result.execution_time_ms:.0f}ms)")
                
                if result.error_message:
                    print(f"      Error: {result.error_message}")
                    
            except Exception as e:
                print(f"💥 ERROR: {e}")
                self.results.append(BenchmarkResult(
                    test_id=test_case.get('id', 'unknown'),
                    test_name=test_case.get('name', 'Unknown'),
                    category=test_case.get('category', 'general'),
                    passed=False,
                    execution_time_ms=0,
                    response_time_ms=0,
                    error_message=str(e)
                ))
        
        return self.generate_report()
    
    def generate_report(self) -> BenchmarkReport:
        """
        Generate comprehensive benchmark report.
        
        Returns:
            BenchmarkReport with aggregated statistics
        """
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
        overall_score = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
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
    
    def save_report(self, report: BenchmarkReport, output_path: Optional[str] = None) -> str:
        """
        Save benchmark report to JSON file.
        
        Args:
            report: BenchmarkReport to save
            output_path: Output file path (defaults to BENCHMARK_OUTPUT_DIR/benchmark_report.json)
            
        Returns:
            Path to saved report file
        """
        if output_path is None:
            output_dir = Path(os.getenv('BENCHMARK_OUTPUT_DIR', '.'))
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / 'benchmark_report.json'
        else:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
        
        report_dict = {
            'timestamp': report.timestamp,
            'summary': {
                'total_tests': report.total_tests,
                'passed_tests': report.passed_tests,
                'failed_tests': report.failed_tests,
                'overall_score': round(report.overall_score, 2),
                'avg_execution_time_ms': round(report.avg_execution_time_ms, 2),
                'avg_response_time_ms': round(report.avg_response_time_ms, 2),
                'total_tokens_used': report.total_tokens_used
            },
            'category_scores': {k: round(v, 2) for k, v in report.category_scores.items()},
            'results': [asdict(r) for r in report.results],
            'metadata': {
                'version': '1.0.0',
                'tool': 'Vaal AI Empire Benchmark Suite',
                'glm5_enabled': self.enable_quality_evaluation and bool(self.glm5_api_key),
                'prometheus_enabled': self.prometheus_enabled
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, default=str)
        
        print(f"\n📊 Report saved to: {output_path}")
        return str(output_path)
    
    def print_summary(self, report: BenchmarkReport) -> None:
        """
        Print benchmark summary to console.
        
        Args:
            report: BenchmarkReport to display
        """
        print("\n" + "=" * 70)
        print("📋 BENCHMARK REPORT SUMMARY")
        print("=" * 70)
        print(f"Timestamp: {report.timestamp}")
        print(f"Total Tests: {report.total_tests}")
        print(f"Passed: {report.passed_tests} ✅")
        print(f"Failed: {report.failed_tests} ❌")
        print(f"Overall Score: {report.overall_score:.1f}%")
        print(f"Avg Execution Time: {report.avg_execution_time_ms:.2f}ms")
        print(f"Avg Response Time: {report.avg_response_time_ms:.2f}ms")
        print("\nCategory Scores:")
        for cat, score in sorted(report.category_scores.items()):
            bar = "█" * int(score)
            print(f"  • {cat:20s}: {score:.1f}/10 {bar}")
        print("=" * 70)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Vaal AI Empire Benchmark Executor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all tests
  python benchmark_executor.py --run-all
  
  # Run only security tests
  python benchmark_executor.py --category security
  
  # Run with report and custom output
  python benchmark_executor.py --run-all --report --output results.json
  
  # Enable Prometheus metrics
  python benchmark_executor.py --run-all --prometheus
        """
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
        default=None,
        help="Output path for report (default: benchmark_results/benchmark_report.json)"
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
        help="Enable Prometheus metrics server"
    )
    
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="API key for AI service (overrides environment variable)"
    )
    
    parser.add_argument(
        "--glm5-api-key",
        type=str,
        default=None,
        help="API key for GLM-5 evaluation (overrides environment variable)"
    )
    
    return parser.parse_args()


async def main() -> int:
    """Main entry point."""
    args = parse_args()
    
    if not args.run_all and not args.category:
        print("Use --run-all or --category <category> to run benchmarks")
        print(f"Available categories: {[c.value for c in BenchmarkCategory]}")
        return 1
    
    # Initialize executor
    executor = BenchmarkExecutor(
        api_key=args.api_key,
        benchmark_data_path=args.benchmark_data,
        enable_quality_evaluation=not args.no_quality_eval,
        prometheus_enabled=args.prometheus,
        glm5_api_key=args.glm5_api_key
    )
    
    # Run benchmarks
    report = await executor.run_all_tests(category=args.category)
    
    # Print summary
    executor.print_summary(report)
    
    # Save report if requested
    if args.report:
        executor.save_report(report, args.output)
    
    # Return exit code based on results
    return 0 if report.failed_tests == 0 else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Benchmark interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
        sys.exit(1)
