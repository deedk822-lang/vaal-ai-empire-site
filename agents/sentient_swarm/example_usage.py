#!/usr/bin/env python3
"""
Example usage of the Enterprise Swarm.

This demonstrates how to use all your configured API keys.
"""

import asyncio
import os
import sys
from pathlib import Path

# Ensure package can be imported when running as standalone script
if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from .swarm_orchestrator import SwarmConfig, SwarmOrchestrator


async def main():
    """Run the enterprise swarm."""

    print("=" * 70)
    print("Enterprise Swarm - Example Usage")
    print("=" * 70)
    print()

    # Check API keys
    print("Checking API Configuration:")
    apis = {
        "GLM5_API_KEY": os.getenv("GLM5_API_KEY"),
        "KIMI_API_KEY": os.getenv("KIMI_API_KEY"),
        "DASHSCOPE_API_KEY": os.getenv("DASHSCOPE_API_KEY"),
        "CODERABBIT_API_KEY": os.getenv("CODERABBIT_API_KEY"),
        "GRAFANA_API_KEY": os.getenv("GRAFANA_API_KEY"),
        "PROMETHEUS_API_KEY": os.getenv("PROMETHEUS_API_KEY"),
        "OPENTELEMETRY_API_KEY": os.getenv("OPENTELEMETRY_API_KEY"),
        "OLLAMA_API_KEY": os.getenv("OLLAMA_API_KEY"),
        "VERCEL_TOKEN": os.getenv("VERCEL_TOKEN"),
    }

    configured = 0
    for name, value in apis.items():
        status = "✅" if value else "❌"
        if value:
            configured += 1
        print(f"  {status} {name}")

    print()
    print(f"Configured: {configured}/{len(apis)} APIs")
    print()

    if configured == 0:
        print("❌ No APIs configured. Set environment variables first.")
        return

    # Configure swarm
    config = SwarmConfig(
        project_name="my-awesome-project",
        output_dir="swarm-output",
        run_code_review=True,
        enable_vercel_deploy=False,
        max_parallel_agents=6,
    )

    print("Configuration:")
    print(f"  Project: {config.project_name}")
    print(f"  Output: {config.output_dir}")
    print(f"  Code Review: {config.enable_code_review}")
    print(f"  Parallel Agents: {config.max_parallel_agents}")
    print()

    # Execute swarm
    orchestrator = SwarmOrchestrator(config)

    try:
        result = await orchestrator.run(
            {
                "company_name": "My Company",
                "description": "AI-powered solutions",
                "url": "https://example.com",
            }
        )

        # Print detailed results
        print()
        print("=" * 70)
        print("RESULTS")
        print("=" * 70)
        print(f"Success: {result.success}")
        print(f"Duration: {result.duration_seconds:.2f}s")

        # Collect files
        all_files = []
        for agent_result in result.agent_results:
            all_files.extend(agent_result.get("files", []))

        print(f"Files Generated: {len(all_files)}")
        print()

        # List files
        print("Generated Files:")
        for filepath in all_files[:10]:
            print(f"  - {filepath}")
        if len(all_files) > 10:
            print(f"  ... and {len(all_files) - 10} more")

        # Show metrics
        print()
        print("Metrics:")
        metrics = orchestrator.get_metrics_report()
        print(f"  LLM Usage: {metrics['llm']}")
        print(f"  Swarm Metrics: {metrics['swarm']}")

    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
