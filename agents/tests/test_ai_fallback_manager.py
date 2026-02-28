import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from datetime import datetime, timedelta
import types

# Provide a minimal requests stub so tests run without external dependency install
if "requests" not in sys.modules:
    requests_stub = types.ModuleType("requests")

    class _RequestException(Exception):
        pass

    class _Timeout(_RequestException):
        pass

    class _ConnectionError(_RequestException):
        pass

    requests_stub.exceptions = types.SimpleNamespace(
        Timeout=_Timeout,
        RequestException=_RequestException,
        ConnectionError=_ConnectionError,
    )
    requests_stub.post = lambda *args, **kwargs: None
    requests_stub.get = lambda *args, **kwargs: None
    sys.modules["requests"] = requests_stub

from unittest.mock import Mock, patch

from agents.lib.ai_fallback_manager import (
    AIProvider,
    AIResponse,
    AIFallbackManager,
    CacheEntry,
)


@patch("agents.lib.ai_fallback_manager.requests.post")
def test_generate_uses_ollama_fallback(mock_post):
    manager = AIFallbackManager(priority=[AIProvider.OLLAMA])
    mock_resp = Mock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"response": "hello from ollama", "eval_count": 12}
    mock_post.return_value = mock_resp

    response = manager.generate("hello")

    assert response.provider == AIProvider.OLLAMA
    assert response.content == "hello from ollama"
    assert response.tokens_used == 12


def test_cache_hit_returns_cached_provider():
    manager = AIFallbackManager(priority=[AIProvider.OLLAMA])
    prompt = "cached prompt"
    original = AIResponse(content="cached content", provider=AIProvider.OLLAMA, latency_ms=123)
    key = manager._get_cache_key(prompt)
    manager._response_cache[key] = CacheEntry(response=original, stored_at=datetime.utcnow())

    cached = manager.generate(prompt)

    assert cached.provider == AIProvider.CACHE
    assert cached.cached is True
    assert cached.content == "cached content"


def test_cache_expiry_removes_old_entry():
    manager = AIFallbackManager(priority=[])
    prompt = "old prompt"
    key = manager._get_cache_key(prompt)
    manager._response_cache[key] = CacheEntry(
        response=AIResponse(content="old", provider=AIProvider.OLLAMA, latency_ms=10),
        stored_at=datetime.utcnow() - timedelta(hours=2),
    )

    assert manager._get_cached_response(prompt) is None
    assert key not in manager._response_cache


def test_rule_based_fallback_when_all_providers_fail():
    manager = AIFallbackManager(priority=[AIProvider.OLLAMA, AIProvider.LOCALAI])

    with patch.object(manager, "_call_ollama", side_effect=RuntimeError("down")), patch.object(
        manager, "_call_openai_compatible", side_effect=RuntimeError("down")
    ):
        response = manager.generate("Please help with code")

    assert response.provider == AIProvider.RULE_BASED
    assert "unable to generate code" in response.content.lower()
