#!/usr/bin/env python3
"""Vaal AI Empire - Ollama-Enhanced Benchmark Executor.

A unified benchmark suite using Ollama as the interface for AI model evaluation.
No API keys required in code - Ollama handles authentication and model management.

Features:
- Unified interface for Kimi K2.5, GLM-5, Qwen models via Ollama
- Head-to-head model comparison
- Async concurrent benchmarking
- No API key management in code
- Works with local models (offline) and cloud models via Ollama

Usage:
    # Run head-to-head comparison
    python agents/ollama_benchmark_enhanced.py

    # Run with specific models
    python agents/ollama_benchmark_enhanced.py --models kimi-k2.5 glm5

    # Run specific category
    python agents/ollama_benchmark_enhanced.py --category security

Requirements:
    - Ollama installed: curl -fsSL https://ollama.com/install.sh | sh
    - Models pulled: ollama pull kimi-k2.5:cloud glm5
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import statistics
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class BenchmarkCategory(Enum):
    """Categories of benchmark tests."""

    SECURITY = "security"
    EFFICIENCY = "efficiency"
    EDGE_CASES = "edge_cases"
    CODE_GENERATION = "code_generation"
    REFACTORING = "refactoring"
    DEBUGGING = "debugging"
    REASONING = "reasoning"
    CREATIVE = "creative"


@dataclass
class BenchmarkResult:
    """Result of a single benchmark test."""

    test_id: str
    test_name: str
    category: str
    model: str
    passed: bool
    latency_ms: float
    response: str
    tokens_per_sec: float = 0.0
    error_message: Optional[str] = None
    quality_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HeadToHeadResult:
    """Result of head-to-head model comparison."""

    test_name: str
    category: str
    models: Dict[str, Dict[str, Any]]
    winner: Optional[str] = None
    margin_ms: float = 0.0


@dataclass
class BenchmarkReport:
    """Comprehensive benchmark report."""

    timestamp: str
    total_tests: int
    model_wins: Dict[str, int]
    latency_comparison: Dict[str, Dict[str, float]]
    results: List[HeadToHeadResult]
    available_models: Dict[str, bool]


class OllamaEnhancedBenchmark:
    """Unified Ollama-based benchmark suite.

    Provides a single interface for benchmarking multiple AI models
    through Ollama, eliminating the need for multiple API keys and SDKs.

    Supported Models:
    - kimi-k2.5: Kimi K2.5 via Ollama Cloud
    - glm-5: GLM-5 via Ollama
    - qwen2.5: Qwen 2.5 Coder (local or cloud)
    - llama3.2: Meta Llama 3.2 (local)
    """

    # Model configurations
    DEFAULT_MODELS = {
        "kimi-k2.5": "kimi-k2.5:cloud",
        "glm-5": "glm5",
        "qwen2.5": "qwen2.5-coder:14b",
        "llama3.2": "llama3.2:latest",
        "deepseek-coder": "deepseek-coder:6.7b",
    }

    def __init__(
        self,
        models: Optional[Dict[str, str]] = None,
        benchmark_data_path: str = "benchmark_data/test_cases.json",
        runs_per_test: int = 3,
        timeout: int = 120,
    ):
        """Initialize the Ollama benchmark executor.

        Args:
            models: Dictionary of model names to Ollama model tags
            benchmark_data_path: Path to test cases JSON file
            runs_per_test: Number of runs per test for statistical significance
            timeout: Timeout in seconds for each model response
        """
        self.models = models or self.DEFAULT_MODELS
        self.benchmark_data_path = Path(benchmark_data_path)
        self.runs_per_test = runs_per_test
        self.timeout = timeout

        self.test_cases: List[Dict] = []
        self.results: List[HeadToHeadResult] = []
        self.available_models: Dict[str, bool] = {}

        self._load_test_cases()

    def _load_test_cases(self):
        """Load test cases from JSON file."""
        if self.benchmark_data_path.exists():
            with open(self.benchmark_data_path, "r") as f:
                data = json.load(f)
                self.test_cases = data.get("test_cases", [])
        else:
            self.test_cases = self._get_default_test_cases()

    def _get_default_test_cases(self) -> List[Dict]:
        """Get default comprehensive test cases."""
        return [
            # Coding tasks
            {
                "id": "CODE001",
                "name": "Fibonacci Function",
                "category": "code_generation",
                "prompt": "Write a Python function to calculate fibonacci numbers efficiently using memoization",
                "expected_patterns": ["def", "fibonacci", "memo", "cache"],
                "difficulty": "easy",
            },
            {
                "id": "CODE002",
                "name": "REST API Design",
                "category": "code_generation",
                "prompt": "Design a REST API endpoint for a payment processing system with proper error handling",
                "expected_patterns": ["POST", "GET", "error", "status", "json"],
                "difficulty": "medium",
            },
            {
                "id": "CODE003",
                "name": "Database Query",
                "category": "code_generation",
                "prompt": "Write a parameterized SQL query to safely search for users by email domain",
                "expected_patterns": ["SELECT", "WHERE", "LIKE", "parameterized", "%"],
                "difficulty": "medium",
            },
            # Debugging tasks
            {
                "id": "DBG001",
                "name": "Regex Fix",
                "category": "debugging",
                "prompt": "Fix this regex pattern to accept hyphens in domain names: ^[a-zA-Z0-9]+@[a-z]+\\.[a-z]{2,3}$",
                "expected_patterns": ["regex", "-", "domain", "[a-z0-9-]"],
                "difficulty": "medium",
            },
            {
                "id": "DBG002",
                "name": "SQL Injection Vulnerability",
                "category": "security",
                "prompt": "Identify and fix the SQL injection vulnerability in this code: app.post('/login', (req, res) => { db.query('SELECT * FROM users WHERE username = \"' + req.body.username + '\"') })",
                "expected_patterns": [
                    "parameterized",
                    "prepared",
                    "statement",
                    "?",
                    "$1",
                ],
                "difficulty": "medium",
            },
            {
                "id": "DBG003",
                "name": "Race Condition",
                "category": "debugging",
                "prompt": "Fix the race condition in this counter: let count = 0; async function increment() { let temp = count; await delay(); count = temp + 1; }",
                "expected_patterns": ["lock", "mutex", "atomic", "synchronized"],
                "difficulty": "hard",
            },
            # Security tasks
            {
                "id": "SEC001",
                "name": "XSS Prevention",
                "category": "security",
                "prompt": "Write a Python function to sanitize user input for safe HTML display, preventing XSS attacks",
                "expected_patterns": [
                    "html.escape",
                    "escape",
                    "sanitize",
                    "&lt;",
                    "&gt;",
                ],
                "difficulty": "medium",
            },
            {
                "id": "SEC002",
                "name": "JWT Implementation",
                "category": "security",
                "prompt": "Implement a secure JWT token generation function with proper expiration and secret key handling",
                "expected_patterns": ["jwt", "secret", "expires", "HS256", "encode"],
                "difficulty": "medium",
            },
            {
                "id": "SEC003",
                "name": "Password Hashing",
                "category": "security",
                "prompt": "Write a secure password hashing function using bcrypt with proper salt generation",
                "expected_patterns": ["bcrypt", "hashpw", "gensalt", "salt"],
                "difficulty": "easy",
            },
            # Efficiency tasks
            {
                "id": "EFF001",
                "name": "SQL Optimization",
                "category": "efficiency",
                "prompt": "Optimize this SQL query: SELECT * FROM orders WHERE customer_id IN (SELECT id FROM customers WHERE city = 'NYC')",
                "expected_patterns": ["JOIN", "INDEX", "EXISTS", "LIMIT"],
                "difficulty": "medium",
            },
            {
                "id": "EFF002",
                "name": "Large File Processing",
                "category": "efficiency",
                "prompt": "Write Python code to process a 10GB CSV file efficiently without loading it all into memory",
                "expected_patterns": [
                    "chunk",
                    "iterator",
                    "with open",
                    "csv.reader",
                    "yield",
                ],
                "difficulty": "medium",
            },
            {
                "id": "EFF003",
                "name": "Caching Strategy",
                "category": "efficiency",
                "prompt": "Implement an LRU cache decorator for expensive function calls with configurable max size",
                "expected_patterns": ["lru_cache", "OrderedDict", "evict", "maxsize"],
                "difficulty": "medium",
            },
            # Reasoning tasks
            {
                "id": "RSN001",
                "name": "API Architecture",
                "category": "reasoning",
                "prompt": "Explain the trade-offs between REST and GraphQL for a microservices architecture handling real-time data",
                "expected_patterns": [
                    "REST",
                    "GraphQL",
                    "websocket",
                    "subscription",
                    "caching",
                ],
                "difficulty": "hard",
            },
            {
                "id": "RSN002",
                "name": "Database Selection",
                "category": "reasoning",
                "prompt": "Compare PostgreSQL vs MongoDB for an e-commerce product catalog with variable product attributes",
                "expected_patterns": [
                    "PostgreSQL",
                    "MongoDB",
                    "JSONB",
                    "schema",
                    "flexible",
                ],
                "difficulty": "medium",
            },
            # Creative tasks
            {
                "id": "CRT001",
                "name": "Technical Documentation",
                "category": "creative",
                "prompt": "Write clear documentation for a rate-limiting middleware function for an Express.js API",
                "expected_patterns": [
                    "rate",
                    "limit",
                    "requests",
                    "window",
                    "middleware",
                ],
                "difficulty": "medium",
            },
        ]

    def verify_models(self) -> Dict[str, bool]:
        """Check which Ollama models are available.

        Returns:
            Dictionary mapping model names to availability status
        """
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            for name, ollama_name in self.models.items():
                # Check if model name appears in ollama list output
                self.available_models[name] = ollama_name.split(":")[0] in result.stdout

        except FileNotFoundError:
            print(
                "❌ Ollama is not installed. Install with: curl -fsSL https://ollama.com/install.sh | sh"
            )
            self.available_models = {name: False for name in self.models}
        except subprocess.TimeoutExpired:
            print("⚠️ Ollama command timed out")
            self.available_models = {name: False for name in self.models}
        except Exception as e:
            print(f"⚠️ Error checking Ollama models: {e}")
            self.available_models = {name: False for name in self.models}

        return self.available_models

    def _parse_ollama_stats(self, stderr: str) -> Dict[str, float]:
        """Parse Ollama performance statistics from stderr.

        Args:
            stderr: Ollama's stderr output

        Returns:
            Dictionary with parsed statistics
        """
        stats = {"tokens_per_sec": 0.0, "eval_duration_ms": 0.0, "total_tokens": 0}

        # Ollama outputs stats like: "eval rate: 45.23 tokens/s"
        patterns = {
            "tokens_per_sec": r"eval rate:\s*([\d.]+)\s*tokens/s",
            "eval_duration_ms": r"eval duration:\s*([\d.]+)\s*ms",
            "total_tokens": r"eval count:\s*(\d+)\s*tokens",
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, stderr, re.IGNORECASE)
            if match:
                stats[key] = float(match.group(1))

        return stats

    async def _run_single_benchmark(
        self,
        model_key: str,
        prompt: str,
    ) -> Dict[str, Any]:
        """Run a single benchmark with one model.

        Args:
            model_key: Key name of the model in self.models
            prompt: The prompt to send to the model

        Returns:
            Dictionary with benchmark results
        """
        ollama_name = self.models.get(model_key)
        if not ollama_name:
            return {"error": f"Model '{model_key}' not configured"}

        latencies = []
        responses = []
        tokens_per_sec_list = []

        for run in range(self.runs_per_test):
            try:
                start = time.perf_counter()

                # Create async subprocess for Ollama
                process = await asyncio.create_subprocess_exec(
                    "ollama",
                    "run",
                    ollama_name,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(input=prompt.encode()),
                        timeout=self.timeout,
                    )
                except asyncio.TimeoutError:
                    process.kill()
                    return {"error": f"Timeout after {self.timeout}s"}

                latency_ms = (time.perf_counter() - start) * 1000
                latencies.append(latency_ms)

                response = stdout.decode().strip()
                responses.append(response)

                # Parse stats from stderr
                stats = self._parse_ollama_stats(stderr.decode())
                if stats["tokens_per_sec"] > 0:
                    tokens_per_sec_list.append(stats["tokens_per_sec"])

            except FileNotFoundError:
                return {"error": "Ollama not installed"}
            except Exception as e:
                return {"error": str(e)}

        # Calculate statistics
        result = {
            "model": model_key,
            "ollama_name": ollama_name,
            "prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt,
            "runs": self.runs_per_test,
            "latency": {
                "mean_ms": round(statistics.mean(latencies), 2),
                "median_ms": round(statistics.median(latencies), 2),
                "stdev_ms": (
                    round(statistics.stdev(latencies), 2) if len(latencies) > 1 else 0
                ),
                "min_ms": round(min(latencies), 2),
                "max_ms": round(max(latencies), 2),
                "p95_ms": (
                    round(sorted(latencies)[int(len(latencies) * 0.95)], 2)
                    if len(latencies) > 1
                    else latencies[0]
                ),
            },
            "throughput": {
                "mean_tokens_per_sec": (
                    round(statistics.mean(tokens_per_sec_list), 2)
                    if tokens_per_sec_list
                    else 0
                ),
            },
            "sample_response": (
                responses[0][:500] + "..." if len(responses[0]) > 500 else responses[0]
            ),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        return result

    async def run_head_to_head(
        self,
        models: Optional[List[str]] = None,
        category: Optional[str] = None,
    ) -> BenchmarkReport:
        """Run head-to-head comparison between models.

        Args:
            models: List of model keys to compare (default: all available)
            category: Filter test cases by category

        Returns:
            BenchmarkReport with comparison results
        """
        # Verify models
        self.verify_models()

        # Determine which models to use
        if models:
            models_to_test = [m for m in models if self.available_models.get(m, False)]
        else:
            models_to_test = [
                m for m, available in self.available_models.items() if available
            ]

        if not models_to_test:
            print("❌ No models available. Pull models with: ollama pull <model>")
            return BenchmarkReport(
                timestamp=datetime.now(timezone.utc).isoformat(),
                total_tests=0,
                model_wins={},
                latency_comparison={},
                results=[],
                available_models=self.available_models,
            )

        # Filter test cases by category
        tests_to_run = self.test_cases
        if category:
            tests_to_run = [t for t in self.test_cases if t.get("category") == category]

        print(f"\n{'=' * 60}")
        print(f"🏁 Head-to-Head Benchmark: {', '.join(models_to_test)}")
        print(f"{'=' * 60}")
        print(f"📊 Running {len(tests_to_run)} tests, {self.runs_per_test} runs each")
        print(f"{'=' * 60}\n")

        self.results = []
        model_wins = {m: 0 for m in models_to_test}
        model_latencies = {m: [] for m in models_to_test}

        for i, test_case in enumerate(tests_to_run):
            test_name = test_case.get("name", "Unknown")
            test_category = test_case.get("category", "general")
            prompt = test_case.get("prompt", "")

            print(f"🧪 [{i+1}/{len(tests_to_run)}] {test_name} ({test_category})")

            test_result = HeadToHeadResult(
                test_name=test_name,
                category=test_category,
                models={},
            )

            # Benchmark each model
            for model in models_to_test:
                try:
                    result = await self._run_single_benchmark(model, prompt)

                    if "error" in result:
                        print(f"    ❌ {model}: {result['error']}")
                        test_result.models[model] = result
                    else:
                        test_result.models[model] = result
                        model_latencies[model].append(result["latency"]["mean_ms"])
                        print(
                            f"    ✅ {model}: {result['latency']['mean_ms']}ms (±{result['latency']['stdev_ms']}ms)"
                        )

                except Exception as e:
                    print(f"    ❌ {model}: {str(e)}")
                    test_result.models[model] = {"error": str(e)}

            # Determine winner for this test
            valid_results = {
                k: v for k, v in test_result.models.items() if "latency" in v
            }
            if len(valid_results) >= 2:
                winner = min(
                    valid_results.items(), key=lambda x: x[1]["latency"]["mean_ms"]
                )
                test_result.winner = winner[0]
                test_result.margin_ms = round(
                    max(v["latency"]["mean_ms"] for v in valid_results.values())
                    - winner[1]["latency"]["mean_ms"],
                    2,
                )
                model_wins[winner[0]] += 1
                print(f"    🏆 Winner: {winner[0]} (by {test_result.margin_ms}ms)")

            self.results.append(test_result)
            print()

        # Calculate latency comparison
        latency_comparison = {}
        for model, latencies in model_latencies.items():
            if latencies:
                latency_comparison[model] = {
                    "avg_ms": round(statistics.mean(latencies), 2),
                    "consistency_ms": (
                        round(statistics.stdev(latencies), 2)
                        if len(latencies) > 1
                        else 0
                    ),
                }

        return BenchmarkReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_tests=len(tests_to_run),
            model_wins=model_wins,
            latency_comparison=latency_comparison,
            results=self.results,
            available_models=self.available_models,
        )

    def save_report(
        self, report: BenchmarkReport, output_path: str = "benchmark_report_ollama.json"
    ):
        """Save benchmark report to JSON file.

        Args:
            report: The benchmark report to save
            output_path: Path to save the report
        """
        report_dict = {
            "timestamp": report.timestamp,
            "summary": {
                "total_tests": report.total_tests,
                "model_wins": report.model_wins,
                "latency_comparison": report.latency_comparison,
                "available_models": report.available_models,
            },
            "results": [
                {
                    "test_name": r.test_name,
                    "category": r.category,
                    "winner": r.winner,
                    "margin_ms": r.margin_ms,
                    "models": r.models,
                }
                for r in report.results
            ],
        }

        with open(output_path, "w") as f:
            json.dump(report_dict, f, indent=2)

        print(f"📄 Report saved to: {output_path}")

    def print_summary(self, report: BenchmarkReport):
        """Print benchmark summary to console.

        Args:
            report: The benchmark report to summarize
        """
        print("\n" + "=" * 60)
        print("BENCHMARK SUMMARY")
        print("=" * 60)
        print(f"Timestamp: {report.timestamp}")
        print(f"Total Tests: {report.total_tests}")
        print(f"\nAvailable Models:")
        for model, available in report.available_models.items():
            print(f"  {'✅' if available else '❌'} {model}")

        print(f"\n🏆 Model Wins:")
        for model, wins in sorted(report.model_wins.items(), key=lambda x: -x[1]):
            print(f"  {model}: {wins} wins")

        print(f"\n⏱️ Average Latency:")
        for model, stats in sorted(
            report.latency_comparison.items(), key=lambda x: x[1]["avg_ms"]
        ):
            print(f"  {model}: {stats['avg_ms']}ms (±{stats['consistency_ms']}ms)")

        print("=" * 60)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Vaal AI Empire Ollama Benchmark Executor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with all available models
  python agents/ollama_benchmark_enhanced.py

  # Compare specific models
  python agents/ollama_benchmark_enhanced.py --models kimi-k2.5 glm-5

  # Run only security tests
  python agents/ollama_benchmark_enhanced.py --category security

Setup:
  # Install Ollama
  curl -fsSL https://ollama.com/install.sh | sh

  # Pull models
  ollama pull kimi-k2.5:cloud
  ollama pull glm5
  ollama pull qwen2.5-coder:14b
""",
    )

    parser.add_argument(
        "--models",
        type=str,
        nargs="+",
        help="Models to benchmark (default: all available)",
    )
    parser.add_argument(
        "--category",
        type=str,
        choices=[c.value for c in BenchmarkCategory],
        help="Run tests for specific category",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="benchmark_report_ollama.json",
        help="Output path for report",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="Number of runs per test (default: 3)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Timeout in seconds per model response (default: 120)",
    )
    parser.add_argument(
        "--benchmark-data",
        type=str,
        default="benchmark_data/test_cases.json",
        help="Path to benchmark test cases JSON",
    )

    return parser.parse_args()


async def main():
    """Main entry point."""
    args = parse_args()

    benchmark = OllamaEnhancedBenchmark(
        benchmark_data_path=args.benchmark_data,
        runs_per_test=args.runs,
        timeout=args.timeout,
    )

    # Run benchmark
    report = await benchmark.run_head_to_head(
        models=args.models,
        category=args.category,
    )

    # Print and save results
    benchmark.print_summary(report)
    benchmark.save_report(report, args.output)


if __name__ == "__main__":
    asyncio.run(main())
