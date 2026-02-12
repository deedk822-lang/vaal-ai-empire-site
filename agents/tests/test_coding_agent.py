"""Tests for the coding agent executor."""

import os
from unittest.mock import patch

import pytest

from agents.coding_agent_executor import (
    AgentResponse,
    CodeExecutionResult,
    CodingAgentExecutor,
    create_agent,
)

requires_api_key = pytest.mark.skipif(
    not os.getenv("DASHSCOPE_API_KEY"),
    reason="DASHSCOPE_API_KEY not set",
)


class TestCodingAgentExecutor:
    """Test cases for CodingAgentExecutor."""

    def test_initialization_requires_api_key(self):
        """Test that initialization fails without API key."""
        
        # Clear any existing API key
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="API key is required"):
                CodingAgentExecutor(api_key=None)

    def test_initialization_with_api_key(self):
        """Test successful initialization with API key."""
        
        agent = CodingAgentExecutor(api_key="test-api-key")
        assert agent.api_key == "test-api-key"
        assert agent.model == "qwen3-coder-plus"
        assert len(agent.messages) == 1  # System prompt

    def test_initialization_with_custom_params(self):
        """Test initialization with custom parameters."""
        
        agent = CodingAgentExecutor(
            api_key="test-key",
            model="custom-model",
            temperature=0.5,
            top_p=0.9,
            max_tokens=1000
        )
        
        assert agent.model == "custom-model"
        assert agent.temperature == 0.5
        assert agent.top_p == 0.9
        assert agent.max_tokens == 1000

    def test_clear_history(self):
        """Test clearing conversation history."""
        
        agent = CodingAgentExecutor(api_key="test-key")
        agent.messages.append({"role": "user", "content": "Hello"})
        agent.messages.append({"role": "assistant", "content": "Hi"})
        
        assert len(agent.messages) == 3
        
        agent.clear_history()
        
        assert len(agent.messages) == 1
        assert agent.messages[0]["role"] == "system"

    def test_get_stats_initial(self):
        """Test getting stats with fresh agent."""
        
        agent = CodingAgentExecutor(api_key="test-key")
        stats = agent.get_stats()
        
        assert stats["total_requests"] == 0
        assert stats["total_tokens_used"] == 0
        assert stats["conversation_length"] == 1

    def test_extract_code_blocks(self):
        """Test code block extraction from markdown."""
        
        agent = CodingAgentExecutor(api_key="test-key")
        
        content = """
Here's some code:

```python
def hello():
    print("Hello")
```

And some JavaScript:

```javascript
function greet() {
    console.log("Hi");
}
```
"""
        
        blocks = agent._extract_code_blocks(content)
        
        assert len(blocks) == 2
        assert blocks[0]["language"] == "python"
        assert "def hello():" in blocks[0]["code"]
        assert blocks[1]["language"] == "javascript"
        assert "function greet()" in blocks[1]["code"]

    def test_get_python_code(self):
        """Test extracting Python code from blocks."""
        
        agent = CodingAgentExecutor(api_key="test-key")
        
        blocks = [
            {"language": "bash", "code": "npm install"},
            {"language": "python", "code": "print('hello')"},
            {"language": "json", "code": '{"key": "value"}'},
        ]
        
        python_code = agent._get_python_code(blocks)
        
        assert python_code == "print('hello')"

    def test_get_python_code_none(self):
        """Test extracting Python code when none exists."""
        
        agent = CodingAgentExecutor(api_key="test-key")
        
        blocks = [
            {"language": "javascript", "code": "console.log('hi')"},
        ]
        
        python_code = agent._get_python_code(blocks)
        
        assert python_code is None


class TestCodeExecution:
    """Test cases for code execution."""

    def test_execute_python_success(self):
        """Test successful Python code execution."""
        
        agent = CodingAgentExecutor(api_key="test-key")
        
        code = "print('Hello, World!')"
        result = agent.execute_python(code)
        
        assert result.success is True
        assert result.exit_code == 0
        assert "Hello, World!" in result.stdout
        assert result.stderr == ""

    def test_execute_python_error(self):
        """Test Python code execution with error."""
        
        agent = CodingAgentExecutor(api_key="test-key")
        
        code = "print(undefined_variable)"
        result = agent.execute_python(code)
        
        assert result.success is False
        assert result.exit_code != 0
        assert "NameError" in result.stderr or "undefined" in result.stderr.lower()

    def test_execute_python_timeout(self):
        """Test Python code execution timeout."""
        
        agent = CodingAgentExecutor(api_key="test-key", execution_timeout=1)
        
        code = "import time; time.sleep(10)"
        result = agent.execute_python(code, timeout=1)
        
        assert result.success is False
        assert "timeout" in result.stderr.lower() or result.exit_code == -1

    def test_execute_python_disabled(self):
        """Test code execution when disabled."""
        
        agent = CodingAgentExecutor(api_key="test-key", enable_code_execution=False)
        
        result = agent.execute_python("print('test')")
        
        assert result.success is False
        assert "disabled" in result.stderr.lower()


class TestAgentResponse:
    """Test cases for AgentResponse dataclass."""

    def test_agent_response_creation(self):
        """Test creating an AgentResponse."""
        
        response = AgentResponse(
            content="Test content",
            code_blocks=[{"language": "python", "code": "print('hi')"}]
        )
        
        assert response.content == "Test content"
        assert len(response.code_blocks) == 1
        assert response.role == "assistant"


class TestCodeExecutionResult:
    """Test cases for CodeExecutionResult dataclass."""

    def test_result_creation(self):
        """Test creating a CodeExecutionResult."""
        
        result = CodeExecutionResult(
            success=True,
            stdout="output",
            stderr="",
            exit_code=0,
            execution_time_ms=100.5
        )
        
        assert result.success is True
        assert result.stdout == "output"
        assert result.execution_time_ms == 100.5


class TestHelperFunctions:
    """Test cases for helper functions."""

    def test_create_agent(self):
        """Test create_agent helper function."""
        
        agent = create_agent(api_key="test-key")
        
        assert isinstance(agent, CodingAgentExecutor)
        assert agent.api_key == "test-key"


@requires_api_key
class TestLiveAPI:
    """Live API smoke tests (requires DASHSCOPE_API_KEY)."""

    def test_chat_live_api_smoke(self):
        """Test a minimal non-streaming API call returns content."""
        agent = CodingAgentExecutor(api_key=os.getenv("DASHSCOPE_API_KEY"))
        response = agent.chat("Respond with the word OK", stream=False, execute_code=False)

        assert isinstance(response, AgentResponse)
        assert isinstance(response.content, str)
        assert response.content.strip() != ""
