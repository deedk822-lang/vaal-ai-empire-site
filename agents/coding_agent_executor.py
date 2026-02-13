#!/usr/bin/env python3
"""
Coding Agent Executor - Local Code Execution for AI Assistants

SECURITY WARNING: This module provides TIME-LIMITED code execution, NOT a secure sandbox.
Code is executed directly via subprocess with only a timeout guard. There is:
- NO filesystem isolation
- NO network restriction
- NO privilege drop/seccomp/AppArmor

This is suitable for trusted environments and demo purposes only.
For production use with untrusted code, consider:
- Running inside a container (Docker, Podman)
- Using nsjail or bubblewrap for process isolation
- Applying seccomp/AppArmor profiles
- Using a dedicated code execution service (e.g., Judge0, Piston)
"""

from __future__ import annotations

import argparse
import asyncio
import math
import os
import subprocess
import sys
import tempfile
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class AgentResponse:
    """Response from the coding agent."""
    content: str
    role: str = "assistant"
    metadata: dict = field(default_factory=dict)


@dataclass
class CodeExecutionResult:
    """Result of local code execution.
    
    WARNING: This execution is NOT sandboxed. Code runs with the same
    permissions as the parent process. Only use with trusted input.
    """
    success: bool
    output: str
    error: Optional[str] = None
    exit_code: int = 0
    execution_time_ms: float = 0.0


@dataclass
class AgentResult:
    """Result from the coding agent including optional execution."""
    response: str
    executed: bool = False
    execution_result: Optional[CodeExecutionResult] = None


class CodingAgentExecutor:
    """
    A lightweight local coding assistant for demos and examples.
    
    This executor provides optional local Python code execution with the
    following characteristics:
    
    ## Execution Model
    - Code runs via subprocess using the current Python interpreter
    - A timeout guard prevents infinite loops (configurable)
    - Output is captured from stdout/stderr
    
    ## Security Limitations (IMPORTANT)
    This is NOT a secure sandbox. The following protections are NOT in place:
    - **Filesystem isolation**: Code can read/write any files accessible to the user
    - **Network isolation**: Code can make network requests
    - **Process isolation**: Code can spawn child processes
    - **Privilege restrictions**: Code runs with the user's permissions
    
    ## Recommendations for Secure Execution
    For production environments with untrusted code, consider:
    1. **Container isolation**: Run inside Docker/Podman with resource limits
    2. **Process sandboxing**: Use nsjail, bubblewrap, or firejail
    3. **Kernel-level security**: Apply seccomp filters or AppArmor profiles
    4. **Dedicated services**: Use Judge0, Piston, or similar execution services
    
    ## Configuration
    - `api_key`: API key for LLM services (optional, can use DASHSCOPE_API_KEY env)
    - `enable_code_execution`: Whether to allow local code execution (default: False)
    - `execution_timeout`: Maximum seconds for code execution (default: 30)
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        enable_code_execution: bool = False,
        execution_timeout: int = 30
    ) -> None:
        self.api_key = self._resolve_api_key(api_key)
        self.enable_code_execution = enable_code_execution
        self.execution_timeout = execution_timeout

    @staticmethod
    def _resolve_api_key(api_key: Optional[str]) -> Optional[str]:
        """Resolve API key from explicit value first, then DASHSCOPE_API_KEY."""
        if api_key and api_key.strip():
            return api_key.strip()

        env_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
        return env_key or None

    @property
    def has_api_key(self) -> bool:
        return bool(self.api_key)

    def _build_scraper_snippet(self) -> str:
        return textwrap.dedent(
            """\
            Here's a Python web scraper starter using `requests` + `BeautifulSoup`:

            ```python
            import requests
            from bs4 import BeautifulSoup

            url = "https://example.com"
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            titles = [h2.get_text(strip=True) for h2 in soup.select("h2")]

            for idx, title in enumerate(titles, start=1):
                print(f"{idx}. {title}")
            ```

            Tip: Respect robots.txt and website terms before scraping.
            """
        ).strip()

    def _execute_known_task(self, message: str) -> str:
        normalized = message.lower().strip()
        if "calculate pi" in normalized:
            return f"Calculated π = {math.pi}"
        return "No known executable task detected."

    def execute_python(
        self,
        code: str,
        timeout: Optional[int] = None
    ) -> CodeExecutionResult:
        """
        Execute Python code locally via subprocess.
        
        ⚠️ SECURITY WARNING ⚠️
        
        This method does NOT provide a secure sandbox. The code will execute
        with the same permissions and access as this Python process, including:
        - Full filesystem access (read/write)
        - Network access (no firewall)
        - Ability to spawn subprocesses
        - Access to environment variables
        
        This is NOT suitable for executing untrusted or LLM-generated code
        in production environments. Use only for:
        - Local development and testing
        - Trusted demo environments
        - Code you have manually reviewed
        
        For secure execution, consider:
        - Docker containers with dropped capabilities
        - nsjail (https://github.com/google/nsjail)
        - bubblewrap (https://github.com/containers/bubblewrap)
        - seccomp/AppArmor profiles
        - Dedicated code execution services
        
        Args:
            code: Python code to execute
            timeout: Maximum execution time in seconds (default: self.execution_timeout)
            
        Returns:
            CodeExecutionResult with output, status, and timing information
        """
        if not self.enable_code_execution:
            return CodeExecutionResult(
                success=False,
                output="",
                error="Code execution is disabled. Set enable_code_execution=True to allow.",
                exit_code=-1
            )
        
        actual_timeout = timeout or self.execution_timeout
        import time
        start_time = time.monotonic()
        
        # Create a temporary file for the code
        # Note: This file is visible to other processes and persists until deleted
        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.py',
                delete=False,
                encoding='utf-8'
            ) as temp_file:
                temp_file.write(code)
                temp_path = temp_file.name
            
            try:
                # Execute using the current Python interpreter
                # WARNING: No sandboxing - code runs with full user permissions
                result = subprocess.run(
                    [sys.executable, temp_path],
                    capture_output=True,
                    text=True,
                    timeout=actual_timeout,
                    # Note: No sandboxing options are applied here
                    # The subprocess inherits the parent's environment and permissions
                )
                
                execution_time = (time.monotonic() - start_time) * 1000
                
                return CodeExecutionResult(
                    success=result.returncode == 0,
                    output=result.stdout,
                    error=result.stderr if result.stderr else None,
                    exit_code=result.returncode,
                    execution_time_ms=round(execution_time, 2)
                )
                
            except subprocess.TimeoutExpired:
                execution_time = (time.monotonic() - start_time) * 1000
                return CodeExecutionResult(
                    success=False,
                    output="",
                    error=f"Execution timed out after {actual_timeout} seconds",
                    exit_code=-1,
                    execution_time_ms=round(execution_time, 2)
                )
            except Exception as e:
                execution_time = (time.monotonic() - start_time) * 1000
                return CodeExecutionResult(
                    success=False,
                    output="",
                    error=f"Execution failed: {str(e)}",
                    exit_code=-1,
                    execution_time_ms=round(execution_time, 2)
                )
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
                    
        except Exception as e:
            return CodeExecutionResult(
                success=False,
                output="",
                error=f"Failed to create execution environment: {str(e)}",
                exit_code=-1
            )

    def respond(self, message: str, execute: bool = False) -> AgentResult:
        """
        Generate a response to the user message.
        
        Args:
            message: User's input message
            execute: Whether to attempt code execution
            
        Returns:
            AgentResult with response and optional execution result
        """
        if "web scraper" in message.lower():
            base_response = self._build_scraper_snippet()
        else:
            base_response = f"I received your request: {message}"

        if not self.has_api_key:
            base_response = (
                "[Note] DASHSCOPE_API_KEY is not set; running in local fallback mode.\n\n"
                f"{base_response}"
            )

        execution_result = None
        
        if execute and self.enable_code_execution:
            # Try to execute any known tasks
            execution_output = self._execute_known_task(message)
            if execution_output != "No known executable task detected.":
                exec_result = self.execute_python(f'print("{execution_output}")')
                execution_result = exec_result
                combined = f"{base_response}\n\nExecution Result:\n{exec_result.output}"
                if exec_result.error:
                    combined += f"\n\nErrors:\n{exec_result.error}"
                return AgentResult(response=combined, executed=True, execution_result=exec_result)

        if execute:
            execution_output = self._execute_known_task(message)
            combined = f"{base_response}\n\nExecution Result:\n{execution_output}"
            return AgentResult(response=combined, executed=True)

        return AgentResult(response=base_response, executed=False)


def run_interactive(executor: CodingAgentExecutor, execute: bool = False) -> None:
    """Run the agent in interactive mode."""
    print("Coding Agent interactive mode. Type 'exit' to quit.")
    print(f"Code execution: {'enabled' if executor.enable_code_execution else 'disabled'}")
    print()
    
    while True:
        try:
            user_input = input("you> ").strip()
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print("\nInterrupted. Exiting interactive mode.")
            break

        if user_input.lower() in {"exit", "quit"}:
            break

        result = executor.respond(user_input, execute=execute)
        print(f"agent> {result.response}\n")


def load_api_key_from_file(api_key_file: Optional[str]) -> Optional[str]:
    """Load API key from file path if provided."""
    if not api_key_file:
        return None

    key_path = Path(api_key_file).expanduser()
    key = key_path.read_text(encoding="utf-8").strip()
    return key or None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the coding agent executor.",
        epilog=textwrap.dedent("""
            Examples:
              # Interactive mode
              python coding_agent_executor.py -i
              
              # Single message
              python coding_agent_executor.py -m "Write a Python web scraper"
              
              # With code execution enabled
              python coding_agent_executor.py -m "Calculate pi" -e --enable-execution
              
            Note: Code execution is NOT sandboxed. Only use with trusted input.
        """)
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-i", "--interactive", action="store_true", help="Start interactive mode")
    group.add_argument("-m", "--message", type=str, help="Send a single message")
    parser.add_argument("-e", "--execute", action="store_true", help="Enable local task execution")
    parser.add_argument(
        "--enable-execution",
        action="store_true",
        help="Enable Python code execution (WARNING: not sandboxed)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Execution timeout in seconds (default: 30)"
    )
    parser.add_argument(
        "--api-key-file",
        type=str,
        default=None,
        help="Path to file containing API key (safer than passing secrets on CLI)"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    executor = CodingAgentExecutor(
        api_key=load_api_key_from_file(args.api_key_file),
        enable_code_execution=args.enable_execution,
        execution_timeout=args.timeout
    )

    if args.interactive:
        run_interactive(executor, execute=args.execute)
        return

    result = executor.respond(args.message, execute=args.execute)
    print(result.response)
    
    if result.execution_result:
        print(f"\n--- Execution Info ---")
        print(f"Success: {result.execution_result.success}")
        print(f"Exit code: {result.execution_result.exit_code}")
        print(f"Time: {result.execution_result.execution_time_ms}ms")


if __name__ == "__main__":
    main()
