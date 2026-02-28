"""AI Fallback Manager for Vaal AI Empire.

Provides resilient AI service with automatic fallback chain:
1. Primary: External APIs (Kimi, Dashscope, GLM)
2. Secondary: Ollama (local models)
3. Tertiary: LocalAI (OpenAI-compatible local server)
4. Quaternary: Cached responses / rule-based fallback
"""

from __future__ import annotations

import hashlib
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class AIProvider(str, Enum):
    """Available AI providers in priority order."""

    KIMI = "kimi"
    DASHSCOPE = "dashscope"
    GLM = "glm"
    OLLAMA = "ollama"
    LOCALAI = "localai"
    CACHE = "cache"
    RULE_BASED = "rule_based"


@dataclass
class AIResponse:
    """Standardized AI response."""

    content: str
    provider: AIProvider
    latency_ms: float
    tokens_used: Optional[int] = None
    model: Optional[str] = None
    cached: bool = False
    error: Optional[str] = None


@dataclass
class ProviderConfig:
    """Configuration for an AI provider."""

    name: str
    api_key: Optional[str]
    base_url: str
    default_model: str
    timeout_seconds: int = 30
    retry_attempts: int = 3
    enabled: bool = True


@dataclass
class CacheEntry:
    """Internal cache container with timestamp for TTL checks."""

    response: AIResponse
    stored_at: datetime


class AIFallbackManager:
    """Manages AI providers with automatic fallback chain."""

    DEFAULT_PRIORITY = [
        AIProvider.KIMI,
        AIProvider.DASHSCOPE,
        AIProvider.GLM,
        AIProvider.OLLAMA,
        AIProvider.LOCALAI,
    ]

    def __init__(self, priority: Optional[List[AIProvider]] = None):
        self.priority = priority or self.DEFAULT_PRIORITY
        self.providers: Dict[AIProvider, ProviderConfig] = {}
        self._response_cache: Dict[str, CacheEntry] = {}
        self._cache_ttl = timedelta(minutes=30)
        self._setup_providers()

    def _setup_providers(self) -> None:
        """Configure all available providers from environment."""

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
                api_key=os.getenv("GLM5_API_KEY") or os.getenv("GLM_API_KEY"),
                base_url="https://open.bigmodel.cn/api/paas/v4",
                default_model="glm-4-flash",
                timeout_seconds=30,
            ),
            AIProvider.OLLAMA: ProviderConfig(
                name="Ollama (Local)",
                api_key=os.getenv("OLLAMA_API_KEY", "ollama"),
                base_url=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
                default_model=os.getenv("OLLAMA_MODEL", "qwen2.5-coder:1.5b"),
                timeout_seconds=60,
            ),
            AIProvider.LOCALAI: ProviderConfig(
                name="LocalAI (Fallback)",
                api_key=os.getenv("LOCALAI_API_KEY", "localai"),
                base_url=os.getenv("LOCALAI_URL", "http://localhost:8080/v1"),
                default_model=os.getenv("LOCALAI_MODEL", "qwen2.5-coder:1.5b"),
                timeout_seconds=120,
            ),
        }

        for provider, config in self.providers.items():
            if not config.api_key and provider not in (AIProvider.OLLAMA, AIProvider.LOCALAI):
                config.enabled = False
                logger.warning("%s disabled: no API key configured", config.name)

    def _get_cache_key(self, prompt: str, model: Optional[str] = None) -> str:
        key_data = f"{prompt}:{model or 'default'}"
        return hashlib.sha256(key_data.encode("utf-8")).hexdigest()

    def _get_cached_response(self, prompt: str, model: Optional[str] = None) -> Optional[AIResponse]:
        cache_key = self._get_cache_key(prompt, model)
        entry = self._response_cache.get(cache_key)
        if entry is None:
            return None

        if datetime.utcnow() - entry.stored_at > self._cache_ttl:
            del self._response_cache[cache_key]
            return None

        return AIResponse(
            content=entry.response.content,
            provider=AIProvider.CACHE,
            latency_ms=0.0,
            tokens_used=entry.response.tokens_used,
            model=entry.response.model,
            cached=True,
        )

    def _cache_response(self, prompt: str, response: AIResponse, model: Optional[str] = None) -> None:
        cache_key = self._get_cache_key(prompt, model)
        self._response_cache[cache_key] = CacheEntry(response=response, stored_at=datetime.utcnow())

    def _get_provider_from_config(self, config: ProviderConfig) -> AIProvider:
        for provider, cfg in self.providers.items():
            if cfg == config:
                return provider
        return AIProvider.RULE_BASED

    def _call_openai_compatible(
        self,
        config: ProviderConfig,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> AIResponse:
        start_time = time.time()

        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }
        messages: List[Dict[str, str]] = []
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
            resp = requests.post(
                f"{config.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=config.timeout_seconds,
            )
            resp.raise_for_status()
            data = resp.json()

            content = data["choices"][0]["message"]["content"]
            tokens = data.get("usage", {}).get("total_tokens")
            model_used = data.get("model", config.default_model)
            return AIResponse(
                content=content,
                provider=self._get_provider_from_config(config),
                latency_ms=(time.time() - start_time) * 1000,
                tokens_used=tokens,
                model=model_used,
            )
        except requests.exceptions.Timeout as exc:
            raise TimeoutError(f"{config.name} request timed out") from exc
        except requests.exceptions.RequestException as exc:
            raise ConnectionError(f"{config.name} request failed: {exc}") from exc
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError(f"Invalid response from {config.name}: {exc}") from exc

    def _call_ollama(
        self,
        config: ProviderConfig,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> AIResponse:
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
            resp = requests.post(
                f"{config.base_url}/api/generate",
                json=payload,
                timeout=config.timeout_seconds,
            )
            resp.raise_for_status()
            data = resp.json()
            return AIResponse(
                content=data.get("response", ""),
                provider=AIProvider.OLLAMA,
                latency_ms=(time.time() - start_time) * 1000,
                tokens_used=data.get("eval_count"),
                model=config.default_model,
            )
        except requests.exceptions.ConnectionError as exc:
            raise ConnectionError(f"Ollama not available at {config.base_url}") from exc
        except requests.exceptions.Timeout as exc:
            raise TimeoutError("Ollama request timed out") from exc
        except requests.exceptions.RequestException as exc:
            raise ConnectionError(f"Ollama request failed: {exc}") from exc

    def _rule_based_fallback(self, prompt: str) -> AIResponse:
        prompt_lower = prompt.lower()

        if "hello" in prompt_lower or "hi" in prompt_lower:
            content = (
                "Hello! I'm currently operating in fallback mode due to AI service "
                "unavailability. How can I assist you today?"
            )
        elif "code" in prompt_lower or "function" in prompt_lower:
            content = (
                "I apologize, but I'm currently unable to generate code due to AI "
                "service unavailability. Please try again later or contact support."
            )
        elif "error" in prompt_lower or "bug" in prompt_lower:
            content = (
                "I understand you're experiencing an issue. I'm currently in fallback "
                "mode and cannot provide detailed debugging assistance."
            )
        else:
            content = (
                "I apologize, but I'm currently operating in fallback mode and cannot "
                "provide a detailed response. Please try again later."
            )

        return AIResponse(content=content, provider=AIProvider.RULE_BASED, latency_ms=0.0, model="fallback")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        use_cache: bool = True,
        preferred_provider: Optional[AIProvider] = None,
    ) -> AIResponse:
        if use_cache:
            cached = self._get_cached_response(prompt)
            if cached is not None:
                return cached

        providers_to_try = self.priority.copy()
        if preferred_provider and preferred_provider in providers_to_try:
            providers_to_try.remove(preferred_provider)
            providers_to_try.insert(0, preferred_provider)

        last_error: Optional[Exception] = None
        for provider in providers_to_try:
            config = self.providers.get(provider)
            if not config or not config.enabled:
                continue

            try:
                if provider == AIProvider.OLLAMA:
                    response = self._call_ollama(config, prompt, system_prompt, max_tokens, temperature)
                else:
                    response = self._call_openai_compatible(config, prompt, system_prompt, max_tokens, temperature)

                if use_cache:
                    self._cache_response(prompt, response)

                return response
            except Exception as exc:  # noqa: BLE001
                logger.warning("Provider %s failed: %s", config.name, exc)
                last_error = exc

        logger.error("All AI providers failed. Last error: %s", last_error)
        return self._rule_based_fallback(prompt)

    def get_status(self) -> Dict[str, Any]:
        status: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "priority": [p.value for p in self.priority],
            "providers": {},
            "cache_size": len(self._response_cache),
        }

        for provider, config in self.providers.items():
            available = False
            if config.enabled:
                try:
                    if provider == AIProvider.OLLAMA:
                        resp = requests.get(f"{config.base_url}/api/tags", timeout=5)
                        available = resp.status_code == 200
                    elif provider == AIProvider.LOCALAI:
                        resp = requests.get(f"{config.base_url}/models", timeout=5)
                        available = resp.status_code == 200
                    else:
                        available = bool(config.api_key)
                except requests.RequestException:
                    available = False

            status["providers"][provider.value] = {
                "name": config.name,
                "enabled": config.enabled,
                "available": available,
                "model": config.default_model,
            }

        return status

    def health_check(self) -> bool:
        for provider in self.priority:
            config = self.providers.get(provider)
            if not config or not config.enabled:
                continue

            if provider == AIProvider.OLLAMA:
                try:
                    resp = requests.get(f"{config.base_url}/api/tags", timeout=5)
                    if resp.status_code == 200:
                        return True
                except requests.RequestException:
                    continue
            elif provider == AIProvider.LOCALAI:
                try:
                    resp = requests.get(f"{config.base_url}/models", timeout=5)
                    if resp.status_code == 200:
                        return True
                except requests.RequestException:
                    continue
            elif config.api_key:
                return True

        return False


_fallback_manager: Optional[AIFallbackManager] = None


def get_fallback_manager() -> AIFallbackManager:
    """Get or create singleton fallback manager instance."""

    global _fallback_manager
    if _fallback_manager is None:
        _fallback_manager = AIFallbackManager()
    return _fallback_manager


def generate_with_fallback(
    prompt: str,
    system_prompt: Optional[str] = None,
    max_tokens: int = 2000,
    temperature: float = 0.7,
    **kwargs: Any,
) -> str:
    """Convenience function returning generated content only."""

    manager = get_fallback_manager()
    response = manager.generate(prompt, system_prompt, max_tokens, temperature, **kwargs)
    return response.content
