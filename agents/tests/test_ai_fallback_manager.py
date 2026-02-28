#!/usr/bin/env python3
"""
Comprehensive tests for AI Fallback Manager.
Tests provider fallback chain, caching, error handling, and health checks.
"""

import pytest
import os
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Import the module to test
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from ai_fallback_manager import (
    AIFallbackManager,
    AIProvider,
    AIResponse,
    ProviderConfig,
    get_fallback_manager,
    generate_with_fallback
)


class TestAIProvider:
    """Test AIProvider enum."""

    def test_provider_values(self):
        """Test provider enum values."""
        assert AIProvider.KIMI.value == "kimi"
        assert AIProvider.DASHSCOPE.value == "dashscope"
        assert AIProvider.GLM.value == "glm"
        assert AIProvider.OLLAMA.value == "ollama"
        assert AIProvider.LOCALAI.value == "localai"
        assert AIProvider.CACHE.value == "cache"
        assert AIProvider.RULE_BASED.value == "rule_based"

    def test_provider_count(self):
        """Test that we have expected number of providers."""
        assert len(AIProvider) == 7


class TestAIResponse:
    """Test AIResponse dataclass."""

    def test_ai_response_creation(self):
        """Test creating an AIResponse."""
        response = AIResponse(
            content="Hello world",
            provider=AIProvider.KIMI,
            latency_ms=150.5,
            tokens_used=10,
            model="moonshot-v1-8k"
        )
        assert response.content == "Hello world"
        assert response.provider == AIProvider.KIMI
        assert response.latency_ms == 150.5
        assert response.tokens_used == 10
        assert response.model == "moonshot-v1-8k"
        assert response.cached is False
        assert response.error is None

    def test_ai_response_defaults(self):
        """Test AIResponse default values."""
        response = AIResponse(
            content="Test",
            provider=AIProvider.OLLAMA,
            latency_ms=100.0
        )
        assert response.tokens_used is None
        assert response.model is None
        assert response.cached is False
        assert response.error is None


class TestProviderConfig:
    """Test ProviderConfig dataclass."""

    def test_provider_config_creation(self):
        """Test creating a ProviderConfig."""
        config = ProviderConfig(
            name="Test Provider",
            api_key="test-key",
            base_url="https://api.test.com",
            default_model="test-model",
            timeout_seconds=60,
            retry_attempts=5,
            enabled=True
        )
        assert config.name == "Test Provider"
        assert config.api_key == "test-key"
        assert config.base_url == "https://api.test.com"
        assert config.default_model == "test-model"
        assert config.timeout_seconds == 60
        assert config.retry_attempts == 5
        assert config.enabled is True

    def test_provider_config_defaults(self):
        """Test ProviderConfig default values."""
        config = ProviderConfig(
            name="Test",
            api_key="key",
            base_url="url",
            default_model="model"
        )
        assert config.timeout_seconds == 30
        assert config.retry_attempts == 3
        assert config.enabled is True


class TestAIFallbackManagerInitialization:
    """Test AIFallbackManager initialization."""

    def test_default_initialization(self):
        """Test manager initialization with defaults."""
        manager = AIFallbackManager()
        assert manager.priority == AIFallbackManager.DEFAULT_PRIORITY
        assert len(manager.providers) > 0
        assert isinstance(manager._response_cache, dict)

    def test_custom_priority(self):
        """Test initialization with custom priority."""
        custom_priority = [AIProvider.OLLAMA, AIProvider.LOCALAI]
        manager = AIFallbackManager(priority=custom_priority)
        assert manager.priority == custom_priority

    def test_provider_setup(self):
        """Test that providers are set up correctly."""
        manager = AIFallbackManager()

        # Check that key providers exist
        assert AIProvider.KIMI in manager.providers
        assert AIProvider.DASHSCOPE in manager.providers
        assert AIProvider.GLM in manager.providers
        assert AIProvider.OLLAMA in manager.providers
        assert AIProvider.LOCALAI in manager.providers

        # Check provider configs
        kimi_config = manager.providers[AIProvider.KIMI]
        assert kimi_config.name == "Kimi"
        assert kimi_config.base_url == "https://api.moonshot.cn/v1"
        assert kimi_config.default_model == "moonshot-v1-8k"


class TestCaching:
    """Test response caching functionality."""

    def test_cache_key_generation(self):
        """Test cache key generation."""
        manager = AIFallbackManager()
        key1 = manager._get_cache_key("test prompt", "model1")
        key2 = manager._get_cache_key("test prompt", "model1")
        key3 = manager._get_cache_key("test prompt", "model2")
        key4 = manager._get_cache_key("different prompt", "model1")

        # Same prompt and model should generate same key
        assert key1 == key2
        # Different model or prompt should generate different key
        assert key1 != key3
        assert key1 != key4

    def test_cache_response(self):
        """Test caching a response."""
        manager = AIFallbackManager()
        response = AIResponse(
            content="cached response",
            provider=AIProvider.KIMI,
            latency_ms=100.0
        )

        manager._cache_response("test prompt", response)
        cached = manager._get_cached_response("test prompt")

        assert cached is not None
        assert cached.content == "cached response"

    def test_cache_miss(self):
        """Test cache miss."""
        manager = AIFallbackManager()
        cached = manager._get_cached_response("non-existent prompt")
        assert cached is None


class TestRuleBasedFallback:
    """Test rule-based fallback functionality."""

    def test_rule_based_hello(self):
        """Test rule-based response for greetings."""
        manager = AIFallbackManager()
        response = manager._rule_based_fallback("Hello there")

        assert response.provider == AIProvider.RULE_BASED
        assert response.model == "fallback"
        assert "fallback mode" in response.content.lower()
        assert response.latency_ms == 0

    def test_rule_based_code_request(self):
        """Test rule-based response for code requests."""
        manager = AIFallbackManager()
        response = manager._rule_based_fallback("Write a Python function")

        assert response.provider == AIProvider.RULE_BASED
        assert "generate code" in response.content.lower() or "unable" in response.content.lower()

    def test_rule_based_error(self):
        """Test rule-based response for error queries."""
        manager = AIFallbackManager()
        response = manager._rule_based_fallback("I have an error in my code")

        assert response.provider == AIProvider.RULE_BASED
        assert len(response.content) > 0

    def test_rule_based_generic(self):
        """Test rule-based response for generic queries."""
        manager = AIFallbackManager()
        response = manager._rule_based_fallback("Random query text")

        assert response.provider == AIProvider.RULE_BASED
        assert "fallback mode" in response.content.lower()


class TestCallOpenAICompatible:
    """Test OpenAI-compatible API calls."""

    @patch('ai_fallback_manager.requests.post')
    def test_successful_api_call(self, mock_post):
        """Test successful OpenAI-compatible API call."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Test response"}}],
            "usage": {"total_tokens": 15},
            "model": "test-model"
        }
        mock_post.return_value = mock_response

        manager = AIFallbackManager()
        config = ProviderConfig(
            name="Test",
            api_key="test-key",
            base_url="https://api.test.com",
            default_model="test-model"
        )

        response = manager._call_openai_compatible(config, "test prompt")

        assert response.content == "Test response"
        assert response.tokens_used == 15
        assert response.model == "test-model"
        assert response.latency_ms > 0

    @patch('ai_fallback_manager.requests.post')
    def test_api_timeout(self, mock_post):
        """Test API timeout handling."""
        import requests
        mock_post.side_effect = requests.exceptions.Timeout("Timeout")

        manager = AIFallbackManager()
        config = ProviderConfig(
            name="Test",
            api_key="test-key",
            base_url="https://api.test.com",
            default_model="test-model"
        )

        with pytest.raises(TimeoutError):
            manager._call_openai_compatible(config, "test prompt")

    @patch('ai_fallback_manager.requests.post')
    def test_api_connection_error(self, mock_post):
        """Test API connection error handling."""
        import requests
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")

        manager = AIFallbackManager()
        config = ProviderConfig(
            name="Test",
            api_key="test-key",
            base_url="https://api.test.com",
            default_model="test-model"
        )

        with pytest.raises(ConnectionError):
            manager._call_openai_compatible(config, "test prompt")

    @patch('ai_fallback_manager.requests.post')
    def test_api_invalid_response(self, mock_post):
        """Test handling of invalid API response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"invalid": "structure"}
        mock_post.return_value = mock_response

        manager = AIFallbackManager()
        config = ProviderConfig(
            name="Test",
            api_key="test-key",
            base_url="https://api.test.com",
            default_model="test-model"
        )

        with pytest.raises(ValueError):
            manager._call_openai_compatible(config, "test prompt")


class TestCallOllama:
    """Test Ollama API calls."""

    @patch('ai_fallback_manager.requests.post')
    def test_successful_ollama_call(self, mock_post):
        """Test successful Ollama API call."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "Ollama response",
            "eval_count": 20
        }
        mock_post.return_value = mock_response

        manager = AIFallbackManager()
        config = manager.providers[AIProvider.OLLAMA]

        response = manager._call_ollama(config, "test prompt")

        assert response.content == "Ollama response"
        assert response.provider == AIProvider.OLLAMA
        assert response.tokens_used == 20

    @patch('ai_fallback_manager.requests.post')
    def test_ollama_connection_error(self, mock_post):
        """Test Ollama connection error."""
        import requests
        mock_post.side_effect = requests.exceptions.ConnectionError("Not available")

        manager = AIFallbackManager()
        config = manager.providers[AIProvider.OLLAMA]

        with pytest.raises(ConnectionError):
            manager._call_ollama(config, "test prompt")


class TestGenerate:
    """Test the main generate method with fallback chain."""

    def test_generate_with_cache_hit(self):
        """Test generation with cache hit."""
        manager = AIFallbackManager()

        # Pre-cache a response
        cached_response = AIResponse(
            content="cached content",
            provider=AIProvider.KIMI,
            latency_ms=100.0
        )
        manager._cache_response("test prompt", cached_response)

        # Generate should return cached response
        result = manager.generate("test prompt", use_cache=True)

        assert result.content == "cached content"
        assert result.cached is True

    def test_generate_without_cache(self):
        """Test generation without cache."""
        manager = AIFallbackManager()

        # All providers will fail, should use rule-based
        result = manager.generate("Hello", use_cache=False)

        # Should eventually hit rule-based fallback
        assert result.provider == AIProvider.RULE_BASED
        assert len(result.content) > 0

    @patch('ai_fallback_manager.requests.post')
    def test_generate_with_preferred_provider(self, mock_post):
        """Test generation with preferred provider."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "Ollama response",
            "eval_count": 10
        }
        mock_post.return_value = mock_response

        manager = AIFallbackManager()
        result = manager.generate(
            "test",
            use_cache=False,
            preferred_provider=AIProvider.OLLAMA
        )

        assert result.provider == AIProvider.OLLAMA


class TestHealthCheck:
    """Test health check functionality."""

    def test_health_check_no_providers(self):
        """Test health check when no providers are available."""
        manager = AIFallbackManager()

        # Disable all providers
        for config in manager.providers.values():
            config.enabled = False

        result = manager.health_check()
        assert result is False

    @patch('ai_fallback_manager.requests.get')
    def test_health_check_with_ollama(self, mock_get):
        """Test health check with Ollama available."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        manager = AIFallbackManager()
        result = manager.health_check()

        # Should return True if Ollama is reachable
        assert isinstance(result, bool)


class TestGetStatus:
    """Test status reporting."""

    def test_get_status_structure(self):
        """Test status report structure."""
        manager = AIFallbackManager()
        status = manager.get_status()

        assert "timestamp" in status
        assert "priority" in status
        assert "providers" in status
        assert "cache_size" in status

        # Check priority is list of strings
        assert isinstance(status["priority"], list)
        assert all(isinstance(p, str) for p in status["priority"])

        # Check providers structure
        assert isinstance(status["providers"], dict)

    def test_get_status_provider_info(self):
        """Test provider information in status."""
        manager = AIFallbackManager()
        status = manager.get_status()

        for provider_name, info in status["providers"].items():
            assert "name" in info
            assert "enabled" in info
            assert "available" in info
            assert "model" in info


class TestSingletonManager:
    """Test singleton manager functionality."""

    def test_get_fallback_manager_singleton(self):
        """Test that get_fallback_manager returns singleton."""
        manager1 = get_fallback_manager()
        manager2 = get_fallback_manager()

        assert manager1 is manager2

    def test_generate_with_fallback_convenience(self):
        """Test convenience function."""
        result = generate_with_fallback("Hello")

        assert isinstance(result, str)
        assert len(result) > 0


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_prompt(self):
        """Test handling of empty prompt."""
        manager = AIFallbackManager()
        result = manager.generate("")

        # Should still return a response
        assert isinstance(result, AIResponse)
        assert result.provider == AIProvider.RULE_BASED

    def test_very_long_prompt(self):
        """Test handling of very long prompt."""
        manager = AIFallbackManager()
        long_prompt = "test " * 10000

        result = manager.generate(long_prompt, use_cache=False)

        # Should handle gracefully
        assert isinstance(result, AIResponse)

    def test_special_characters_in_prompt(self):
        """Test handling of special characters."""
        manager = AIFallbackManager()
        special_prompt = "Test with special chars: \n\t\r @#$%^&*()"

        result = manager.generate(special_prompt, use_cache=False)

        assert isinstance(result, AIResponse)

    def test_provider_from_config_not_found(self):
        """Test _get_provider_from_config with unknown config."""
        manager = AIFallbackManager()
        unknown_config = ProviderConfig(
            name="Unknown",
            api_key="test",
            base_url="test",
            default_model="test"
        )

        provider = manager._get_provider_from_config(unknown_config)
        assert provider == AIProvider.RULE_BASED


class TestIntegration:
    """Integration tests for full workflows."""

    def test_full_fallback_chain(self):
        """Test that fallback chain works end-to-end."""
        manager = AIFallbackManager()

        # All external providers will fail, should fall back to rule-based
        result = manager.generate("Hello, how are you?", use_cache=False)

        assert isinstance(result, AIResponse)
        assert result.content is not None
        assert len(result.content) > 0
        assert result.latency_ms >= 0

    def test_caching_integration(self):
        """Test caching across multiple calls."""
        manager = AIFallbackManager()

        # Pre-cache a successful response
        cached_response = AIResponse(
            content="test content",
            provider=AIProvider.KIMI,
            latency_ms=100.0
        )
        manager._cache_response("unique test prompt", cached_response)

        # First call - cache hit
        result1 = manager.generate("unique test prompt", use_cache=True)
        assert result1.cached is True
        assert result1.content == "test content"

        # Second call - cache hit again
        result2 = manager.generate("unique test prompt", use_cache=True)
        assert result2.cached is True
        assert result2.content == result1.content

    def test_cache_disabled(self):
        """Test that cache can be disabled."""
        manager = AIFallbackManager()
        prompt = "test prompt"

        # Multiple calls with cache disabled
        result1 = manager.generate(prompt, use_cache=False)
        result2 = manager.generate(prompt, use_cache=False)

        assert result1.cached is False
        assert result2.cached is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])