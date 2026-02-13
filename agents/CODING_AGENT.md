# Coding Agent Executor

A lightweight Python CLI for coding assistance with optional local code execution.

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

## Installation

```bash
# No additional installation required - uses Python stdlib
python agents/coding_agent_executor.py --help
```

## Usage

### Interactive Mode
```bash
# Set API key for LLM features
export DASHSCOPE_API_KEY=your_key_here

# Start interactive session
python agents/coding_agent_executor.py -i
```

### Single Message
```bash
python agents/coding_agent_executor.py -m "Write a Python web scraper"
```

### With Code Execution
```bash
# Enable execution (WARNING: not sandboxed!)
python agents/coding_agent_executor.py -m "Calculate pi" --enable-execution

# With custom timeout
python agents/coding_agent_executor.py -m "Long running task" --enable-execution --timeout 60
```

### Using API Key File
```bash
# Safer than passing secrets on CLI
echo "your_api_key" > ~/.secrets/dashscope_key
python agents/coding_agent_executor.py -m "Hello" --api-key-file ~/.secrets/dashscope_key
```

## API Reference

### CodingAgentExecutor

```python
from coding_agent_executor import CodingAgentExecutor, AgentResult

# Initialize
executor = CodingAgentExecutor(
    api_key=None,              # Optional, uses DASHSCOPE_API_KEY env
    enable_code_execution=False,  # Must explicitly enable
    execution_timeout=30       # Seconds before timeout
)

# Respond to message
result: AgentResult = executor.respond("Write a function", execute=False)
print(result.response)

# Execute code directly
if executor.enable_code_execution:
    exec_result = executor.execute_python("print('Hello, World!')")
    print(exec_result.output)
    print(f"Success: {exec_result.success}")
    print(f"Time: {exec_result.execution_time_ms}ms")
```

### AgentResult

| Field | Type | Description |
|-------|------|-------------|
| response | str | The agent's text response |
| executed | bool | Whether code was executed |
| execution_result | CodeExecutionResult \| None | Execution details if code ran |

### CodeExecutionResult

| Field | Type | Description |
|-------|------|-------------|
| success | bool | Whether execution succeeded (exit code 0) |
| output | str | stdout from execution |
| error | str \| None | stderr if any |
| exit_code | int | Process exit code |
| execution_time_ms | float | Execution time in milliseconds |

## Running Examples

```bash
# List available examples
python agents/coding_agent_example.py --help

# Run example 1: Web scraper snippet
python agents/coding_agent_example.py 1

# Run example 3: With code execution
python agents/coding_agent_example.py 3
```

## Testing

```bash
# Run tests
pytest agents/tests/test_coding_agent.py -v

# With coverage
pytest agents/tests/test_coding_agent.py --cov=coding_agent_executor
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│              CodingAgentExecutor                │
├─────────────────────────────────────────────────┤
│ - respond(message, execute) → AgentResult       │
│ - execute_python(code) → CodeExecutionResult    │
│ - _resolve_api_key() → str | None               │
├─────────────────────────────────────────────────┤
│ Configuration:                                  │
│ - enable_code_execution: bool                   │
│ - execution_timeout: int                        │
│ - api_key: str | None                           │
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

## License

Part of Vaal AI Empire - Proprietary © 2025

---

**Built in the Vaal Triangle. Use responsibly.**
