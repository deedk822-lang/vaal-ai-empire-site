#!/usr/bin/env python3
"""
Swarm Auto-Fixer: Uses Qwen 3.5-Plus to analyze PR diffs and generate fixes.
APEX Security Framework v2.0 Compliant

Usage:
    python agents/swarm_autofixer.py \
        --pr-number 134 \
        --diff-file pr-diff.txt \
        --output-dir swarm-fixes/ \
        --model qwen3.5-plus
"""
import os
import sys
import json
import argparse
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

# APEX Invariant: Structured logging without PII
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


class FixSuggestion:
    """Single fix suggestion from Qwen 3.5-Plus."""
    
    def __init__(
        self,
        file_path: str,
        issue_type: str,
        severity: str,
        description: str,
        suggested_fix: str,
        line_number: Optional[int] = None,
        confidence: float = 0.8
    ):
        self.file_path = file_path
        self.line_number = line_number
        self.issue_type = issue_type
        self.severity = severity
        self.description = description
        self.suggested_fix = suggested_fix
        self.confidence = confidence
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "line_number": self.line_number,
            "issue_type": self.issue_type,
            "severity": self.severity,
            "description": self.description,
            "suggested_fix": self.suggested_fix,
            "confidence": self.confidence
        }


class SwarmAnalysisResult:
    """Complete analysis result."""
    
    def __init__(
        self,
        pr_number: int,
        files_analyzed: int = 0,
        issues_found: int = 0,
        fixes_generated: int = 0,
        duration_ms: int = 0,
        suggestions: Optional[List[FixSuggestion]] = None,
        timestamp: Optional[str] = None
    ):
        self.pr_number = pr_number
        self.files_analyzed = files_analyzed
        self.issues_found = issues_found
        self.fixes_generated = fixes_generated
        self.duration_ms = duration_ms
        self.suggestions = suggestions or []
        self.timestamp = timestamp or datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pr_number": self.pr_number,
            "files_analyzed": self.files_analyzed,
            "issues_found": self.issues_found,
            "fixes_generated": self.fixes_generated,
            "duration_ms": self.duration_ms,
            "suggestions": [s.to_dict() for s in self.suggestions],
            "timestamp": self.timestamp
        }


class SwarmAutoFixer:
    """Real Swarm Auto-Fixer using Qwen 3.5-Plus."""
    
    def __init__(
        self,
        api_key: str,
        model: str = "qwen3.5-plus",
        base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self._client = None
        logger.info(f"✓ Swarm Auto-Fixer initialized with {model}")
    
    @property
    def client(self):
        """Lazy-load the OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            except ImportError:
                logger.warning("openai package not installed - using placeholder mode")
                return None
        return self._client
    
    def analyze_diff(self, diff_content: str, pr_number: int) -> SwarmAnalysisResult:
        """Analyze PR diff and generate fix suggestions."""
        start_time = datetime.now()
        
        # Handle empty diff
        if not diff_content or not diff_content.strip():
            logger.warning("⚠ Empty diff - no analysis needed")
            return SwarmAnalysisResult(pr_number=pr_number)
        
        # Truncate if too large
        max_diff_size = 500000
        if len(diff_content) > max_diff_size:
            logger.warning(f"⚠ Diff truncated from {len(diff_content)} to {max_diff_size} chars")
            diff_content = diff_content[:max_diff_size] + "\n\n[...truncated...]"
        
        # If no API client, return placeholder
        if not self.client:
            logger.warning("⚠ No API client available - returning placeholder")
            return SwarmAnalysisResult(
                pr_number=pr_number,
                files_analyzed=1,
                duration_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )
        
        system_prompt = """You are an expert code reviewer for a South African fintech platform.
Analyze the PR diff and identify issues in these categories:
1. Security (PayFast integration, XRPL settlements, API keys, SQL injection)
2. Performance (database queries, API calls, loops, memory usage)
3. Code Quality (unused variables, imports, error handling, logging)
4. Compliance (POPIA data protection, ZAR currency handling)
5. Best Practices (naming conventions, documentation, test coverage)

For each issue found, provide a JSON object with:
- file_path: Exact path to the file
- line_number: Line number if applicable (null if not)
- issue_type: Category of issue
- severity: low|medium|high|critical
- description: Clear explanation of the problem
- suggested_fix: Exact code change or fix description
- confidence: 0.0-1.0 confidence score

Output format: JSON array of objects.
If no issues found, return empty array [].

Be precise. Only flag real issues, not style preferences."""

        user_prompt = f"""PR #{pr_number} Diff:
```
{diff_content}
```

Analyze this diff and return fix suggestions as a JSON array."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=4000
            )
            
            content = response.choices[0].message.content.strip()
            
            # Extract JSON from response
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                suggestions_data = json.loads(json_match.group())
            else:
                suggestions_data = []
            
            suggestions = [
                FixSuggestion(
                    file_path=s.get("file_path", "unknown"),
                    issue_type=s.get("issue_type", "unknown"),
                    severity=s.get("severity", "low"),
                    description=s.get("description", ""),
                    suggested_fix=s.get("suggested_fix", ""),
                    line_number=s.get("line_number"),
                    confidence=s.get("confidence", 0.8)
                )
                for s in suggestions_data
            ]
            
        except Exception as e:
            logger.error(f"✗ Qwen analysis failed: {e}")
            suggestions = []
        
        end_time = datetime.now()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)
        
        files_analyzed = len(set(s.file_path for s in suggestions)) if suggestions else 1
        
        result = SwarmAnalysisResult(
            pr_number=pr_number,
            files_analyzed=files_analyzed,
            issues_found=len(suggestions),
            fixes_generated=len(suggestions),
            duration_ms=duration_ms,
            suggestions=suggestions
        )
        
        logger.info(f"📊 Analysis complete: {result.issues_found} issues in {duration_ms}ms")
        return result
    
    def generate_fix_files(self, result: SwarmAnalysisResult, output_dir: str) -> int:
        """Generate fix files from suggestions."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        if not result.suggestions:
            # Write empty result file
            summary_file = output_path / "summary.json"
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(result.to_dict(), f, indent=2)
            logger.info(f"📄 No fixes needed. Summary written to {summary_file}")
            return 0
        
        files_written = 0
        
        # Group by file
        by_file: Dict[str, List[FixSuggestion]] = {}
        for suggestion in result.suggestions:
            if suggestion.file_path not in by_file:
                by_file[suggestion.file_path] = []
            by_file[suggestion.file_path].append(suggestion)
        
        for file_path, suggestions in by_file.items():
            safe_name = file_path.replace('/', '_').replace('\\', '_')
            fix_file = output_path / f"fix_{safe_name}.md"
            
            with open(fix_file, 'w', encoding='utf-8') as f:
                f.write(f"# Auto-Generated Fixes for `{file_path}`\n\n")
                f.write(f"**PR #{result.pr_number}** | Generated: {result.timestamp}\n\n")
                f.write(f"**Issues Found:** {len(suggestions)}\n\n---\n\n")
                
                for i, suggestion in enumerate(suggestions, 1):
                    f.write(f"## Issue {i}: {suggestion.issue_type}\n\n")
                    f.write(f"**Severity:** {suggestion.severity.upper()}\n\n")
                    f.write(f"**Line:** {suggestion.line_number or 'N/A'}\n\n")
                    f.write(f"**Description:** {suggestion.description}\n\n")
                    f.write(f"**Suggested Fix:**\n```diff\n{suggestion.suggested_fix}\n```\n\n")
                    f.write(f"**Confidence:** {suggestion.confidence:.0%}\n\n---\n\n")
            
            files_written += 1
            logger.info(f"✅ Generated fix file: {fix_file}")
        
        # Write summary JSON
        summary_file = output_path / "summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, indent=2)
        
        logger.info(f"📄 Summary written to {summary_file}")
        return files_written


def main():
    parser = argparse.ArgumentParser(description="Swarm Auto-Fixer")
    parser.add_argument("--pr-number", required=True, help="PR number to analyze")
    parser.add_argument("--diff-file", required=True, help="Path to PR diff file")
    parser.add_argument("--output-dir", default="swarm-fixes/", help="Output directory")
    parser.add_argument("--model", default="qwen3.5-plus", help="Qwen model")
    args = parser.parse_args()
    
    api_key = os.getenv("DASHSCOPE_API_KEY")
    
    if not api_key:
        logger.warning("⚠ DASHSCOPE_API_KEY not set - using placeholder mode")
        result = SwarmAnalysisResult(pr_number=int(args.pr_number))
        output_path = Path(args.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        with open(output_path / "summary.json", 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, indent=2)
        
        # Output for GitHub Actions
        print(f"files_generated=0")
        print(f"duration_ms=0")
        print(f"issues_found=0")
        
        # Write to GITHUB_OUTPUT if available
        github_output = os.environ.get("GITHUB_OUTPUT")
        if github_output:
            with open(github_output, "a", encoding='utf-8') as f:
                f.write("files_generated=0\n")
                f.write("duration_ms=0\n")
                f.write("issues_found=0\n")
        
        sys.exit(0)
    
    # Read diff file
    diff_path = Path(args.diff_file)
    if not diff_path.exists():
        logger.error(f"❌ Diff file not found: {args.diff_file}")
        diff_content = ""
    else:
        with open(diff_path, 'r', encoding='utf-8') as f:
            diff_content = f.read()
    
    # Run analysis
    fixer = SwarmAutoFixer(api_key=api_key, model=args.model)
    result = fixer.analyze_diff(diff_content, int(args.pr_number))
    files_written = fixer.generate_fix_files(result, args.output_dir)
    result.fixes_generated = files_written
    
    # Output for GitHub Actions
    print(f"files_generated={result.fixes_generated}")
    print(f"duration_ms={result.duration_ms}")
    print(f"issues_found={result.issues_found}")
    
    # Write to GITHUB_OUTPUT if available
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding='utf-8') as f:
            f.write(f"files_generated={result.fixes_generated}\n")
            f.write(f"duration_ms={result.duration_ms}\n")
            f.write(f"issues_found={result.issues_found}\n")
    
    logger.info(f"✅ Swarm Auto-Fixer complete: {result.fixes_generated} files generated")
    sys.exit(0)


if __name__ == "__main__":
    main()
