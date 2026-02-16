"""
Unified LLM Client with multi-provider fallback.

Uses your configured API keys:
- GLM5_API_KEY (Primary)
- KIMI_API_KEY (Fallback 1)
- DASHSCOPE_API_KEY (Fallback 2)
- OLLAMA_API_KEY (Local fallback)
"""

import os
import json
import asyncio
import hashlib
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime


class LLMProvider(Enum):
    GLM5 = "glm5"
    KIMI = "kimi"
    DASHSCOPE = "dashscope"
    OLLAMA = "ollama"


@dataclass
class LLMResponse:
    """Standardized LLM response."""
    success: bool
    content: str
    provider: LLMProvider
    latency_ms: float
    tokens_used: int = 0
    model: str = ""
    cached: bool = False
    error: Optional[str] = None
    raw_response: Optional[Dict] = None


class UnifiedLLMClient:
    """
    Enterprise LLM client with automatic failover.
    
    Priority order:
    1. GLM-5 (GLM5_API_KEY)
    2. Kimi K2.5 (KIMI_API_KEY)
    3. DashScope Qwen (DASHSCOPE_API_KEY)
    4. Ollama Local (OLLAMA_API_KEY)
    """
    
    # API endpoints
    ENDPOINTS = {
        LLMProvider.GLM5: "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        LLMProvider.KIMI: "https://api.moonshot.cn/v1/chat/completions",
        LLMProvider.DASHSCOPE: "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
        LLMProvider.OLLAMA: "http://localhost:11434/api/generate",
    }
    
    # Default models
    MODELS = {
        LLMProvider.GLM5: "glm-4-plus",
        LLMProvider.KIMI: "moonshot-v1-128k",
        LLMProvider.DASHSCOPE: "qwen-coder-plus",
        LLMProvider.OLLAMA: "llama3.2",
    }
    
    def __init__(self):
        self.api_keys = self._load_api_keys()
        self.metrics = {
            'requests': {p: 0 for p in LLMProvider},
            'failures': {p: 0 for p in LLMProvider},
            'latency': {p: [] for p in LLMProvider},
        }
        self.cache: Dict[str, LLMResponse] = {}
        self.cache_ttl = 3600  # 1 hour
    
    def _load_api_keys(self) -> Dict[LLMProvider, Optional[str]]:
        """Load API keys from environment."""
        return {
            LLMProvider.GLM5: os.getenv('GLM5_API_KEY'),
            LLMProvider.KIMI: os.getenv('KIMI_API_KEY'),
            LLMProvider.DASHSCOPE: os.getenv('DASHSCOPE_API_KEY'),
            LLMProvider.OLLAMA: os.getenv('OLLAMA_API_KEY') or 'local',
        }
    
    def _get_available_providers(self) -> List[LLMProvider]:
        """Get list of providers with configured API keys."""
        available = []
        for provider, key in self.api_keys.items():
            if key:
                available.append(provider)
        return available
    
    async def generate(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        use_cache: bool = True,
        timeout: float = 60.0
    ) -> LLMResponse:
        """
        Generate with automatic provider fallback.
        
        Tries each available provider in priority order until one succeeds.
        """
        # Check cache
        if use_cache:
            cache_key = self._get_cache_key(prompt, system_message, temperature)
            cached = self._get_from_cache(cache_key)
            if cached:
                return cached
        
        # Get available providers
        providers = self._get_available_providers()
        
        if not providers:
            return LLMResponse(
                success=False,
                content="",
                provider=LLMProvider.GLM5,
                latency_ms=0,
                error="No LLM providers configured. Set GLM5_API_KEY, KIMI_API_KEY, or DASHSCOPE_API_KEY"
            )
        
        # Try each provider
        last_error = None
        for provider in providers:
            try:
                response = await asyncio.wait_for(
                    self._call_provider(provider, prompt, system_message, temperature, max_tokens),
                    timeout=timeout
                )
                
                if response.success:
                    # Cache successful response
                    if use_cache:
                        self._save_to_cache(cache_key, response)
                    return response
                else:
                    last_error = response.error
                    
            except asyncio.TimeoutError:
                last_error = f"{provider.value} timeout"
                self.metrics['failures'][provider] += 1
            except Exception as e:
                last_error = str(e)
                self.metrics['failures'][provider] += 1
        
        # All providers failed
        return LLMResponse(
            success=False,
            content="",
            provider=providers[0] if providers else LLMProvider.GLM5,
            latency_ms=0,
            error=f"All providers failed. Last error: {last_error}"
        )
    
    async def _call_provider(
        self,
        provider: LLMProvider,
        prompt: str,
        system_message: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> LLMResponse:
        """Call specific provider API."""
        start_time = time.time()
        api_key = self.api_keys[provider]
        
        if not api_key:
            return LLMResponse(
                success=False,
                content="",
                provider=provider,
                latency_ms=0,
                error=f"API key not configured for {provider.value}"
            )
        
        # Use appropriate caller
        if provider == LLMProvider.GLM5:
            response = await self._call_glm5(api_key, prompt, system_message, temperature, max_tokens)
        elif provider == LLMProvider.KIMI:
            response = await self._call_kimi(api_key, prompt, system_message, temperature, max_tokens)
        elif provider == LLMProvider.DASHSCOPE:
            response = await self._call_dashscope(api_key, prompt, system_message, temperature, max_tokens)
        elif provider == LLMProvider.OLLAMA:
            response = await self._call_ollama(prompt, system_message, temperature, max_tokens)
        else:
            response = LLMResponse(
                success=False,
                content="",
                provider=provider,
                latency_ms=0,
                error=f"Unknown provider: {provider}"
            )
        
        # Update metrics
        latency = (time.time() - start_time) * 1000
        response.latency_ms = latency
        self.metrics['requests'][provider] += 1
        self.metrics['latency'][provider].append(latency)
        
        return response
    
    async def _call_glm5(
        self,
        api_key: str,
        prompt: str,
        system_message: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> LLMResponse:
        """Call GLM-5 API."""
        import aiohttp
        
        url = self.ENDPOINTS[LLMProvider.GLM5]
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.MODELS[LLMProvider.GLM5],
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    return LLMResponse(
                        success=False,
                        content="",
                        provider=LLMProvider.GLM5,
                        latency_ms=0,
                        error=f"HTTP {resp.status}: {error_text[:200]}"
                    )
                
                data = await resp.json()
                content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                tokens = data.get('usage', {}).get('total_tokens', 0)
                
                return LLMResponse(
                    success=True,
                    content=content,
                    provider=LLMProvider.GLM5,
                    latency_ms=0,
                    tokens_used=tokens,
                    model=self.MODELS[LLMProvider.GLM5],
                    raw_response=data
                )
    
    async def _call_kimi(
        self,
        api_key: str,
        prompt: str,
        system_message: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> LLMResponse:
        """Call Kimi API."""
        import aiohttp
        
        url = self.ENDPOINTS[LLMProvider.KIMI]
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.MODELS[LLMProvider.KIMI],
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    return LLMResponse(
                        success=False,
                        content="",
                        provider=LLMProvider.KIMI,
                        latency_ms=0,
                        error=f"HTTP {resp.status}: {error_text[:200]}"
                    )
                
                data = await resp.json()
                content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                tokens = data.get('usage', {}).get('total_tokens', 0)
                
                return LLMResponse(
                    success=True,
                    content=content,
                    provider=LLMProvider.KIMI,
                    latency_ms=0,
                    tokens_used=tokens,
                    model=self.MODELS[LLMProvider.KIMI],
                    raw_response=data
                )
    
    async def _call_dashscope(
        self,
        api_key: str,
        prompt: str,
        system_message: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> LLMResponse:
        """Call DashScope API."""
        import aiohttp
        
        url = self.ENDPOINTS[LLMProvider.DASHSCOPE]
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.MODELS[LLMProvider.DASHSCOPE],
            "input": {"messages": messages},
            "parameters": {
                "temperature": temperature,
                "max_tokens": max_tokens
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    return LLMResponse(
                        success=False,
                        content="",
                        provider=LLMProvider.DASHSCOPE,
                        latency_ms=0,
                        error=f"HTTP {resp.status}: {error_text[:200]}"
                    )
                
                data = await resp.json()
                content = data.get('output', {}).get('text', '')
                tokens = data.get('usage', {}).get('total_tokens', 0)
                
                return LLMResponse(
                    success=True,
                    content=content,
                    provider=LLMProvider.DASHSCOPE,
                    latency_ms=0,
                    tokens_used=tokens,
                    model=self.MODELS[LLMProvider.DASHSCOPE],
                    raw_response=data
                )
    
    async def _call_ollama(
        self,
        prompt: str,
        system_message: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> LLMResponse:
        """Call Ollama local API."""
        import aiohttp
        
        url = self.ENDPOINTS[LLMProvider.OLLAMA]
        
        full_prompt = prompt
        if system_message:
            full_prompt = f"{system_message}\n\n{prompt}"
        
        payload = {
            "model": self.MODELS[LLMProvider.OLLAMA],
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        return LLMResponse(
                            success=False,
                            content="",
                            provider=LLMProvider.OLLAMA,
                            latency_ms=0,
                            error=f"HTTP {resp.status}: {error_text[:200]}"
                        )
                    
                    data = await resp.json()
                    content = data.get('response', '')
                    
                    return LLMResponse(
                        success=True,
                        content=content,
                        provider=LLMProvider.OLLAMA,
                        latency_ms=0,
                        tokens_used=0,
                        model=self.MODELS[LLMProvider.OLLAMA],
                        raw_response=data
                    )
        except Exception as e:
            return LLMResponse(
                success=False,
                content="",
                provider=LLMProvider.OLLAMA,
                latency_ms=0,
                error=f"Ollama connection failed: {e}"
            )
    
    def _get_cache_key(self, *args) -> str:
        """Generate cache key."""
        key_data = json.dumps(args, sort_keys=True)
        return hashlib.sha256(key_data.encode()).hexdigest()
    
    def _get_from_cache(self, key: str) -> Optional[LLMResponse]:
        """Get cached response."""
        if key in self.cache:
            cached = self.cache[key]
            if time.time() - cached.get('timestamp', 0) < self.cache_ttl:
                return cached['response']
        return None
    
    def _save_to_cache(self, key: str, response: LLMResponse):
        """Save to cache."""
        self.cache[key] = {
            'response': response,
            'timestamp': time.time()
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get usage metrics."""
        return {
            'requests': {k.value: v for k, v in self.metrics['requests'].items()},
            'failures': {k.value: v for k, v in self.metrics['failures'].items()},
            'avg_latency_ms': {
                k.value: sum(v) / len(v) if v else 0
                for k, v in self.metrics['latency'].items()
            },
            'available_providers': [p.value for p in self._get_available_providers()]
        }
