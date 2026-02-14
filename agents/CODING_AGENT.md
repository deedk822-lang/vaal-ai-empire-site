# 🤖 Vaal AI Empire - Coding Agent Executor

A powerful coding assistant powered by **Qwen3-Coder-Plus** via DashScope API.

## ⚠️ Security Warning

**This module provides TIME-LIMITED code execution, NOT a secure sandbox.**

Code execution via `execute_python()` has the following security characteristics:

| Protection | Status |
|------------|--------|
| Filesystem isolation | ❌ None |
| Network restriction | ❌ None |
| Privilege drop | ❌ None |
| seccomp/AppArmor | ❌ None |
| Timeout guard | ✅ Yes (configurable) |

### What This Means

When `execute_python()` runs code:
- It can read/write any files accessible to your user account
- It can make network requests to any address
- It can spawn child processes
- It has access to all environment variables
- It runs with the same permissions as the parent process

### Safe Use Cases

✅ Local development and testing  
✅ Trusted demo environments  
✅ Code you have manually reviewed  
✅ Controlled sandbox environments (Docker, VMs)

### Unsafe Use Cases

❌ Production systems with untrusted input  
❌ Directly executing LLM-generated code  
❌ Multi-tenant environments  
❌ Systems with sensitive data access

## Recommendations for Secure Execution

For production environments, consider these alternatives:

### 1. Container Isolation (Docker/Podman)
```bash
# Run with dropped capabilities and resource limits
docker run --rm \
  --cap-drop=ALL \
  --network=none \
  --memory="128m" \
  --cpus="0.5" \
  -v /tmp/code:/code:ro \
  python:3.11-slim python /code/script.py
```

### 2. Process Sandboxing (nsjail)
```bash
nsjail --mode=o \
  --time_limit=30 \
  --cgroup_pids_max=10 \
  --rlimit_as=128 \
  --disable_clone_newnet \
  -- /usr/bin/python3 /tmp/script.py
```

### 3. Bubblewrap
```bash
bwrap --ro-bind /usr /usr \
  --ro-bind /lib /lib \
  --ro-bind /lib64 /lib64 \
  --tmpfs /tmp \
  --unshare-net \
  --die-with-parent \
  /usr/bin/python3 script.py
```

### 4. seccomp/AppArmor
Apply Linux security modules to restrict system calls and file access.

### 5. Dedicated Services
- [Judge0](https://judge0.com/) - Open-source code execution system
- [Piston](https://github.com/engineer-man/piston) - Code execution engine
- [CodeBox](https://github.com/judge0/codebox) - Lightweight code executor

---

## Features

- 🚀 **Streaming Responses** - Real-time code generation
- 🐍 **Code Execution** - Run Python code with timeout protection (NOT sandboxed)
- 💬 **Conversation Memory** - Maintains context across messages
- 📊 **Usage Statistics** - Track API usage and tokens
- 🔧 **Customizable** - Configure temperature, system prompts, and more

---

## Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

## Quick Start

### 1. Set API Key

```bash
export DASHSCOPE_API_KEY=your_api_key_here
```

Get your API key from: https://dashscope.aliyun.com/

### 2. Run Interactive Session

```bash
python agents/coding_agent_executor.py -i
```

Or send a single message:

```bash
python agents/coding_agent_executor.py -m "Write a Python function to sort a list"
```

---

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

---

## API Reference

### `CodingAgentExecutor`

Main class for the coding agent.

#### Constructor Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | str | `DASHSCOPE_API_KEY` | DashScope API key |
| `api_key_file` | str | None | Path to file containing API key (safer) |
| `base_url` | str | DashScope URL | API base URL |
| `model` | str | `qwen3-coder-plus` | Model name |
| `system_prompt` | str | Default prompt | System instructions |
| `temperature` | float | 0.7 | Sampling temperature (0-2) |
| `top_p` | float | 0.8 | Nucleus sampling |
| `max_tokens` | int | None | Max tokens to generate |
| `enable_code_execution` | bool | True | Allow code execution (NOT sandboxed) |
| `execution_timeout` | int | 30 | Code timeout in seconds |
| `fallback_mode` | bool | False | Run in local mode when no API key |

#### Methods

##### `chat(message, stream=True, execute_code=False, on_chunk=None)`

Send a message to the agent.

**Returns:** `AgentResponse`

- `content` - Response text
- `code_blocks` - Extracted code blocks
- `execution_result` - Code execution result (if enabled)

##### `execute_python(code, timeout=None)`

Execute Python code with timeout protection.

**⚠️ SECURITY WARNING:** This is NOT a secure sandbox. See above for details.

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

---

## Interactive Commands

When in interactive mode:

| Command | Description |
|---------|-------------|
| `/exit` | End session |
| `/clear` | Clear conversation history |
| `/run` | Execute last Python code |
| `/stats` | Show usage statistics |

---

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

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DASHSCOPE_API_KEY` | Yes* | Your DashScope API key (*or use api_key parameter) |

---

## Model Information

**Qwen3-Coder-Plus** is a powerful code generation model optimized for:
- Code generation and completion
- Code review and debugging
- Refactoring and optimization
- Multi-language support

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│              CodingAgentExecutor                │
├─────────────────────────────────────────────────┤
│ - chat(message, stream, execute_code)           │
│ - execute_python(code, timeout)                 │
│ - clear_history()                               │
│ - get_stats()                                   │
├─────────────────────────────────────────────────┤
│ Configuration:                                  │
│ - enable_code_execution: bool                   │
│ - execution_timeout: int                        │
│ - temperature, top_p, max_tokens                │
└─────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────┐
│          subprocess.run([sys.executable, ...])  │
│                                                 │
│  ⚠️ NO SANDBOX - Full user permissions         │
│  - No filesystem isolation                      │
│  - No network restrictions                      │
│  - No privilege drop                            │
│  - Only timeout guard                           │
└─────────────────────────────────────────────────┘
```

---

## License

© 2025 Vaal AI Empire - Proprietary

---

**Built in the Vaal Triangle. Use responsibly.**
