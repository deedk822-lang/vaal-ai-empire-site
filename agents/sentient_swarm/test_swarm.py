"""
Test script to verify swarm functionality.
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sentient_swarm import (
    SwarmOrchestrator,
    SwarmConfig,
    UnifiedLLMClient,
    EnterpriseMetrics,
    DistributedTracer,
)


async def test_api_keys():
    """Test which API keys are configured."""
    print("\n" + "="*60)
    print("API KEY CONFIGURATION CHECK")
    print("="*60)
    
    keys = {
        'GLM5_API_KEY': os.getenv('GLM5_API_KEY'),
        'KIMI_API_KEY': os.getenv('KIMI_API_KEY'),
        'DASHSCOPE_API_KEY': os.getenv('DASHSCOPE_API_KEY'),
        'GRAFANA_API_KEY': os.getenv('GRAFANA_API_KEY'),
        'PROMETHEUS_API_KEY': os.getenv('PROMETHEUS_API_KEY'),
        'OPENTELEMETRY_API_KEY': os.getenv('OPENTELEMETRY_API_KEY'),
        'CODERABBIT_API_KEY': os.getenv('CODERABBIT_API_KEY'),
        'OLLAMA_API_KEY': os.getenv('OLLAMA_API_KEY'),
        'VERCEL_TOKEN': os.getenv('VERCEL_TOKEN'),
    }
    
    for name, key_exists in keys.items():
        status = "✅" if key_exists else "❌"
        # CodeQL: This only prints presence status ("set"/"not set"), never the actual key value
        presence = "set" if key_exists else "not set"
        print(f"{status} {name}: {presence}")
    
    configured = sum(1 for v in keys.values() if v)
    print(f"\nTotal configured: {configured}/{len(keys)}")
    return configured


async def test_llm_client():
    """Test LLM client with fallbacks."""
    print("\n" + "="*60)
    print("LLM CLIENT TEST")
    print("="*60)
    
    client = UnifiedLLMClient()
    
    # Check available providers
    metrics = client.get_metrics()
    print(f"Available providers: {', '.join(metrics['available_providers'])}")
    
    if not metrics['available_providers']:
        print("⚠️  No LLM providers configured - agents will use local templates")
        return False
    
    # Test generation
    print("\nTesting generation...")
    try:
        response = await client.generate(
            prompt="Generate a one-sentence greeting",
            system_message="You are a helpful assistant.",
            temperature=0.7,
            timeout=30.0
        )
        
        if response.success:
            print(f"✅ Generation successful")
            print(f"   Provider: {response.provider.value}")
            print(f"   Model: {response.model}")
            print(f"   Latency: {response.latency_ms:.0f}ms")
            print(f"   Tokens: {response.tokens_used}")
            print(f"   Content: {response.content[:100]}...")
            return True
        else:
            print(f"❌ Generation failed: {response.error}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False


async def test_metrics():
    """Test metrics collection."""
    print("\n" + "="*60)
    print("METRICS TEST")
    print("="*60)
    
    metrics = EnterpriseMetrics()
    
    # Record some metrics
    metrics.counter("requests", 100, {"status": "200"})
    metrics.counter("requests", 5, {"status": "500"})
    metrics.gauge("active_users", 50)
    
    # Timer
    import time
    with metrics.timer("operation_duration"):
        time.sleep(0.1)
    
    # Export
    prom_output = metrics.export_prometheus()
    print("✅ Prometheus export:")
    print(prom_output[:500])
    print("...")
    
    return True


async def test_tracer():
    """Test distributed tracing."""
    print("\n" + "="*60)
    print("TRACER TEST")
    print("="*60)
    
    tracer = DistributedTracer()
    
    # Create trace
    trace_id = tracer.start_trace("test_operation")
    span1 = tracer.start_span("step_1", trace_id)
    span2 = tracer.start_span("step_2", span1)
    
    tracer.add_event(span2, "checkpoint", message="halfway")
    tracer.end_span(span2)
    tracer.end_span(span1)
    
    # Export
    otlp = tracer.export_otlp()
    print(f"✅ Trace created with {len(otlp['resourceSpans'][0]['scopeSpans'][0]['spans'])} spans")
    
    return True


async def test_swarm_orchestrator():
    """Test swarm orchestrator."""
    print("\n" + "="*60)
    print("SWARM ORCHESTRATOR TEST")
    print("="*60)
    
    config = SwarmConfig(
        project_name="test-project",
        output_dir="output/test",
        run_code_review=False
    )
    
    orchestrator = SwarmOrchestrator(config)
    
    try:
        result = await orchestrator.run(context={
            'company_name': 'Test Company',
            'description': 'AI testing'
        })
        
        print(f"\n✅ Swarm completed in {result.duration_seconds:.2f}s")
        print(f"   Agents successful: {sum(1 for r in result.agent_results if r.get('status') == 'success')}/{len(result.agent_results)}")
        
        # Show generated files
        all_files = []
        for agent_result in result.agent_results:
            all_files.extend(agent_result.get('files', []))
        
        print(f"   Files generated: {len(all_files)}")
        for f in all_files[:5]:
            print(f"      - {f}")
        if len(all_files) > 5:
            print(f"      ... and {len(all_files) - 5} more")
        
        return result.success
        
    except Exception as e:
        print(f"❌ Swarm failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("SENTIENT SWARM - ENTERPRISE TEST SUITE")
    print("="*60)
    
    results = {
        'api_keys': await test_api_keys(),
        'llm_client': await test_llm_client(),
        'metrics': await test_metrics(),
        'tracer': await test_tracer(),
    }
    
    # Only run swarm test if at least one LLM provider is available
    if results['llm_client']:
        results['swarm'] = await test_swarm_orchestrator()
    else:
        print("\n⚠️  Skipping swarm test - no LLM providers configured")
        results['swarm'] = False
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for name, passed in results.items():
        if isinstance(passed, int):
            status = f"✅ {passed} configured"
        elif passed:
            status = "✅ PASSED"
        else:
            status = "❌ FAILED"
        print(f"{name:20s}: {status}")
    
    total_passed = sum(1 for v in results.values() if v is True or (isinstance(v, int) and v > 0))
    total_tests = len([v for v in results.values() if isinstance(v, bool)])
    
    print(f"\nTotal: {total_passed}/{total_tests} tests passed")
    
    def _passed(v):
        return (isinstance(v, bool) and v) or (isinstance(v, int) and v > 0)

    if all(_passed(v) for v in results.values()):
        print("\n✅ ALL TESTS PASSED - SYSTEM READY")
    else:
        print("\n⚠️  SOME TESTS FAILED - CHECK CONFIGURATION")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
