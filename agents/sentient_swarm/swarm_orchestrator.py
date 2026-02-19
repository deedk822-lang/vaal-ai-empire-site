"""
Swarm Orchestrator - Parallel Agent Execution

Uses all your configured API keys:
- GLM5_API_KEY, KIMI_API_KEY, DASHSCOPE_API_KEY (LLMs)
- GRAFANA_API_KEY, PROMETHEUS_API_KEY (Metrics)
- OPENTELEMETRY_API_KEY (Tracing)
- CODERABBIT_API_KEY (Code Review)
- OLLAMA_API_KEY (Local LLM)
- VERCEL_TOKEN (Deployment)
"""

import asyncio
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .agents import (
    AmbientAgent,
    CodeReviewAgent,
    EmpathyAgent,
    MXAgent,
    PerformanceAgent,
    SentientUIAgent,
)
from .api_clients import GrafanaClient, PrometheusClient, UnifiedLLMClient, VercelClient
from .observability import DistributedTracer, EnterpriseMetrics, StructuredLogger


@dataclass
class SwarmConfig:
    """Configuration for swarm execution."""

    project_name: str
    output_dir: str = "output"
    enable_vercel_deploy: bool = False
    run_code_review: bool = True
    max_parallel_agents: int = 6


@dataclass
class SwarmResult:
    """Result of swarm execution."""

    config: SwarmConfig
    start_time: str
    end_time: str
    agent_results: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    traces: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float:
        from datetime import datetime

        start = datetime.fromisoformat(self.start_time.replace("Z", "+00:00"))
        end = datetime.fromisoformat(self.end_time.replace("Z", "+00:00"))
        return (end - start).total_seconds()

    @property
    def success(self) -> bool:
        return len(self.errors) == 0 and all(
            r.get("status") == "success" for r in self.agent_results
        )


class SwarmOrchestrator:
    """
    Main orchestrator for parallel agent execution.

    Executes all 5 pillars simultaneously:
    1. Sentient UI (Liquid Glass)
    2. MX (Machine Experience)
    3. Empathy (Human Connection)
    4. Performance (Core Web Vitals)
    5. Ambient (Zero UI)

    Plus: Code Review
    """

    def __init__(self, config: Optional[SwarmConfig] = None):
        self.config = config or SwarmConfig(project_name="default")

        # Initialize shared infrastructure
        self.llm = UnifiedLLMClient()
        self.metrics = EnterpriseMetrics()
        self.tracer = DistributedTracer()
        self.logger = StructuredLogger("SwarmOrchestrator")

        # Observability clients
        self.grafana = GrafanaClient()
        self.prometheus = PrometheusClient()
        self.vercel = VercelClient()

        # Initialize agents
        self.agents = {
            "sentient_ui": SentientUIAgent(self.llm, self.metrics, self.tracer),
            "mx": MXAgent(self.llm, self.metrics, self.tracer),
            "empathy": EmpathyAgent(self.llm, self.metrics, self.tracer),
            "performance": PerformanceAgent(self.llm, self.metrics, self.tracer),
            "ambient": AmbientAgent(self.llm, self.metrics, self.tracer),
        }

        self.code_review_agent = CodeReviewAgent(self.llm, self.metrics, self.tracer)

    async def run(self, context: Optional[Dict[str, Any]] = None) -> SwarmResult:
        """
        Execute all agents in parallel.

        Args:
            context: Optional context dict passed to agents

        Returns:
            SwarmResult with all outputs
        """
        start_time = datetime.utcnow().isoformat() + "Z"
        trace_id = self.tracer.start_trace("swarm_execution")

        self.logger.info(
            "Swarm execution started",
            project=self.config.project_name,
            trace_id=trace_id,
        )

        print(f"\n{'='*60}")
        print(f"🚀 SWARM EXECUTION: {self.config.project_name}")
        print(f"{'='*60}\n")

        # Execute agents in parallel
        semaphore = asyncio.Semaphore(self.config.max_parallel_agents)

        async def run_agent(name: str, agent):
            async with semaphore:
                self.logger.info(f"Starting agent: {name}")
                span_id = self.tracer.start_span(f"agent_{name}", trace_id)

                try:
                    result = await agent.execute(context or {})
                    self.tracer.end_span(span_id, status="success")
                    self.metrics.counter(
                        "agent_executions", 1, {"agent": name, "status": "success"}
                    )
                    print(f"✅ {name}: Success")
                    return result
                except Exception as e:
                    self.tracer.end_span(span_id, status="error", error=str(e))
                    self.logger.exception(f"Agent {name} failed", e)
                    self.metrics.counter(
                        "agent_executions", 1, {"agent": name, "status": "error"}
                    )
                    print(f"❌ {name}: Failed - {e}")
                    return {"agent": name, "status": "error", "error": str(e)}

        # Run all agents
        tasks = [run_agent(name, agent) for name, agent in self.agents.items()]
        agent_results = await asyncio.gather(*tasks)

        # Code review
        if self.config.run_code_review:
            print("\n🔍 Running code review...")
            all_files = []
            for result in agent_results:
                if result.get("status") == "success":
                    all_files.extend(result.get("files", []))

            review_result = await self.code_review_agent.execute(
                {"files": all_files, "output_dir": self.config.output_dir}
            )
            agent_results.append(review_result)

        # Export observability data
        print("\n📊 Exporting observability data...")

        # Prometheus metrics
        prom_metrics = self.metrics.export_prometheus()
        prom_file = os.path.join(self.config.output_dir, "metrics.prom")
        os.makedirs(self.config.output_dir, exist_ok=True)
        with open(prom_file, "w") as f:
            f.write(prom_metrics)

        # Traces
        traces = self.tracer.export_otlp()
        traces_file = os.path.join(self.config.output_dir, "traces.json")
        with open(traces_file, "w") as f:
            json.dump(traces, f, indent=2)

        # LLM metrics
        llm_metrics = self.llm.get_metrics()

        end_time = datetime.utcnow().isoformat() + "Z"

        # Create result
        result = SwarmResult(
            config=self.config,
            start_time=start_time,
            end_time=end_time,
            agent_results=list(agent_results),
            metrics={
                "llm_usage": llm_metrics,
                "prometheus_file": prom_file,
                "traces_file": traces_file,
            },
            traces=traces,
        )

        # Summary
        print(f"\n{'='*60}")
        print("📋 EXECUTION SUMMARY")
        print(f"{'='*60}")
        print(f"Duration: {result.duration_seconds:.2f}s")
        print(
            f"Agents: {len([r for r in agent_results if r.get('status') == 'success'])}/{len(agent_results)}"
        )
        print(f"Files generated: {sum(len(r.get('files', [])) for r in agent_results)}")
        print(
            f"LLM providers used: {', '.join(llm_metrics.get('available_providers', []))}"
        )

        if result.success:
            print("\n✅ SWARM EXECUTION SUCCESSFUL")
        else:
            print("\n⚠️  SWARM EXECUTION COMPLETED WITH ERRORS")

        print(f"{'='*60}\n")

        # Annotate in Grafana
        await self.grafana.annotate(
            f"Swarm execution: {self.config.project_name}",
            tags=["swarm", "deployment" if result.success else "failed"],
        )

        self.logger.info(
            "Swarm execution completed",
            project=self.config.project_name,
            duration=result.duration_seconds,
            success=result.success,
        )

        return result

    async def deploy_to_vercel(self, files: Dict[str, str]) -> Dict[str, Any]:
        """Deploy to Vercel using VERCEL_TOKEN."""
        if not self.config.enable_vercel_deploy:
            return {"success": False, "error": "Vercel deploy not enabled"}

        self.logger.info("Deploying to Vercel", project=self.config.project_name)

        result = await self.vercel.deploy(
            project_name=self.config.project_name, files=files
        )

        if result.get("success"):
            self.logger.info("Vercel deployment successful", url=result.get("url"))
        else:
            self.logger.error("Vercel deployment failed", error=result.get("error"))

        return result

    def get_metrics_report(self) -> Dict[str, Any]:
        """Get comprehensive metrics report."""
        return {
            "llm": self.llm.get_metrics(),
            "swarm": self.metrics.get_summary(),
            "project": self.config.project_name,
        }
