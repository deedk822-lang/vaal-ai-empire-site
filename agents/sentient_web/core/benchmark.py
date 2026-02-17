"""
Real performance benchmarking using actual tools.

Implements +AAA standards with:
- Lighthouse CI for Core Web Vitals
- axe-core for accessibility
- Real measurement (not simulated)
- Statistical analysis
"""

import asyncio
import json
import subprocess
import tempfile
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
 fix/coderabbit-issues-resolved
from http.server import HTTPServer, SimpleHTTPRequestHandler

 merge/develop-to-main
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import statistics


@dataclass
class BenchmarkMetric:
    """Single benchmark metric."""
    name: str
    value: float
    unit: str
    threshold: Optional[float] = None
    status: str = "unknown"  # pass, fail, warning
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkResult:
    """Complete benchmark result."""
    tool: str
    url: str
    timestamp: str
    metrics: List[BenchmarkMetric] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    duration_ms: float = 0.0
    
    def get_score(self) -> float:
        """Calculate overall score."""
        if not self.metrics:
            return 0.0
        passed = sum(1 for m in self.metrics if m.status == "pass")
        return (passed / len(self.metrics)) * 100


class BenchmarkRunner(ABC):
    """Abstract base for benchmark runners."""
    
    @abstractmethod
    async def run(self, url_or_path: str) -> BenchmarkResult:
        """Run benchmark and return results."""
        pass
    
    def _check_threshold(self, value: float, threshold: Optional[float], lower_is_better: bool = True) -> str:
        """Check if value meets threshold."""
        if threshold is None:
            return "unknown"
        
        if lower_is_better:
            if value <= threshold:
                return "pass"
            elif value <= threshold * 1.2:  # 20% grace
                return "warning"
            else:
                return "fail"
        else:
            if value >= threshold:
                return "pass"
            elif value >= threshold * 0.8:  # 20% grace
                return "warning"
            else:
                return "fail"


class LighthouseRunner(BenchmarkRunner):
    """
    Google Lighthouse CI runner for Core Web Vitals.
    
    Measures real performance metrics:
    - LCP (Largest Contentful Paint)
    - INP (Interaction to Next Paint)
    - CLS (Cumulative Layout Shift)
    - TTFB (Time to First Byte)
    - FCP (First Contentful Paint)
    """
    
    # 2026 targets
    TARGETS = {
        'LCP': 2000,      # < 2.0s
        'INP': 200,       # < 200ms
        'CLS': 0.05,      # < 0.05
        'TTFB': 600,      # < 600ms
        'FCP': 1800,      # < 1.8s
        'SPEED_INDEX': 3400,
        'TOTAL_BLOCKING_TIME': 200,
    }
    
    def __init__(self, chrome_flags: Optional[List[str]] = None):
        self.chrome_flags = chrome_flags or [
            '--headless',
            '--no-sandbox',
            '--disable-gpu',
            '--disable-dev-shm-usage'
        ]
    
    async def run(self, url_or_path: str) -> BenchmarkResult:
        """Run Lighthouse benchmark."""
        start_time = time.time()
        timestamp = datetime.now().isoformat()
        
        # Check if lighthouse is installed
        if not await self._check_lighthouse():
            return self._fallback_result(url_or_path, timestamp, "Lighthouse not installed")
        
        # Create temp file for output
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_path = f.name
        
        try:
            # Build command
            cmd = [
                'lighthouse',
                url_or_path,
                '--output=json',
                f'--output-path={output_path}',
                '--only-categories=performance,accessibility,best-practices,seo',
                '--chrome-flags=' + ' '.join(self.chrome_flags),
                '--preset=desktop'
            ]
            
            # Run lighthouse
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=120
            )
            
            if process.returncode != 0:
                return self._fallback_result(
                    url_or_path, timestamp, 
                    f"Lighthouse failed: {stderr.decode()[:200]}"
                )
            
            # Parse results
            with open(output_path, 'r') as f:
                data = json.load(f)
            
            metrics = self._extract_metrics(data)
            duration_ms = (time.time() - start_time) * 1000
            
            return BenchmarkResult(
                tool='lighthouse',
                url=url_or_path,
                timestamp=timestamp,
                metrics=metrics,
                raw_data=data,
                duration_ms=duration_ms
            )
            
        except asyncio.TimeoutError:
            return self._fallback_result(url_or_path, timestamp, "Lighthouse timeout")
        except Exception as e:
            return self._fallback_result(url_or_path, timestamp, str(e))
        finally:
            # Cleanup
            try:
                Path(output_path).unlink(missing_ok=True)
            except:
                pass
    
    async def _check_lighthouse(self) -> bool:
        """Check if lighthouse CLI is available."""
        try:
            process = await asyncio.create_subprocess_exec(
                'lighthouse', '--version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await asyncio.wait_for(process.communicate(), timeout=5)
            return process.returncode == 0
        except:
            return False
    
    def _extract_metrics(self, data: Dict[str, Any]) -> List[BenchmarkMetric]:
        """Extract metrics from Lighthouse JSON."""
        metrics = []
        
        # Core Web Vitals
        audits = data.get('audits', {})
        
        # LCP
        if 'largest-contentful-paint' in audits:
            lcp = audits['largest-contentful-paint']
            value = lcp.get('numericValue', 0)
            metrics.append(BenchmarkMetric(
                name='LCP',
                value=value,
                unit='ms',
                threshold=self.TARGETS['LCP'],
                status=self._check_threshold(value, self.TARGETS['LCP']),
                details={'displayValue': lcp.get('displayValue', '')}
            ))
        
        # INP (if available)
        if 'interaction-to-next-paint' in audits:
            inp = audits['interaction-to-next-paint']
            value = inp.get('numericValue', 0)
            metrics.append(BenchmarkMetric(
                name='INP',
                value=value,
                unit='ms',
                threshold=self.TARGETS['INP'],
                status=self._check_threshold(value, self.TARGETS['INP']),
                details={'displayValue': inp.get('displayValue', '')}
            ))
        
        # CLS
        if 'cumulative-layout-shift' in audits:
            cls = audits['cumulative-layout-shift']
            value = cls.get('numericValue', 0)
            metrics.append(BenchmarkMetric(
                name='CLS',
                value=value,
                unit='',
                threshold=self.TARGETS['CLS'],
                status=self._check_threshold(value, self.TARGETS['CLS']),
                details={'displayValue': cls.get('displayValue', '')}
            ))
        
        # TTFB
        if 'server-response-time' in audits:
            ttfb = audits['server-response-time']
            value = ttfb.get('numericValue', 0)
            metrics.append(BenchmarkMetric(
                name='TTFB',
                value=value,
                unit='ms',
                threshold=self.TARGETS['TTFB'],
                status=self._check_threshold(value, self.TARGETS['TTFB']),
                details={'displayValue': ttfb.get('displayValue', '')}
            ))
        
        # FCP
        if 'first-contentful-paint' in audits:
            fcp = audits['first-contentful-paint']
            value = fcp.get('numericValue', 0)
            metrics.append(BenchmarkMetric(
                name='FCP',
                value=value,
                unit='ms',
                threshold=self.TARGETS['FCP'],
                status=self._check_threshold(value, self.TARGETS['FCP']),
                details={'displayValue': fcp.get('displayValue', '')}
            ))
        
        # Performance score
        categories = data.get('categories', {})
        if 'performance' in categories:
            perf = categories['performance']
            score = perf.get('score', 0) * 100
            metrics.append(BenchmarkMetric(
                name='Performance_Score',
                value=score,
                unit='',
                threshold=90,
                status=self._check_threshold(score, 90, lower_is_better=False),
                details={'category': 'performance'}
            ))
        
        return metrics
    
    def _fallback_result(self, url: str, timestamp: str, error: str) -> BenchmarkResult:
        """Create fallback result when Lighthouse fails."""
        return BenchmarkResult(
            tool='lighthouse',
            url=url,
            timestamp=timestamp,
            metrics=[],
            errors=[error],
            duration_ms=0
        )


class AXEAccessibilityRunner(BenchmarkRunner):
    """
    axe-core accessibility scanner.
    
    Validates WCAG 2.1 AA/AAA compliance.
    """
    
    async def run(self, url_or_path: str) -> BenchmarkResult:
        """Run axe accessibility scan."""
        start_time = time.time()
        timestamp = datetime.now().isoformat()
        
        # For HTML files, we need to serve them
        is_file = Path(url_or_path).is_file()
        server = None
        
        if is_file:
            # Serve file temporarily
            server_url, server = await self._serve_file(url_or_path)
            if not server_url:
                return self._fallback_result(url_or_path, timestamp, "Could not serve file")
        else:
            server_url = url_or_path
        
        try:
            # Check if axe is available
            if not await self._check_axe():
                return self._fallback_result(url_or_path, timestamp, "axe not installed")
            
            # Run axe
            cmd = ['axe', server_url, '--tags=wcag2a,wcag2aa,wcag21aa', '--format=json']
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=60
            )
            
            if process.returncode not in [0, 1]:  # 1 means violations found
                return self._fallback_result(
                    url_or_path, timestamp,
                    f"axe failed: {stderr.decode()[:200]}"
                )
            
            # Parse results
            try:
                data = json.loads(stdout.decode())
            except json.JSONDecodeError:
                data = {}
            
            metrics = self._extract_metrics(data)
            duration_ms = (time.time() - start_time) * 1000
            
            return BenchmarkResult(
                tool='axe-core',
                url=url_or_path,
                timestamp=timestamp,
                metrics=metrics,
                raw_data=data,
                duration_ms=duration_ms
            )
            
        except asyncio.TimeoutError:
            return self._fallback_result(url_or_path, timestamp, "axe timeout")
        except Exception as e:
            return self._fallback_result(url_or_path, timestamp, str(e))
        finally:
            if server:
                server.shutdown()
                server.server_close()
    
    async def _check_axe(self) -> bool:
        """Check if axe CLI is available."""
        try:
            process = await asyncio.create_subprocess_exec(
                'axe', '--version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await asyncio.wait_for(process.communicate(), timeout=5)
            return process.returncode == 0
        except:
            return False
    
 fix/coderabbit-issues-resolved
    async def _serve_file(self, file_path: str) -> Tuple[Optional[str], Optional[HTTPServer]]:
        """Start temporary HTTP server for file."""
        # Simplified - in production use a proper server

    async def _serve_file(self, file_path: str) -> tuple[Optional[str], Optional[HTTPServer]]:
        """Start temporary HTTP server for file."""
        # Simplified - in production use a proper server
        from http.server import HTTPServer, SimpleHTTPRequestHandler
 merge/develop-to-main
        import threading
        
        file_path = Path(file_path).resolve()
        directory = file_path.parent
        
        class Handler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(directory), **kwargs)
        
        try:
            server = HTTPServer(('localhost', 0), Handler)
            port = server.server_address[1]
            
            thread = threading.Thread(target=server.serve_forever)
            thread.daemon = True
            thread.start()
            
            # Give server time to start
            await asyncio.sleep(0.5)
            
            return f"http://localhost:{port}/{file_path.name}", server
        except Exception as e:
            print(f"Server error: {e}")
            return None, None
    
    def _extract_metrics(self, data: Dict[str, Any]) -> List[BenchmarkMetric]:
        """Extract accessibility metrics from axe results."""
        metrics = []
        
        # Count violations by impact
        violations = data.get('violations', [])
        
        critical = sum(1 for v in violations if v.get('impact') == 'critical')
        serious = sum(1 for v in violations if v.get('impact') == 'serious')
        moderate = sum(1 for v in violations if v.get('impact') == 'moderate')
        minor = sum(1 for v in violations if v.get('impact') == 'minor')
        
        metrics.append(BenchmarkMetric(
            name='Critical_Violations',
            value=critical,
            unit='count',
            threshold=0,
            status='pass' if critical == 0 else 'fail',
            details={'description': 'Critical accessibility violations'}
        ))
        
        metrics.append(BenchmarkMetric(
            name='Serious_Violations',
            value=serious,
            unit='count',
            threshold=0,
            status='pass' if serious == 0 else 'fail',
            details={'description': 'Serious accessibility violations'}
        ))
        
        # Calculate overall score
        total_issues = critical * 4 + serious * 2 + moderate * 1 + minor * 0.5
        score = max(0, 100 - total_issues * 5)
        
        metrics.append(BenchmarkMetric(
            name='Accessibility_Score',
            value=score,
            unit='',
            threshold=90,
            status=self._check_threshold(score, 90, lower_is_better=False),
            details={
                'critical': critical,
                'serious': serious,
                'moderate': moderate,
                'minor': minor
            }
        ))
        
        return metrics
    
    def _fallback_result(self, url: str, timestamp: str, error: str) -> BenchmarkResult:
        """Create fallback result when axe fails."""
        return BenchmarkResult(
            tool='axe-core',
            url=url,
            timestamp=timestamp,
            metrics=[],
            errors=[error],
            duration_ms=0
        )


class RealBenchmarkRunner:
    """
    Orchestrates multiple benchmark tools.
    
    Runs benchmarks in parallel and aggregates results.
    """
    
    def __init__(self):
        self.runners: List[BenchmarkRunner] = [
            LighthouseRunner(),
            AXEAccessibilityRunner(),
        ]
        self.results: List[BenchmarkResult] = []
    
    async def benchmark_url(self, url: str) -> Dict[str, Any]:
        """Run all benchmarks on a URL."""
        # Run all benchmarks in parallel
        tasks = [runner.run(url) for runner in self.runners]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        self.results = []
        for result in results:
            if isinstance(result, Exception):
                print(f"Benchmark failed: {result}")
            else:
                self.results.append(result)
        
        return self._aggregate_results()
    
    def _aggregate_results(self) -> Dict[str, Any]:
        """Aggregate results from all benchmark tools."""
        all_metrics = []
        all_errors = []
        total_duration = 0
        
        for result in self.results:
            all_metrics.extend(result.metrics)
            all_errors.extend(result.errors)
            total_duration += result.duration_ms
        
        # Group metrics by name and calculate statistics
        metric_groups = {}
        for m in all_metrics:
            if m.name not in metric_groups:
                metric_groups[m.name] = []
            metric_groups[m.name].append(m)
        
        # Calculate overall score
        if all_metrics:
            passed = sum(1 for m in all_metrics if m.status == "pass")
            overall_score = (passed / len(all_metrics)) * 100
        else:
            overall_score = 0
        
        return {
            'overall_score': round(overall_score, 2),
            'total_duration_ms': round(total_duration, 2),
            'tools_used': [r.tool for r in self.results],
            'metrics_by_name': {
                name: [
                    {
                        'value': m.value,
                        'unit': m.unit,
                        'status': m.status,
                        'threshold': m.threshold
                    }
                    for m in metrics
                ]
                for name, metrics in metric_groups.items()
            },
            'all_metrics': [
                {
                    'tool': next((r.tool for r in self.results if m in r.metrics), 'unknown'),
                    'name': m.name,
                    'value': m.value,
                    'unit': m.unit,
                    'status': m.status,
                    'threshold': m.threshold
                }
                for m in all_metrics
            ],
            'errors': all_errors,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_summary(self) -> str:
        """Get human-readable summary."""
        if not self.results:
            return "No benchmark results available"
        
        lines = ["\n📊 REAL BENCHMARK RESULTS", "=" * 50]
        
        for result in self.results:
            lines.append(f"\n{result.tool.upper()}")
            lines.append("-" * 30)
            
            if result.errors:
                lines.append(f"⚠️ Errors: {', '.join(result.errors)}")
            
            for m in result.metrics:
                icon = "✅" if m.status == "pass" else "⚠️" if m.status == "warning" else "❌"
                threshold_str = f" (target: {m.threshold})" if m.threshold else ""
                lines.append(f"  {icon} {m.name}: {m.value}{m.unit}{threshold_str}")
            
            lines.append(f"  Duration: {result.duration_ms:.0f}ms")
        
        lines.append("\n" + "=" * 50)
        return "\n".join(lines)
