#!/usr/bin/env python3
"""
Vaal AI Empire - Coding Agent Executor Examples

This file demonstrates various ways to use the CodingAgentExecutor.

Usage:
    python coding_agent_example.py <number>
    
    # Run without API key (fallback mode)
    python coding_agent_example.py --fallback 3
"""

from __future__ import annotations

import argparse
import os
import sys
from coding_agent_executor import create_agent, quick_chat, CodingAgentExecutor

# Make sure to set your DASHSCOPE_API_KEY environment variable
# export DASHSCOPE_API_KEY=your_api_key_here


def example_1_basic_chat():
    """Example 1: Basic chat with streaming"""
    print("=" * 60)
    print("Example 1: Basic Chat")
    print("=" * 60)
    
    agent = create_agent()
    
    response = agent.chat(
        "Write a Python function to calculate Fibonacci numbers",
        stream=True
    )
    
    print(f"\n\nCode blocks found: {len(response.code_blocks)}")
    for i, block in enumerate(response.code_blocks):
        print(f"  Block {i+1}: {block['language']}")


def example_2_no_streaming():
    """Example 2: Non-streaming response"""
    print("\n" + "=" * 60)
    print("Example 2: Non-Streaming Response")
    print("=" * 60)
    
    agent = create_agent()
    
    response = agent.chat(
        "Explain Python list comprehensions with 3 examples",
        stream=False
    )
    
    print(response.content)


def example_3_code_execution():
    """Example 3: Chat with automatic code execution"""
    print("\n" + "=" * 60)
    print("Example 3: Code Generation + Execution")
    print("=" * 60)
    
    agent = create_agent()
    
    response = agent.chat(
        "Write a Python script that calculates the first 10 prime numbers",
        stream=False,
        execute_code=True
    )
    
    print(response.content)
    
    if response.execution_result:
        result = response.execution_result
        print(f"\n--- Execution Result ---")
        print(f"Success: {result.success}")
        print(f"Time: {result.execution_time_ms:.2f}ms")
        print(f"Output:\n{result.stdout}")


def example_4_conversation():
    """Example 4: Multi-turn conversation with context"""
    print("\n" + "=" * 60)
    print("Example 4: Conversation Context")
    print("=" * 60)
    
    agent = create_agent()
    
    # First message
    print("\n👤 User: Create a Python class for a Bank Account")
    print("\n🤖 Assistant:")
    agent.chat("Create a Python class for a Bank Account", stream=True)
    
    # Follow-up with context
    print("\n\n👤 User: Now add a method to transfer money between accounts")
    print("\n🤖 Assistant:")
    agent.chat("Now add a method to transfer money between accounts", stream=True)
    
    # Check conversation length
    print(f"\n\nConversation messages: {len(agent.messages)}")


def example_5_custom_system_prompt():
    """Example 5: Custom system prompt"""
    print("\n" + "=" * 60)
    print("Example 5: Custom System Prompt")
    print("=" * 60)
    
    custom_prompt = """You are a Python expert focused on data science.
Always use type hints, docstrings, and include example usage.
Prefer pandas and numpy for data operations."""
    
    agent = create_agent(system_prompt=custom_prompt)
    
    response = agent.chat(
        "Write a function to calculate moving averages",
        stream=False
    )
    
    print(response.content)


def example_6_quick_chat():
    """Example 6: Quick one-off chat"""
    print("\n" + "=" * 60)
    print("Example 6: Quick Chat")
    print("=" * 60)
    
    response = quick_chat(
        "What are Python decorators?"
    )
    
    print(response)


def example_7_with_callback():
    """Example 7: Streaming with custom callback"""
    print("\n" + "=" * 60)
    print("Example 7: Custom Stream Callback")
    print("=" * 60)
    
    agent = create_agent()
    
    # Custom callback that counts tokens
    token_count = [0]
    def on_chunk(chunk: str):
        token_count[0] += 1
        # Custom processing - just print dots instead of content
        print(".", end="", flush=True)
    
    response = agent.chat(
        "Write a Python script to scrape a website using requests and BeautifulSoup",
        stream=True,
        on_chunk=on_chunk
    )
    
    print(f"\n\nReceived approximately {token_count[0]} chunks")
    print(f"Total code blocks: {len(response.code_blocks)}")


def example_8_code_review():
    """Example 8: Code review with the agent"""
    print("\n" + "=" * 60)
    print("Example 8: Code Review")
    print("=" * 60)
    
    code_to_review = """
def calculate_total(items):
    total = 0
    for i in range(len(items)):
        total = total + items[i]['price'] * items[i]['quantity']
    return total
"""
    
    agent = create_agent()
    
    response = agent.chat(
        f"Review this Python code and suggest improvements:\n```python\n{code_to_review}\n```",
        stream=False
    )
    
    print(response.content)


def example_9_interactive():
    """Example 9: Interactive session"""
    print("\n" + "=" * 60)
    print("Example 9: Interactive Session")
    print("=" * 60)
    print("This will start an interactive session.")
    print("Type /exit to quit, /help for commands.")
    print("=" * 60)
    
    agent = create_agent()
    agent.interactive_session()


def example_10_statistics():
    """Example 10: Track usage statistics"""
    print("\n" + "=" * 60)
    print("Example 10: Usage Statistics")
    print("=" * 60)
    
    agent = create_agent()
    
    # Make a few requests
    for i in range(3):
        agent.chat(f"Generate a random number in Python (request {i+1})", stream=False)
    
    # Get stats
    stats = agent.get_stats()
    print("Usage Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


# Simple example runner (from branch version)
EXAMPLES_SIMPLE = {
    1: ("Generate scraper snippet", "Write a Python web scraper", False),
    2: ("Simple message", "Create a function to add two numbers", False),
    3: ("Message + code execution", "Calculate pi", True),
}


def run_simple_example(example_num: int, fallback: bool = False) -> None:
    """Run a simple example by number."""
    if example_num not in EXAMPLES_SIMPLE:
        print(f"❌ Invalid example number: {example_num}")
        print(f"Available: {list(EXAMPLES_SIMPLE.keys())}")
        return
    
    title, message, execute = EXAMPLES_SIMPLE[example_num]
    
    print(f"Example {example_num}: {title}")
    print(f"Prompt: {message}")
    print("-" * 40)
    
    try:
        agent = create_agent(fallback_mode=fallback)
        response = agent.respond(message, execute=execute, stream=False)
        print(response.content)
        
        if response.execution_result:
            print(f"\n--- Execution Result ---")
            print(f"Success: {response.execution_result.success}")
            if response.execution_result.stdout:
                print(f"Output: {response.execution_result.stdout}")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Vaal AI Empire - Coding Agent Executor Examples",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python coding_agent_example.py 3
  python coding_agent_example.py --fallback 3
  python coding_agent_example.py all
        """
    )
    parser.add_argument(
        "example",
        nargs="?",
        default=None,
        help="Example number to run (1-10, or 'all')"
    )
    parser.add_argument(
        "--fallback",
        action="store_true",
        help="Run in fallback mode (no API key required)"
    )
    args = parser.parse_args()
    
    # Check for API key (unless fallback mode)
    if not args.fallback and not os.getenv("DASHSCOPE_API_KEY"):
        print("⚠️  Warning: DASHSCOPE_API_KEY not set!")
        print("Use --fallback to run without API key, or set:")
        print("  export DASHSCOPE_API_KEY=your_key_here")
        print()
    
    # Full examples
    examples = {
        "1": example_1_basic_chat,
        "2": example_2_no_streaming,
        "3": example_3_code_execution,
        "4": example_4_conversation,
        "5": example_5_custom_system_prompt,
        "6": example_6_quick_chat,
        "7": example_7_with_callback,
        "8": example_8_code_review,
        "9": example_9_interactive,
        "10": example_10_statistics,
    }
    
    if args.example:
        if args.example.isdigit() and int(args.example) in [1, 2, 3]:
            # Use simple example runner for 1-3
            run_simple_example(int(args.example), fallback=args.fallback)
        elif args.example in examples:
            # Use full example
            examples[args.example]()
        elif args.example == "all":
            # Run all examples
            print("Vaal AI Empire - Coding Agent Executor Examples")
            print("=" * 60)
            for num, func in examples.items():
                if num != "9":  # Skip interactive
                    print(f"\nRunning Example {num}: {func.__doc__.split(chr(10))[0]}")
                    print("-" * 40)
                    try:
                        func()
                    except Exception as e:
                        print(f"\n❌ Example {num} failed: {e}")
            print("\n✅ All examples completed!")
        else:
            print(f"❌ Invalid example: {args.example}")
            sys.exit(1)
    else:
        # Show usage
        print("Vaal AI Empire - Coding Agent Executor Examples")
        print()
        print("Usage: python coding_agent_example.py <example_number>")
        print()
        print("Simple Examples (1-3):")
        for num, (title, _, _) in EXAMPLES_SIMPLE.items():
            print(f"  {num}. {title}")
        print()
        print("Full Examples:")
        for num, func in examples.items():
            print(f"  {num}. {func.__doc__.split(chr(10))[0]}")
        print()
        print("Options:")
        print("  --fallback    Run without API key (limited functionality)")
        print()
        print("Run all (except interactive):")
        print("  python coding_agent_example.py all")
