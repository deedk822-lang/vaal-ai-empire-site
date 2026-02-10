# 🤖 Vaal AI Empire - Coding Agent Executor

A powerful coding assistant powered by **Qwen3-Coder-Plus** via DashScope API.

## Features

- 🚀 **Streaming Responses** - Real-time code generation
- 🐍 **Code Execution** - Run Python code safely in sandboxed environment
- 💬 **Conversation Memory** - Maintains context across messages
- 📊 **Usage Statistics** - Track API usage and tokens
- 🔧 **Customizable** - Configure temperature, system prompts, and more

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set API Key

```bash
export DASHSCOPE_API_KEY=your_api_key_here
```

Get your API key from: https://dashscope.aliyun.com/

### 3. Run Interactive Session

```bash
python agents/coding_agent_executor.py -i
```

Or send a single message:

```bash
python agents/coding_agent_executor.py -m "Write a Python function to sort a list"
```

## Usage Examples

### Basic Chat

```python
from agents.coding_agent_executor import create_agent

agent = create_agent()
response = agent.chat("Write a Python function to calculate factorial", stream=True)
```

### With Code Execution

```python
response = agent.chat(
    "Write a script to calculate pi using Monte Carlo method",
    stream=True,
    execute_code=True
)

if response.execution_result:
    print(response.execution_result.stdout)
```

### Non-Streaming

```python
response = agent.chat("Explain Python generators", stream=False)
print(response.content)
```

### Custom Configuration

```python
agent = create_agent(
    temperature=0.5,  # More deterministic
    top_p=0.9,
    system_prompt="You are a security-focused code reviewer...",
    enable_code_execution=True,
    execution_timeout=60
)
```

## API Reference

### `CodingAgentExecutor`

Main class for the coding agent.

#### Constructor Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | str | `DASHSCOPE_API_KEY` | DashScope API key |
| `base_url` | str | DashScope URL | API base URL |
| `model` | str | `qwen3-coder-plus` | Model name |
| `system_prompt` | str | Default prompt | System instructions |
| `temperature` | float | 0.7 | Sampling temperature (0-2) |
| `top_p` | float | 0.8 | Nucleus sampling |
| `max_tokens` | int | None | Max tokens to generate |
| `enable_code_execution` | bool | True | Allow code execution |
| `execution_timeout` | int | 30 | Code timeout in seconds |

#### Methods

##### `chat(message, stream=True, execute_code=False, on_chunk=None)`

Send a message to the agent.

**Returns:** `AgentResponse`

- `content` - Response text
- `code_blocks` - Extracted code blocks
- `execution_result` - Code execution result (if enabled)

##### `execute_python(code, timeout=None)`

Execute Python code safely.

**Returns:** `CodeExecutionResult`

- `success` - Whether execution succeeded
- `stdout` - Standard output
- `stderr` - Standard error
- `exit_code` - Process exit code
- `execution_time_ms` - Execution time

##### `clear_history()`

Clear conversation history.

##### `get_stats()`

Get usage statistics.

##### `interactive_session()`

Start interactive CLI session.

## Interactive Commands

When in interactive mode:

| Command | Description |
|---------|-------------|
| `/exit` | End session |
| `/clear` | Clear conversation history |
| `/run` | Execute last Python code |
| `/stats` | Show usage statistics |

## Examples

Run examples with:

```bash
python agents/coding_agent_example.py <number>

# Examples:
python agents/coding_agent_example.py 1  # Basic chat
python agents/coding_agent_example.py 3  # Code execution
python agents/coding_agent_example.py 9  # Interactive session
python agents/coding_agent_example.py all  # Run all
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DASHSCOPE_API_KEY` | Yes | Your DashScope API key |

## Model Information

**Qwen3-Coder-Plus** is a powerful code generation model optimized for:
- Code generation and completion
- Code review and debugging
- Refactoring and optimization
- Multi-language support

## Safety

Code execution runs in a subprocess with:
- Timeout protection (default 30s)
- Temporary file isolation
- No network access restrictions (use carefully)
- Automatic cleanup

## License

© 2025 Vaal AI Empire - Proprietary
