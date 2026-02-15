#!/usr/bin/env python3
"""Simple coding-agent style CLI with optional code execution."""

from __future__ import annotations

import argparse
import math
import os
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class AgentResult:
    response: str
    executed: bool = False


class CodingAgentExecutor:
    """A lightweight local coding assistant for demos and examples."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = self._resolve_api_key(api_key)

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
        return textwrap.dedent("""\
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
            """).strip()

    def _execute_known_task(self, message: str) -> str:
        normalized = message.lower().strip()
        if "calculate pi" in normalized:
            return f"Calculated π = {math.pi}"
        return "No known executable task detected."

    def respond(self, message: str, execute: bool = False) -> AgentResult:
        if "web scraper" in message.lower():
            base_response = self._build_scraper_snippet()
        else:
            base_response = f"I received your request: {message}"

        if not self.has_api_key:
            base_response = (
                "[Note] DASHSCOPE_API_KEY is not set; running in local fallback mode.\n\n"
                f"{base_response}"
            )

        if execute:
            execution_output = self._execute_known_task(message)
            combined = f"{base_response}\n\nExecution Result:\n{execution_output}"
            return AgentResult(response=combined, executed=True)

        return AgentResult(response=base_response, executed=False)


def run_interactive(executor: CodingAgentExecutor, execute: bool = False) -> None:
    print("Coding Agent interactive mode. Type 'exit' to quit.")
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
    parser = argparse.ArgumentParser(description="Run the coding agent executor.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-i", "--interactive", action="store_true", help="Start interactive mode"
    )
    group.add_argument("-m", "--message", type=str, help="Send a single message")
    parser.add_argument(
        "-e", "--execute", action="store_true", help="Enable local task execution"
    )
    parser.add_argument(
        "--api-key-file",
        type=str,
        default=None,
        help="Path to file containing API key (safer than passing secrets on CLI)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    executor = CodingAgentExecutor(api_key=load_api_key_from_file(args.api_key_file))

    if args.interactive:
        run_interactive(executor, execute=args.execute)
        return

    result = executor.respond(args.message, execute=args.execute)
    print(result.response)


if __name__ == "__main__":
    main()
