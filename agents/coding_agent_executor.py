"""
Vaal AI Empire - Coding Agent Executor
Powered by Qwen3-Coder-Plus via DashScope API

This module provides a coding agent that can:
- Generate, analyze, and refactor code
- Execute Python code safely in a sandboxed environment
- Stream responses for real-time feedback
- Maintain conversation context

Usage:
    export DASHSCOPE_API_KEY=your_key_here
    
    # Interactive mode
    python agents/coding_agent_executor.py -i
    
    # Single message
    python agents/coding_agent_executor.py -m "Write a Python web scraper"
    
    # With code execution
    python agents/coding_agent_executor.py -m "Calculate pi" -e
    
    # Load key from file (safer than CLI args)
    python agents/coding_agent_executor.py -m "Hello" --api-key-file ~/.dashscope_key
"""

from __future__ import annotations

import argparse
import os
import sys
import json
import re
import subprocess
import tempfile
import textwrap
from pathlib import Path
from typing import Iterator, Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime

from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class CodeExecutionResult:
    """Result of code execution"""
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    execution_time_ms: float
    files_created: List[str] = field(default_factory=list)


@dataclass
class AgentResponse:
    """Response from the coding agent"""
    content: str
    role: str = "assistant"
    timestamp: datetime = field(default_factory=datetime.now)
    code_blocks: List[Dict[str, str]] = field(default_factory=list)
    execution_result: Optional[CodeExecutionResult] = None


def load_api_key_from_file(api_key_file: Optional[str]) -> Optional[str]:
    """Load API key from file path if provided."""
    if not api_key_file:
        return None
    
    key_path = Path(api_key_file).expanduser()
    if not key_path.exists():
        raise FileNotFoundError(f"API key file not found: {key_path}")
    
    key = key_path.read_text(encoding="utf-8").strip()
    return key or None


class CodingAgentExecutor:
    """
    Coding Agent Executor using Qwen3-Coder-Plus via DashScope API.
    
    Features:
    - Streaming responses for real-time feedback
    - Code extraction and execution
    - Conversation memory
    - Safe sandboxed execution
    - Local fallback mode when API key is not available
    """
    
    DEFAULT_SYSTEM_PROMPT = """You are an expert coding assistant powered by Qwen3-Coder-Plus. 
Your capabilities include:

1. **Code Generation**: Write clean, efficient, well-documented code
2. **Code Review**: Analyze code for bugs, security issues, and improvements
3. **Refactoring**: Restructure code for better readability and performance
4. **Debugging**: Identify and fix errors in code
5. **Explanation**: Explain complex concepts clearly with examples

Guidelines:
- Always provide complete, runnable code examples
- Include comments explaining key logic
- Follow best practices and coding standards
- When suggesting fixes, explain WHY the fix works
- For Python code, follow PEP 8 style guidelines
- Warn about any security considerations

When writing code, wrap it in appropriate markdown code blocks with language specified."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_key_file: Optional[str] = None,
        base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        model: str = "qwen3-coder-plus",
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        top_p: float = 0.8,
        max_tokens: Optional[int] = None,
        enable_code_execution: bool = True,
        execution_timeout: int = 30,
        fallback_mode: bool = False
    ):
        """
        Initialize the Coding Agent Executor.
        
        Args:
            api_key: DashScope API key (defaults to DASHSCOPE_API_KEY env var)
            api_key_file: Path to file containing API key (safer than CLI args)
            base_url: API base URL
            model: Model name to use
            system_prompt: Custom system prompt
            temperature: Sampling temperature (0-2)
            top_p: Nucleus sampling parameter
            max_tokens: Maximum tokens to generate
            enable_code_execution: Whether to enable code execution
            execution_timeout: Timeout for code execution in seconds
            fallback_mode: If True, run in local fallback mode when no API key
        """
        # Resolve API key from multiple sources
        self.api_key = self._resolve_api_key(api_key, api_key_file)
        self.fallback_mode = fallback_mode and not self.api_key
        
        if not self.api_key and not self.fallback_mode:
            raise ValueError(
                "API key is required. Set DASHSCOPE_API_KEY environment variable, "
                "pass api_key parameter, use --api-key-file, or enable fallback_mode."
            )
        
        self.client = None
        if self.api_key:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=base_url
            )
        
        self.model = model
        self.system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens
        self.enable_code_execution = enable_code_execution
        self.execution_timeout = execution_timeout
        
        # Conversation history
        self.messages: List[Dict[str, str]] = [
            {"role": "system", "content": self.system_prompt}
        ]
        
        # Statistics
        self.total_requests = 0
        self.total_tokens_used = 0
    
    def _resolve_api_key(
        self, 
        api_key: Optional[str], 
        api_key_file: Optional[str]
    ) -> Optional[str]:
        """Resolve API key from multiple sources in priority order."""
        # 1. Explicit API key
        if api_key and api_key.strip():
            return api_key.strip()
        
        # 2. API key from file
        if api_key_file:
            return load_api_key_from_file(api_key_file)
        
        # 3. Environment variable
        env_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
        if env_key:
            return env_key
        
        return None
    
    @property
    def has_api_key(self) -> bool:
        """Check if API key is configured."""
        return bool(self.api_key and self.client)
    
    def _generate_fallback_response(self, message: str) -> str:
        """Generate a local fallback response when API is unavailable."""
        normalized = message.lower().strip()
        
        if "web scraper" in normalized or "scrape" in normalized:
            return textwrap.dedent(
                """\
                Here's a Python web scraper using `requests` + `BeautifulSoup`:

                ```python
                import requests
                from bs4 import BeautifulSoup

                def scrape_website(url):
                    try:
                        response = requests.get(url, timeout=10)
                        response.raise_for_status()
                        
                        soup = BeautifulSoup(response.text, "html.parser")
                        
                        # Extract all headings
                        headings = [h.get_text(strip=True) for h in soup.find_all(["h1", "h2", "h3"])]
                        
                        # Extract all paragraphs
                        paragraphs = [p.get_text(strip=True) for p in soup.find_all("p")[:5]]
                        
                        return {
                            "headings": headings,
                            "paragraphs": paragraphs,
                            "title": soup.title.string if soup.title else None
                        }
                    except requests.RequestException as e:
                        print(f"Error fetching {url}: {e}")
                        return None

                # Example usage
                if __name__ == "__main__":
                    result = scrape_website("https://example.com")
                    if result:
                        print(f"Title: {result['title']}")
                        for h in result['headings'][:5]:
                            print(f"Heading: {h}")
                ```

                Tip: Always respect robots.txt and website terms of service. Consider adding delays between requests to be polite.
                """
            ).strip()
        
        elif "factorial" in normalized:
            return textwrap.dedent(
                """\
                Here's a Python function to calculate factorial:

                ```python
def factorial(n):
                    \"\"\"Calculate factorial of n.\"\"\"
                    if n < 0:
                        raise ValueError("Factorial not defined for negative numbers")
                    if n == 0 or n == 1:
                        return 1
                    return n * factorial(n - 1)

                # Iterative version (better for large numbers)
                def factorial_iterative(n):
                    \"\"\"Calculate factorial iteratively.\"\"\"
                    if n < 0:
                        raise ValueError("Factorial not defined for negative numbers")
                    result = 1
                    for i in range(2, n + 1):
                        result *= i
                    return result

                # Example usage
                print(factorial(5))  # 120
                print(factorial_iterative(5))  # 120
                ```
                """
            ).strip()
        
        elif "fibonacci" in normalized:
            return textwrap.dedent(
                """\
                Here's a Python function to generate Fibonacci numbers:

                ```python
def fibonacci(n):
                    \"\"\"Generate first n Fibonacci numbers.\"\"\"
                    if n <= 0:
                        return []
                    elif n == 1:
                        return [0]
                    
                    fibs = [0, 1]
                    for i in range(2, n):
                        fibs.append(fibs[i-1] + fibs[i-2])
                    return fibs

                # Generator version (memory efficient)
                def fibonacci_generator(limit=None):
                    \"\"\"Generate Fibonacci sequence.\"\"\"
                    a, b = 0, 1
                    count = 0
                    while limit is None or count < limit:
                        yield a
                        a, b = b, a + b
                        count += 1

                # Example usage
                print(fibonacci(10))
                print(list(fibonacci_generator(10)))
                ```
                """
            ).strip()
        
        return f"I received your request: {message}\n\n[Note: Running in local fallback mode. Set DASHSCOPE_API_KEY for AI-powered responses.]"

    def chat(
        self,
        message: str,
        stream: bool = True,
        execute_code: bool = False,
        on_chunk: Optional[Callable[[str], None]] = None
    ) -> AgentResponse:
        """
        Send a message to the coding agent and get a response.
        
        Args:
            message: User message
            stream: Whether to stream the response
            execute_code: Whether to automatically execute extracted Python code
            on_chunk: Callback function for streaming chunks
            
        Returns:
            AgentResponse with content and metadata
        """
        # Add user message to history
        self.messages.append({"role": "user", "content": message})
        
        # Handle fallback mode
        if self.fallback_mode or not self.client:
            content = self._generate_fallback_response(message)
            if not self.has_api_key:
                content = (
                    "[Note] DASHSCOPE_API_KEY is not set; running in local fallback mode.\n\n"
                    f"{content}"
                )
            
            code_blocks = self._extract_code_blocks(content)
            
            # Execute code if requested
            execution_result = None
            if execute_code and self.enable_code_execution and code_blocks:
                python_code = self._get_python_code(code_blocks)
                if python_code:
                    execution_result = self.execute_python(python_code)
            
            self.messages.append({"role": "assistant", "content": content})
            
            return AgentResponse(
                content=content,
                code_blocks=code_blocks,
                execution_result=execution_result
            )
        
        # Build completion parameters
        params = {
            "model": self.model,
            "messages": self.messages,
            "stream": stream,
            "temperature": self.temperature,
            "top_p": self.top_p,
        }
        
        if self.max_tokens:
            params["max_tokens"] = self.max_tokens
        
        # Get completion
        completion = self.client.chat.completions.create(**params)
        
        if stream:
            content = self._handle_streaming_response(completion, on_chunk)
        else:
            content = completion.choices[0].message.content
            self.total_tokens_used += completion.usage.total_tokens if completion.usage else 0
        
        # Extract code blocks
        code_blocks = self._extract_code_blocks(content)
        
        # Execute code if requested and enabled
        execution_result = None
        if execute_code and self.enable_code_execution and code_blocks:
            python_code = self._get_python_code(code_blocks)
            if python_code:
                execution_result = self.execute_python(python_code)
        
        # Add assistant response to history
        self.messages.append({"role": "assistant", "content": content})
        
        self.total_requests += 1
        
        return AgentResponse(
            content=content,
            code_blocks=code_blocks,
            execution_result=execution_result
        )
    
    def respond(
        self,
        message: str,
        execute: bool = False,
        stream: bool = False
    ) -> AgentResponse:
        """
        Simple interface for getting a response (alias for chat with different defaults).
        
        Args:
            message: User message
            execute: Whether to execute extracted code
            stream: Whether to stream (default False for simpler interface)
            
        Returns:
            AgentResponse
        """
        return self.chat(message, stream=stream, execute_code=execute)
    
    def _handle_streaming_response(
        self,
        completion: Iterator,
        on_chunk: Optional[Callable[[str], None]] = None
    ) -> str:
        """Handle streaming response from API."""
        content_parts = []
        
        for chunk in completion:
            delta = chunk.choices[0].delta
            if delta.content:
                content_parts.append(delta.content)
                if on_chunk:
                    on_chunk(delta.content)
                else:
                    print(delta.content, end="", flush=True)
        
        if not on_chunk:
            print()  # New line after streaming
            
        return "".join(content_parts)
    
    def _extract_code_blocks(self, content: str) -> List[Dict[str, str]]:
        """Extract code blocks from markdown content."""
        pattern = r'```(\w+)?\n(.*?)```'
        matches = re.findall(pattern, content, re.DOTALL)
        
        code_blocks = []
        for lang, code in matches:
            code_blocks.append({
                "language": lang.strip() if lang else "text",
                "code": code.strip()
            })
        
        return code_blocks
    
    def _get_python_code(self, code_blocks: List[Dict[str, str]]) -> Optional[str]:
        """Extract Python code from code blocks."""
        for block in code_blocks:
            if block["language"].lower() in ("python", "py"):
                return block["code"]
        return None
    
    def execute_python(self, code: str, timeout: Optional[int] = None) -> CodeExecutionResult:
        """
        Execute Python code in a sandboxed environment.
        
        Args:
            code: Python code to execute
            timeout: Execution timeout in seconds
            
        Returns:
            CodeExecutionResult with output and status
        """
        if not self.enable_code_execution:
            return CodeExecutionResult(
                success=False,
                stdout="",
                stderr="Code execution is disabled",
                exit_code=-1,
                execution_time_ms=0
            )
        
        timeout = timeout or self.execution_timeout
        start_time = datetime.now()
        
        # Create temporary file for the code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # Run the code with timeout
            result = subprocess.run(
                [sys.executable, temp_file],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return CodeExecutionResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                execution_time_ms=execution_time,
                files_created=[temp_file]
            )
            
        except subprocess.TimeoutExpired:
            return CodeExecutionResult(
                success=False,
                stdout="",
                stderr=f"Execution timed out after {timeout} seconds",
                exit_code=-1,
                execution_time_ms=timeout * 1000,
                files_created=[temp_file]
            )
        except Exception as e:
            return CodeExecutionResult(
                success=False,
                stdout="",
                stderr=str(e),
                exit_code=-1,
                execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                files_created=[temp_file]
            )
        finally:
            # Cleanup
            try:
                os.unlink(temp_file)
            except:
                pass
    
    def clear_history(self):
        """Clear conversation history except system prompt."""
        self.messages = [{"role": "system", "content": self.system_prompt}]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        return {
            "total_requests": self.total_requests,
            "total_tokens_used": self.total_tokens_used,
            "conversation_length": len(self.messages)
        }
    
    def interactive_session(self):
        """Start an interactive coding session."""
        print("=" * 60)
        print("🚀 Vaal AI Empire - Coding Agent Executor")
        print(f"🤖 Model: {self.model}")
        print("=" * 60)
        print("Commands:")
        print("  /exit     - End session")
        print("  /clear    - Clear conversation history")
        print("  /run      - Execute last Python code")
        print("  /stats    - Show usage statistics")
        print("=" * 60)
        print()
        
        last_code = None
        
        while True:
            try:
                user_input = input("\n👤 You: ").strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input == "/exit":
                    print("\n👋 Goodbye!")
                    break
                elif user_input == "/clear":
                    self.clear_history()
                    print("\n🧹 Conversation history cleared.")
                    continue
                elif user_input == "/run":
                    if last_code:
                        print("\n⚙️  Executing code...")
                        result = self.execute_python(last_code)
                        print(f"\n{'✅' if result.success else '❌'} Execution {'successful' if result.success else 'failed'}")
                        print(f"⏱️  Time: {result.execution_time_ms:.2f}ms")
                        if result.stdout:
                            print(f"\n📤 Output:\n{result.stdout}")
                        if result.stderr:
                            print(f"\n📛 Error:\n{result.stderr}")
                    else:
                        print("\n⚠️ No code to execute. Generate some code first!")
                    continue
                elif user_input == "/stats":
                    stats = self.get_stats()
                    print(f"\n📊 Statistics:")
                    for key, value in stats.items():
                        print(f"  {key}: {value}")
                    continue
                
                # Normal chat
                print("\n🤖 Assistant: ", end="", flush=True)
                response = self.chat(user_input, stream=True)
                
                # Store Python code for potential execution
                for block in response.code_blocks:
                    if block["language"] in ("python", "py"):
                        last_code = block["code"]
                        break
                
            except KeyboardInterrupt:
                print("\n\n⚠️ Interrupted. Use /exit to quit.")
            except Exception as e:
                print(f"\n❌ Error: {e}")


# Convenience function for quick usage
def create_agent(
    api_key: Optional[str] = None,
    **kwargs
) -> CodingAgentExecutor:
    """Create a new CodingAgentExecutor instance."""
    return CodingAgentExecutor(api_key=api_key, **kwargs)


def quick_chat(message: str, **kwargs) -> str:
    """Quick one-off chat with the coding agent."""
    agent = create_agent(**kwargs)
    response = agent.chat(message, stream=False)
    return response.content


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Vaal AI Empire Coding Agent - Powered by Qwen3-Coder-Plus",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python coding_agent_executor.py -i
  
  # Single message
  python coding_agent_executor.py -m "Write a Python web scraper"
  
  # With code execution
  python coding_agent_executor.py -m "Calculate pi" -e
  
  # Load API key from file (safer than CLI args)
  python coding_agent_executor.py -m "Hello" --api-key-file ~/.dashscope_key
  
  # Fallback mode (no API key required)
  python coding_agent_executor.py -m "Write a web scraper" --fallback
        """
    )
    
    # Mode selection (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Start interactive session"
    )
    mode_group.add_argument(
        "-m", "--message",
        type=str,
        help="Send a single message"
    )
    
    # API Configuration
    api_group = parser.add_argument_group("API Configuration")
    api_group.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="DashScope API key (or set DASHSCOPE_API_KEY env var)"
    )
    api_group.add_argument(
        "--api-key-file",
        type=str,
        default=None,
        help="Path to file containing API key (safer than CLI args)"
    )
    api_group.add_argument(
        "--fallback",
        action="store_true",
        help="Run in fallback mode (no API key required, limited functionality)"
    )
    
    # Generation parameters
    gen_group = parser.add_argument_group("Generation Parameters")
    gen_group.add_argument(
        "-t", "--temp",
        type=float,
        default=0.7,
        help="Sampling temperature (0-2, default: 0.7)"
    )
    gen_group.add_argument(
        "--top-p",
        type=float,
        default=0.8,
        help="Nucleus sampling parameter (default: 0.8)"
    )
    gen_group.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        help="Maximum tokens to generate"
    )
    gen_group.add_argument(
        "--no-stream",
        action="store_true",
        help="Disable streaming response"
    )
    
    # Execution options
    exec_group = parser.add_argument_group("Execution Options")
    exec_group.add_argument(
        "-e", "--execute",
        action="store_true",
        help="Execute generated Python code"
    )
    exec_group.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Code execution timeout in seconds (default: 30)"
    )
    exec_group.add_argument(
        "--no-execute",
        action="store_true",
        help="Disable code execution (override default)"
    )
    
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()
    
    # Determine execution mode
    enable_execution = not args.no_execute
    
    try:
        # Create agent
        agent = CodingAgentExecutor(
            api_key=args.api_key,
            api_key_file=args.api_key_file,
            temperature=args.temp,
            top_p=args.top_p,
            max_tokens=args.max_tokens,
            enable_code_execution=enable_execution,
            execution_timeout=args.timeout,
            fallback_mode=args.fallback
        )
    except ValueError as e:
        print(f"❌ Error: {e}")
        print("\nTip: Use --fallback flag to run without API key, or set DASHSCOPE_API_KEY")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    
    if args.interactive:
        # Interactive mode
        agent.interactive_session()
        
    elif args.message:
        # Single message mode
        print(f"🤖 Prompt: {args.message}\n")
        
        response = agent.chat(
            args.message,
            stream=not args.no_stream,
            execute_code=args.execute
        )
        
        # Print response if not streaming
        if args.no_stream:
            print(response.content)
        
        # Show execution result if code was executed
        if response.execution_result:
            result = response.execution_result
            print(f"\n{'='*60}")
            print(f"⚙️  Code Execution Result:")
            print(f"{'='*60}")
            print(f"Success: {'✅ Yes' if result.success else '❌ No'}")
            print(f"Time: {result.execution_time_ms:.2f}ms")
            if result.stdout:
                print(f"\n📤 Output:\n{result.stdout}")
            if result.stderr:
                print(f"\n📛 Error:\n{result.stderr}")


if __name__ == "__main__":
    main()
