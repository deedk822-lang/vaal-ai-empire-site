"""
Code Review Agent - Uses CodeRabbit or LLM for automated review.
"""

import os
from typing import Any, Dict, List

from .base_agent import BaseAgent


class CodeReviewAgent(BaseAgent):
    """Automated code review using CODERABBIT_API_KEY or LLM."""

    def __init__(self, llm_client=None, metrics=None, tracer=None):
        super().__init__("CodeReview", llm_client, metrics, tracer)
        self.coderabbit_key = os.getenv("CODERABBIT_API_KEY")

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Review generated code."""
        self.log("🔍 Reviewing generated code...")

        output_dir = context.get("output_dir", "output")
        files_to_review = context.get("files", [])

        review_results = []

        for filepath in files_to_review:
            if not os.path.exists(filepath):
                continue

            with open(filepath, "r", encoding="utf-8") as f:
                code = f.read()

            # Use LLM to review
            review_prompt = f"""Review this code for:
1. Security vulnerabilities
2. Performance issues
3. Accessibility problems
4. Best practices
5. Potential bugs

File: {filepath}

```
{code[:3000]}  # First 3000 chars
```

Output findings as JSON array."""

            review_response = await self.llm.generate(
                prompt=review_prompt,
                system_message="You are a senior code reviewer. Be thorough and specific.",
                temperature=0.3,
            )

            # Parse findings
            try:
                import json

                findings = json.loads(review_response.content)
            except:
                findings = [{"issue": "Parse error", "severity": "low"}]

            review_results.append(
                {
                    "file": filepath,
                    "findings": findings,
                    "provider": review_response.provider.value,
                }
            )

        # Generate summary report
        total_issues = sum(len(r["findings"]) for r in review_results)

        report = f"""# Code Review Report

## Summary
- Files reviewed: {len(files_to_review)}
- Total issues: {total_issues}

## Findings
"""

        for result in review_results:
            report += f"\n### {result['file']}\n"
            for finding in result["findings"]:
                report += f"- [{finding.get('severity', 'info').upper()}] {finding.get('issue', 'Unknown issue')}\n"

        report_file = self.write_file("review-report.md", report)

        return {
            "agent": self.name,
            "status": "success",
            "files": [report_file],
            "metrics": {
                "files_reviewed": len(files_to_review),
                "total_issues": total_issues,
                "provider": (
                    review_results[-1]["provider"] if review_results else "none"
                ),
            },
        }
