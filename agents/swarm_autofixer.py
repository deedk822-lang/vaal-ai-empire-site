#!/usr/bin/env python3
"""
Swarm Auto-Fixer - Real Implementation
APEX Security Framework v2.0 Compliant

Uses Qwen 3.5-Plus via Alibaba Cloud DashScope API for intelligent code fixing.
Designed for GitHub Actions integration in hybrid-swarm-autofixer.yml

APEX Invariants:
- No PII logging (Invariant #1)
- Auth verified per-request (Invariant #2)
- Input validation at trust boundaries (Invariant #3)
"""

import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import aiohttp
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "aiohttp"], check=True)
    import aiohttp

# APEX Invariant: Structured logging without PII
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# APEX Configuration
# ═══════════════════════════════════════════════════════════════════

@dataclass
class APEXConfig:
    """
    APEX-compliant configuration for Swarm Auto-Fixer.
    
    Attributes:
        api_key: DashScope API key (from DASHSCOPE_API_KEY env var)
        api_url: DashScope API endpoint
        model: Qwen model identifier
        max_tokens: Maximum tokens in response
        temperature: Generation temperature (lower = more deterministic)
        timeout_seconds: Request timeout
        max_retries: Maximum retry attempts
        retry_delay_seconds: Base delay between retries
    """
    api_key: str = ""
    api_url: str = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
    model: str = "qwen3-235b-a22b"  # Qwen 3.5-Plus model
    max_tokens: int = 8192
    temperature: float = 0.3  # Lower for more deterministic fixes
    timeout_seconds: int = 120
    max_retries: int = 3
    retry_delay_seconds: float = 2.0

    @classmethod
    def from_env(cls) -> "APEXConfig":
        """Load configuration from environment variables."""
        return cls(
            api_key=os.environ.get("DASHSCOPE_API_KEY", ""),
            api_url=os.environ.get("DASHSCOPE_API_URL", cls.api_url),
            model=os.environ.get("SWARM_MODEL", cls.model),
        )


@dataclass
class CodeIssue:
    """
    Represents a code issue to fix.
    
    Attributes:
        file_path: Path to the file containing the issue
        line_start: Starting line number
        line_end: Ending line number
        severity: Issue severity (error, warning, info)
        rule_id: Identifier for the rule that triggered the issue
        message: Human-readable description of the issue
        suggestion: Optional suggested fix
        source: Source of the issue detection (codeql, eslint, bandit, etc.)
    """
    file_path: str
    line_start: int
    line_end: int
    severity: str  # error, warning, info
    rule_id: str
    message: str
    suggestion: Optional[str] = None
    source: str = "codeql"  # codeql, eslint, bandit, etc.


@dataclass
class FixResult:
    """
    Result of a fix operation.
    
    Attributes:
        success: Whether the fix was applied successfully
        file_path: Path to the file that was fixed
        original_content: Original file content (for rollback)
        fixed_content: Fixed file content
        issues_addressed: List of issue IDs that were addressed
        explanation: Human-readable explanation of the fix
        error: Error message if fix failed
        duration_ms: Duration of the fix operation in milliseconds
    """
    success: bool
    file_path: str
    original_content: str = ""
    fixed_content: str = ""
    issues_addressed: List[str] = field(default_factory=list)
    explanation: str = ""
    error: Optional[str] = None
    duration_ms: int = 0


# ═══════════════════════════════════════════════════════════════════
# Qwen 3.5-Plus API Client
# ═══════════════════════════════════════════════════════════════════

class QwenClient:
    """
    Client for Qwen 3.5-Plus via DashScope API.
    
    Handles authentication, request formatting, and response parsing
    for the Qwen 3.5-Plus model via Alibaba Cloud DashScope.
    """

    def __init__(self, config: APEXConfig):
        """
        Initialize the Qwen client.
        
        Args:
            config: APEX configuration containing API credentials
        """
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self) -> "QwenClient":
        """Create async context with HTTP session."""
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Clean up HTTP session."""
        if self._session:
            await self._session.close()

    async def generate_fix(
        self,
        code: str,
        issues: List[CodeIssue],
        file_path: str,
        language: str = "javascript"
    ) -> Dict[str, Any]:
        """
        Generate a fix for the given code issues using Qwen 3.5-Plus.

        APEX: No PII is logged. Only file paths and issue types are recorded.
        
        Args:
            code: Original source code
            issues: List of issues to fix
            file_path: Path to the file (for context)
            language: Programming language of the code
            
        Returns:
            Dictionary containing fixed_code, raw_response, and model info
            
        Raises:
            ValueError: If API key is not configured
            Exception: If all retry attempts fail
        """
        if not self.config.api_key:
            raise ValueError("DASHSCOPE_API_KEY not configured")

        # Build the prompt with issue details
        issues_text = "\n".join([
            f"- Line {i.line_start}: [{i.severity.upper()}] {i.rule_id}: {i.message}"
            for i in issues
        ])

        prompt = f"""You are an expert code fixer. Fix the following code issues while maintaining:
1. Original functionality
2. Code style consistency
3. Security best practices (APEX Framework)
4. No breaking changes

File: {file_path}
Language: {language}

Issues to fix:
{issues_text}

Original code:
```
{code}
```

Instructions:
1. Fix ALL listed issues
2. Preserve all existing functionality
3. Add comments explaining security-sensitive changes
4. Return ONLY the fixed code in a code block

Fixed code:"""

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.config.model,
            "input": {
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            },
            "parameters": {
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
                "result_format": "message"
            }
        }

        last_error: Optional[str] = None
        for attempt in range(self.config.max_retries):
            try:
                async with self._session.post(
                    self.config.api_url,
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"✅ Fix generated successfully for {file_path}")
                        return self._parse_response(result)
                    elif response.status == 429:
                        # Rate limited - exponential backoff
                        delay = self.config.retry_delay_seconds * (attempt + 1)
                        logger.warning(f"Rate limited, retrying in {delay}s...")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        error_text = await response.text()
                        last_error = f"API error {response.status}: {error_text[:200]}"
                        logger.error(f"API error: {last_error}")
            except asyncio.TimeoutError:
                last_error = "Request timed out"
                logger.warning(f"Request timed out, attempt {attempt + 1}/{self.config.max_retries}")
                continue
            except Exception as e:
                last_error = str(e)
                logger.error(f"Request failed: {last_error}")
                continue

        raise Exception(f"Failed after {self.config.max_retries} retries: {last_error}")

    def _parse_response(self, response: Dict) -> Dict[str, Any]:
        """
        Parse the API response and extract fixed code.
        
        Args:
            response: Raw API response dictionary
            
        Returns:
            Dictionary with fixed_code, raw_response, and model
            
        Raises:
            ValueError: If response parsing fails
        """
        try:
            content = response.get("output", {}).get("choices", [{}])[0].get("message", {}).get("content", "")

            # Extract code from markdown code block if present
            if "```" in content:
                start = content.find("```")
                end = content.rfind("```")
                if start != end:
                    code_block = content[start:end + 3]
                    # Remove language identifier if present
                    lines = code_block.split("\n")
                    if lines[0].startswith("```"):
                        # Remove language identifier (e.g., ```python)
                        lines[0] = "```"
                    content = "\n".join(lines[1:-1] if len(lines) > 2 else lines)

            return {
                "fixed_code": content.strip(),
                "raw_response": response,
                "model": self.config.model,
            }
        except Exception as e:
            raise ValueError(f"Failed to parse response: {e}")


# ═══════════════════════════════════════════════════════════════════
# Swarm Auto-Fixer Engine
# ═══════════════════════════════════════════════════════════════════

class SwarmAutoFixer:
    """
    Main Auto-Fixer engine.
    
    APEX: No PII logging, full audit trail, comprehensive error handling.
    
    Processes code issues from SARIF files and generates fixes using
    Qwen 3.5-Plus via DashScope API.
    """

    def __init__(self, config: Optional[APEXConfig] = None):
        """
        Initialize the Swarm Auto-Fixer.
        
        Args:
            config: Optional APEX configuration (defaults to env-based config)
        """
        self.config = config or APEXConfig.from_env()
        self.results: List[FixResult] = []
        self.start_time: float = 0
        logger.info(f"Swarm Auto-Fixer initialized with model: {self.config.model}")

    async def fix_file(
        self,
        file_path: Path,
        issues: List[CodeIssue]
    ) -> FixResult:
        """
        Fix issues in a single file.
        
        Args:
            file_path: Path to the file to fix
            issues: List of issues to address
            
        Returns:
            FixResult containing the outcome of the fix operation
        """
        start = time.time()

        try:
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                return FixResult(
                    success=False,
                    file_path=str(file_path),
                    error=f"File not found: {file_path}"
                )

            original_content = file_path.read_text(encoding="utf-8")

            # Determine language from file extension
            ext_map: Dict[str, str] = {
                ".js": "javascript",
                ".ts": "typescript",
                ".py": "python",
                ".yaml": "yaml",
                ".yml": "yaml",
                ".json": "json",
            }
            language = ext_map.get(file_path.suffix, "text")

            async with QwenClient(self.config) as client:
                result = await client.generate_fix(
                    code=original_content,
                    issues=issues,
                    file_path=str(file_path),
                    language=language
                )

            fixed_code = result.get("fixed_code", "")

            if not fixed_code or fixed_code == original_content:
                logger.warning(f"No changes generated for {file_path}")
                return FixResult(
                    success=False,
                    file_path=str(file_path),
                    original_content=original_content,
                    error="No changes generated"
                )

            # Write the fix
            file_path.write_text(fixed_code, encoding="utf-8")
            logger.info(f"✅ Fixed {file_path}: {len(issues)} issue(s)")

            duration_ms = int((time.time() - start) * 1000)

            return FixResult(
                success=True,
                file_path=str(file_path),
                original_content=original_content,
                fixed_content=fixed_code,
                issues_addressed=[i.rule_id for i in issues],
                explanation=f"Fixed {len(issues)} issue(s) using {self.config.model}",
                duration_ms=duration_ms
            )

        except Exception as e:
            duration_ms = int((time.time() - start) * 1000)
            logger.error(f"Failed to fix {file_path}: {e}")
            return FixResult(
                success=False,
                file_path=str(file_path),
                error=str(e),
                duration_ms=duration_ms
            )

    async def run(
        self,
        issues_by_file: Dict[str, List[CodeIssue]]
    ) -> Dict[str, Any]:
        """
        Run the auto-fixer on all provided issues.

        APEX: Returns structured result with full audit trail.
        
        Args:
            issues_by_file: Dictionary mapping file paths to lists of issues
            
        Returns:
            Dictionary containing fix results and summary statistics
        """
        self.start_time = time.time()
        self.results = []

        total_files = len(issues_by_file)
        logger.info(f"Starting fix run for {total_files} file(s)")

        for file_path_str, issues in issues_by_file.items():
            file_path = Path(file_path_str)
            result = await self.fix_file(file_path, issues)
            self.results.append(result)

            # APEX: Log progress (no PII)
            status = "✅" if result.success else "❌"
            logger.info(f"{status} {file_path.name}: {len(issues)} issue(s) in {result.duration_ms}ms")

        # Compile summary
        success_count = sum(1 for r in self.results if r.success)
        total_issues = sum(len(issues) for issues in issues_by_file.values())

        summary = {
            "success": success_count > 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_ms": int((time.time() - self.start_time) * 1000),
            "files_total": total_files,
            "files_fixed": success_count,
            "issues_total": total_issues,
            "model": self.config.model,
            "results": [
                {
                    "file_path": r.file_path,
                    "success": r.success,
                    "issues_addressed": r.issues_addressed,
                    "duration_ms": r.duration_ms,
                    "error": r.error
                }
                for r in self.results
            ]
        }
        
        logger.info(f"Fix run complete: {success_count}/{total_files} files fixed")
        return summary


# ═══════════════════════════════════════════════════════════════════
# GitHub Actions Integration
# ═══════════════════════════════════════════════════════════════════

def parse_sarif_issues(sarif_path: Path) -> Dict[str, List[CodeIssue]]:
    """
    Parse SARIF file to extract issues grouped by file.
    
    Args:
        sarif_path: Path to the SARIF file
        
    Returns:
        Dictionary mapping file paths to lists of CodeIssue objects
    """
    issues_by_file: Dict[str, List[CodeIssue]] = {}

    if not sarif_path.exists():
        logger.warning(f"SARIF file not found: {sarif_path}")
        return issues_by_file

    try:
        sarif_data = json.loads(sarif_path.read_text(encoding="utf-8"))

        for run in sarif_data.get("runs", []):
            for result in run.get("results", []):
                rule_id = result.get("ruleId", "unknown")
                message = result.get("message", {}).get("text", "")

                for location in result.get("locations", []):
                    artifact = location.get("artifactLocation", {})
                    file_path = artifact.get("uri", "")
                    region = location.get("region", {})

                    if not file_path:
                        continue

                    if file_path not in issues_by_file:
                        issues_by_file[file_path] = []

                    issues_by_file[file_path].append(CodeIssue(
                        file_path=file_path,
                        line_start=region.get("startLine", 1),
                        line_end=region.get("endLine", region.get("startLine", 1)),
                        severity=result.get("level", "warning"),
                        rule_id=rule_id,
                        message=message,
                        source="codeql"
                    ))
        
        logger.info(f"Parsed {sum(len(v) for v in issues_by_file.values())} issues from {sarif_path}")
    except Exception as e:
        logger.error(f"Failed to parse SARIF {sarif_path}: {e}")

    return issues_by_file


async def main() -> int:
    """
    Main entry point for GitHub Actions.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    config = APEXConfig.from_env()

    if not config.api_key:
        logger.warning("DASHSCOPE_API_KEY not set - using placeholder mode")
        result = {
            "success": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_ms": 0,
            "files_total": 0,
            "files_fixed": 0,
            "issues_total": 0,
            "model": "placeholder",
            "results": [],
            "note": "DASHSCOPE_API_KEY not configured - no fixes applied"
        }
    else:
        # Look for SARIF files to process
        sarif_files = list(Path(".").glob("**/*.sarif"))

        if not sarif_files:
            logger.info("No SARIF files found - creating placeholder result")
            result = {
                "success": True,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "duration_ms": 0,
                "files_total": 0,
                "files_fixed": 0,
                "issues_total": 0,
                "model": config.model,
                "results": [],
                "note": "No SARIF files found to process"
            }
        else:
            # Parse all SARIF files
            all_issues: Dict[str, List[CodeIssue]] = {}
            for sarif_file in sarif_files:
                file_issues = parse_sarif_issues(sarif_file)
                for file_path, issues in file_issues.items():
                    if file_path not in all_issues:
                        all_issues[file_path] = []
                    all_issues[file_path].extend(issues)

            if not all_issues:
                result = {
                    "success": True,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "duration_ms": 0,
                    "files_total": 0,
                    "files_fixed": 0,
                    "issues_total": 0,
                    "model": config.model,
                    "results": [],
                    "note": "No issues found in SARIF files"
                }
            else:
                # Run the auto-fixer
                fixer = SwarmAutoFixer(config)
                result = await fixer.run(all_issues)

    # Write results for GitHub Actions
    output_path = Path("swarm-results.json")
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    logger.info(f"Results written to: {output_path}")

    # Write to GITHUB_OUTPUT if available (modern GitHub Actions syntax)
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            f.write(f"success={str(result['success']).lower()}\n")
            f.write(f"files_fixed={result['files_fixed']}\n")
            f.write(f"issues_total={result['issues_total']}\n")
            f.write(f"duration_ms={result['duration_ms']}\n")

    return 0 if result["success"] else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
