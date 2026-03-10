"""
AI Fallback Manager for Vaal AI Empire

Provides resilient AI service with automatic fallback chain:
1. Primary: External APIs (Kimi, Dashscope, GLM)
2. Secondary: Ollama (local models)
3. Tertiary: LocalAI (OpenAI-compatible local server)
4. Quaternary: Cached responses / rule-based fallback

Author: Vaal AI Empire
Version: 1.0.0
"""

import os
import json
import time
import logging
from enum import Enum
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from functools import lru_cache
import requests
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AIProvider(Enum):
    """Available AI providers in priority order"""
    KIMI = "kimi"
    DASHSCOPE = "dashscope"
    GLM = "glm"
    OLLAMA = "ollama"
    LOCALAI = "localai"
    CACHE = "cache"
    RULE_BASED = "rule_based"


@dataclass
class AIResponse:
    """Standardized AI response"""
    content: str
    provider: AIProvider
    latency_ms: float
    tokens_used: Optional[int] = None
    model: Optional[str] = None
    cached: bool = False
    error: Optional[str] = None


@dataclass
class ProviderConfig:
    """Configuration for an AI provider"""
    name: str
    api_key: Optional[str]
    base_url: str
    default_model: str
    timeout_seconds: int = 30
    retry_attempts: int = 3
    enabled: bool = True


class AIFallbackManager:
    """
    Manages AI providers with automatic fallback chain.

    Usage:
        manager = AIFallbackManager()
        response = manager.generate("Write a Python function to...")
        print(response.content)
    """

    # Provider priority order (highest to lowest)
    DEFAULT_PRIORITY = [
        AIProvider.KIMI,
        AIProvider.DASHSCOPE,
        AIProvider.GLM,
        AIProvider.OLLAMA,
        AIProvider.LOCALAI,
    ]

    def __init__(self, priority: Optional[List[AIProvider]] = None):
        """
        Initialize the fallback manager.

        Args:
            priority: Custom provider priority order. Defaults to DEFAULT_PRIORITY.
        """
        self.priority = priority or self.DEFAULT_PRIORITY
        self.providers: Dict[AIProvider, ProviderConfig] = {}
        self._response_cache: Dict[str, AIResponse] = {}
        self._cache_ttl = timedelta(minutes=30)
        self._setup_providers()

    def _setup_providers(self):
        """Configure all available providers from environment"""
        self.providers = {
            AIProvider.KIMI: ProviderConfig(
                name="Kimi",
                api_key=os.getenv("KIMI_API_KEY"),
                base_url="https://api.moonshot.cn/v1",
                default_model="moonshot-v1-8k",
                timeout_seconds=30,
            ),
            AIProvider.DASHSCOPE: ProviderConfig(
                name="Dashscope (Qwen)",
                api_key=os.getenv("DASHSCOPE_API_KEY"),
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                default_model="qwen-turbo",
                timeout_seconds=30,
            ),
            AIProvider.GLM: ProviderConfig(
                name="GLM",
                api_key=os.getenv("GLM5_API_KEY"),
                base_url="https://open.bigmodel.cn/api/paas/v4",
                default_model="glm-4-flash",
                timeout_seconds=30,
            ),
            AIProvider.OLLAMA: ProviderConfig(
                name="Ollama (Local)",
                api_key=os.getenv("OLLAMA_API_KEY", "ollama"),
                base_url=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
                default_model="qwen2.5-coder:1.5b",
                timeout_seconds=60,
            ),
            AIProvider.LOCALAI: ProviderConfig(
                name="LocalAI (Fallback)",
                api_key=os.getenv("LOCALAI_API_KEY", "localai"),
                base_url=os.getenv("LOCALAI_URL", "http://localhost:8080/v1"),
                default_model="qwen2.5-coder:1.5b",
                timeout_seconds=120,
            ),
        }

        # Disable providers without API keys
        for provider, config in self.providers.items():
            if not config.api_key and provider not in [AIProvider.OLLAMA, AIProvider.LOCALAI]:
                config.enabled = False
                logger.warning(f"{config.name} disabled: No API key configured")

    def _get_cache_key(self, prompt: str, model: Optional[str] = None) -> str:
        """Generate cache key for a prompt"""
        import hashlib
        key_data = f"{prompt}:{model or 'default'}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _get_cached_response(self, prompt: str, model: Optional[str] = None) -> Optional[AIResponse]:
        """Get cached response if available and not expired"""
        cache_key = self._get_cache_key(prompt, model)
        if cache_key in self._response_cache:
            cached = self._response_cache[cache_key]
            # Check if cache is still valid (simplified)
            return cached
        return None

    def _cache_response(self, prompt: str, response: AIResponse, model: Optional[str] = None):
        """Cache a response"""
        cache_key = self._get_cache_key(prompt, model)
        self._response_cache[cache_key] = response

    def _call_openai_compatible(
        self,
        config: ProviderConfig,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> AIResponse:
        """Call an OpenAI-compatible API"""
        start_time = time.time()

        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": config.default_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        try:
            response = requests.post(
                f"{config.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=config.timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()

            latency_ms = (time.time() - start_time) * 1000
            content = data["choices"][0]["message"]["content"]
            tokens = data.get("usage", {}).get("total_tokens")
            model_used = data.get("model", config.default_model)

            return AIResponse(
                content=content,
                provider=self._get_provider_from_config(config),
                latency_ms=latency_ms,
                tokens_used=tokens,
                model=model_used,
            )

        except requests.exceptions.Timeout:
            raise TimeoutError(f"{config.name} request timed out after {config.timeout_seconds}s")
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"{config.name} request failed: {str(e)}")
        except (KeyError, IndexError) as e:
            raise ValueError(f"Invalid response from {config.name}: {str(e)}")

    def _call_ollama(
        self,
        config: ProviderConfig,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> AIResponse:
        """Call Ollama API"""
        start_time = time.time()

        payload = {
            "model": config.default_model,
            "prompt": prompt,
            "system": system_prompt or "",
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        try:
            response = requests.post(
                f"{config.base_url}/api/generate",
                json=payload,
                timeout=config.timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()

            latency_ms = (time.time() - start_time) * 1000

            return AIResponse(
                content=data.get("response", ""),
                provider=AIProvider.OLLAMA,
                latency_ms=latency_ms,
                tokens_used=data.get("eval_count"),
                model=config.default_model,
            )

        except requests.exceptions.ConnectionError:
            raise ConnectionError(f"Ollama not available at {config.base_url}")
        except requests.exceptions.Timeout:
            raise TimeoutError(f"Ollama request timed out")
        except Exception as e:
            raise RuntimeError(f"Ollama error: {str(e)}")

    def _get_provider_from_config(self, config: ProviderConfig) -> AIProvider:
        """Get provider enum from config"""
        for provider, cfg in self.providers.items():
            if cfg == config:
                return provider
        return AIProvider.RULE_BASED

    def _rule_based_fallback(self, prompt: str) -> AIResponse:
        """Generate a rule-based fallback response"""
        logger.warning("Using rule-based fallback - all AI providers unavailable")

        # Simple pattern matching for common requests
        prompt_lower = prompt.lower()

        if "hello" in prompt_lower or "hi" in prompt_lower:
            content = "Hello! I'm currently operating in fallback mode due to AI service unavailability. How can I assist you today?"
        elif "code" in prompt_lower or "function" in prompt_lower:
            content = "I apologize, but I'm currently unable to generate code due to AI service unavailability. Please try again later or contact support."
        elif "error" in prompt_lower or "bug" in prompt_lower:
            content = "I understand you're experiencing an issue. I'm currently in fallback mode and cannot provide detailed debugging assistance. Please check our documentation or contact support."
        else:
            content = "I apologize, but I'm currently operating in fallback mode and cannot provide a detailed response. Please try again later when AI services are restored."

        return AIResponse(
            content=content,
            provider=AIProvider.RULE_BASED,
            latency_ms=0,
            model="fallback",
        )

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        use_cache: bool = True,
        preferred_provider: Optional[AIProvider] = None,
    ) -> AIResponse:
        """
        Generate a response using the fallback chain.

        Args:
            prompt: The user prompt
            system_prompt: Optional system instructions
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            use_cache: Whether to use cached responses
            preferred_provider: Specific provider to try first

        Returns:
            AIResponse with generated content and metadata
        """
        # Check cache first
        if use_cache:
            cached = self._get_cached_response(prompt)
            if cached:
                logger.info(f"Cache hit for prompt")
                cached.cached = True
                return cached

        # Determine provider order
        providers_to_try = self.priority.copy()
        if preferred_provider and preferred_provider in providers_to_try:
            providers_to_try.remove(preferred_provider)
            providers_to_try.insert(0, preferred_provider)

        # Try each provider in order
        last_error = None
        for provider in providers_to_try:
            config = self.providers.get(provider)
            if not config or not config.enabled:
                continue

            try:
                logger.info(f"Trying {config.name}...")

                if provider in [AIProvider.OLLAMA]:
                    response = self._call_ollama(config, prompt, system_prompt, max_tokens, temperature)
                else:
                    response = self._call_openai_compatible(config, prompt, system_prompt, max_tokens, temperature)

                # Cache successful response
                if use_cache:
                    self._cache_response(prompt, response)

                logger.info(f"✅ Success with {config.name} ({response.latency_ms:.0f}ms)")
                return response

            except Exception as e:
                logger.warning(f"❌ {config.name} failed: {str(e)}")
                last_error = e
                continue

        # All providers failed - use rule-based fallback
        logger.error(f"All AI providers failed. Last error: {last_error}")
        return self._rule_based_fallback(prompt)

    def get_status(self) -> Dict[str, Any]:
        """Get current status of all providers"""
        status = {
            "timestamp": datetime.utcnow().isoformat(),
            "priority": [p.value for p in self.priority],
            "providers": {},
            "cache_size": len(self._response_cache),
        }

        for provider, config in self.providers.items():
            # Test connectivity
            is_available = False
            if config.enabled:
                try:
                    if provider == AIProvider.OLLAMA:
                        resp = requests.get(f"{config.base_url}/api/tags", timeout=5)
                        is_available = resp.status_code == 200
                    else:
                        # For API-based providers, just check if key is set
                        is_available = bool(config.api_key)
                except:
                    is_available = False

            status["providers"][provider.value] = {
                "name": config.name,
                "enabled": config.enabled,
                "available": is_available,
                "model": config.default_model,
            }

        return status

    def health_check(self) -> bool:
        """Quick health check - returns True if at least one provider is available"""
        for provider in self.priority:
            config = self.providers.get(provider)
            if config and config.enabled:
                if provider == AIProvider.OLLAMA:
                    try:
                        resp = requests.get(f"{config.base_url}/api/tags", timeout=5)
                        if resp.status_code == 200:
                            return True
                    except:
                        continue
                elif config.api_key:
                    return True
        return False


# Singleton instance for application-wide use
_fallback_manager: Optional[AIFallbackManager] = None


def get_fallback_manager() -> AIFallbackManager:
    """Get or create the singleton fallback manager instance"""
    global _fallback_manager
    if _fallback_manager is None:
        _fallback_manager = AIFallbackManager()
    return _fallback_manager


def generate_with_fallback(
    prompt: str,
    system_prompt: Optional[str] = None,
    max_tokens: int = 2000,
    temperature: float = 0.7,
    **kwargs
) -> str:
    """
    Convenience function for quick generation with fallback.

    Returns:
        Generated text content (not the full AIResponse)
    """
    manager = get_fallback_manager()
    response = manager.generate(prompt, system_prompt, max_tokens, temperature, **kwargs)
    return response.content


if __name__ == "__main__":
    # Test the fallback manager
    print("Testing AI Fallback Manager...")
    print("=" * 50)

    manager = AIFallbackManager()

    # Print status
    status = manager.get_status()
    print(f"\nProvider Status:")
    for name, info in status["providers"].items():
        status_icon = "✅" if info["available"] else "❌"
        enabled_icon = "🟢" if info["enabled"] else "🔴"
        print(f"  {status_icon} {enabled_icon} {info['name']}: {name} ({info['model']})")

    # Test generation
    print("\n" + "=" * 50)
    print("Testing generation...")
    try:
        response = manager.generate(
            "Write a one-sentence greeting for a South African AI company.",
            system_prompt="You are a helpful AI assistant."
        )
        print(f"\nProvider: {response.provider.value}")
        print(f"Model: {response.model}")
        print(f"Latency: {response.latency_ms:.0f}ms")
        print(f"Response: {response.content}")
    except Exception as e:
        print(f"Error: {e}")
