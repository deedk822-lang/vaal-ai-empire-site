#!/usr/bin/env python3
"""Runnable examples for coding_agent_executor.py."""

from __future__ import annotations

import argparse

from coding_agent_executor import CodingAgentExecutor

EXAMPLES = {
    1: ("Generate scraper snippet", "Write a Python web scraper", False),
    2: ("Simple message", "Create a function to add two numbers", False),
    3: ("Message + code execution", "Calculate pi", True),
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run coding agent executor examples")
    parser.add_argument(
        "example", type=int, choices=EXAMPLES.keys(), help="Example number to run"
    )
    args = parser.parse_args()

    title, message, execute = EXAMPLES[args.example]
    executor = CodingAgentExecutor()

    print(f"Example {args.example}: {title}")
    print(f"Prompt: {message}")
    print("-" * 40)
    result = executor.respond(message, execute=execute)
    print(result.response)


if __name__ == "__main__":
    main()
