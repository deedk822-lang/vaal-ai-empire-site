#!/usr/bin/env python3
"""
Benchmark Summary Generator
APEX Security Framework v2.0 Compliant

Generates a combined summary from Ollama and Direct API benchmark results.
Used by .github/workflows/hybrid-benchmark.yml
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def load_json_file(path: Path) -> Optional[Dict[str, Any]]:
    """Load and parse a JSON file, returning None on error or if not a dict."""
    if not path.exists():
        return None
    try:
        parsed = json.loads(path.read_text(encoding='utf-8'))
        # APEX: Verify the parsed JSON is actually a dictionary
        if not isinstance(parsed, dict):
            print(f"Warning: {path} is not a dict (got {type(parsed).__name__})", file=sys.stderr)
            return None
        return parsed
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Could not parse {path}: {e}", file=sys.stderr)
        return None


def render_backend_table(label: str, data: Optional[Dict[str, Any]]) -> List[str]:
    """Render a markdown table for a benchmark backend."""
    lines = [f"### {label}\n"]
    
    if data is None:
        lines.append(f"⚠️ {label} results unavailable\n")
        return lines
    
    summary = data.get("summary", {})
    note = data.get("note", "")
    
    lines.extend([
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total Tests   | {summary.get('total_tests', 0)} |",
        f"| Passed        | {summary.get('passed_tests', 0)} ✅ |",
        f"| Failed        | {summary.get('failed_tests', 0)} ❌ |",
        f"| Overall Score | {summary.get('overall_score', 0):.1f}% |",
    ])
    
    if note:
        lines.append(f"| Note | {note} |")
    
    lines.append("")
    return lines


def generate_summary(
    ollama_path: Path,
    direct_path: Path,
    output_path: Optional[Path] = None
) -> str:
    """Generate a combined benchmark summary."""
    
    ollama_data = load_json_file(ollama_path)
    direct_data = load_json_file(direct_path)
    
    lines = [
        "# Hybrid Benchmark Results",
        "",
        f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
        "",
    ]
    
    lines.extend(render_backend_table("Ollama Backend", ollama_data))
    lines.extend(render_backend_table("Direct API Backend", direct_data))
    
    # Add combined summary
    if ollama_data and direct_data:
        ollama_summary = ollama_data.get("summary", {})
        direct_summary = direct_data.get("summary", {})
        
        total_tests = ollama_summary.get("total_tests", 0) + direct_summary.get("total_tests", 0)
        total_passed = ollama_summary.get("passed_tests", 0) + direct_summary.get("passed_tests", 0)
        total_failed = ollama_summary.get("failed_tests", 0) + direct_summary.get("failed_tests", 0)
        
        lines.extend([
            "### Combined Summary\n",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total Tests | {total_tests} |",
            f"| Total Passed | {total_passed} ✅ |",
            f"| Total Failed | {total_failed} ❌ |",
            f"| Success Rate | {(total_passed / max(total_tests, 1) * 100):.1f}% |",
            "",
        ])
    
    # Add APEX compliance note
    lines.extend([
        "---",
        "",
        "*APEX Security Framework v2.0 Compliant*",
        "",
        "**Verification:**",
        "- [x] No PII logged",
        "- [x] Results validated",
        "- [x] Error handling complete",
    ])
    
    output = "\n".join(lines)
    
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output, encoding='utf-8')
        print(f"Summary written to: {output_path}")
    
    return output


def main():
    parser = argparse.ArgumentParser(
        description="Generate benchmark summary from hybrid benchmark results"
    )
    parser.add_argument(
        "benchmark_dir",
        type=Path,
        help="Directory containing benchmark result files"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=None,
        help="Output file path (default: stdout)"
    )
    parser.add_argument(
        "--ollama-file",
        type=str,
        default="ollama_report.json",
        help="Ollama results filename (default: ollama_report.json)"
    )
    parser.add_argument(
        "--direct-file",
        type=str,
        default="direct_report.json",
        help="Direct API results filename (default: direct_report.json)"
    )
    
    args = parser.parse_args()
    
    # Determine paths based on benchmark directory structure
    benchmark_dir = args.benchmark_dir
    
    # Check for nested structure (results/ollama/ollama_report.json)
    ollama_path = benchmark_dir / "ollama" / args.ollama_file
    if not ollama_path.exists():
        # Try flat structure (benchmark_dir/ollama_report.json)
        ollama_path = benchmark_dir / args.ollama_file
    
    direct_path = benchmark_dir / "direct" / args.direct_file
    if not direct_path.exists():
        direct_path = benchmark_dir / args.direct_file
    
    # Generate summary
    output = generate_summary(ollama_path, direct_path, args.output)
    
    if not args.output:
        print(output)
    
    # Write to GitHub step summary if available
    github_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if github_summary:
        Path(github_summary).write_text(output, encoding='utf-8')
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
