"""
Model Router - Intelligent Routing Between Ollama and DashScope.

Production routing strategy:
- 90% of requests: Ollama local (qwen2.5:7b) - unlimited, no latency
- 10% complex tasks: DashScope fallback (qwen2.5-7b-instruct) - 1M free tokens/month
- Automatic failover with circuit breaker pattern

@author Vaal AI Empire Team
"""

import os
import logging
from typing import Optional, List, Dict, Any, Literal
from dataclasses import dataclass
from enum import Enum

from .ollama_client import OllamaClient, OllamaConfig

logger = logging.getLogger(__name__)


class Provider(str, Enum):
    """Available model providers."""
    OLLAMA = "ollama"
    DASHSCOPE = "dashscope"
    AUTO = "auto"


@dataclass
class ModelMapping:
    """Model mapping for different providers."""
    ollama: str
    dashscope: str


# Default model mappings
DEFAULT_MODELS = {
    "primary": ModelMapping(
        ollama="qwen2.5:7b-instruct-q4_K_M",
        dashscope="qwen2.5-7b-instruct"
    ),
    "fast": ModelMapping(
        ollama="llama3.2:3b",
        dashscope="qwen2.5-3b-instruct"
    ),
    "finance": ModelMapping(
        ollama="mistral:7b-instruct-v0.2",
        dashscope="qwen2.5-7b-instruct"
    ),
    "multilingual": ModelMapping(
        ollama="qwen2.5:7b-instruct-q4_K_M",  # Qwen2.5 supports 100+ languages
        dashscope="qwen2.5-7b-instruct"
    )
}


class ModelRouter:
    """
    Intelligent model router with automatic failover.
    
    Strategy:
    - Ollama (primary): Free, unlimited, low latency
    - DashScope (fallback): Cloud backup with free tier
    
    Features:
    - Circuit breaker pattern for automatic failover
    - Configurable retry thresholds
    - Task-based model selection
    - Automatic recovery detection
    
    Example:
        >>> router = ModelRouter()
        >>> response = router.chat_completion(
        ...     messages=[{"role": "user", "content": "Hello!"}]
        ... )
    """
    
    def __init__(self):
        """Initialize model router with primary and fallback providers."""
        # Initialize Ollama (primary)
        ollama_config = OllamaConfig(
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            model_primary=os.getenv("OLLAMA_MODEL_PRIMARY", "qwen2.5:7b-instruct-q4_K_M"),
            model_fast=os.getenv("OLLAMA_MODEL_FAST", "llama3.2:3b"),
            model_finance=os.getenv("OLLAMA_MODEL_FINANCE", "mistral:7b-instruct-v0.2")
        )
        self.ollama = OllamaClient(ollama_config)
        
        # Initialize DashScope (fallback) - lazy loaded
        self._dashscope = None
        self._dashscope_available = None
        
        # Configuration flags
        self.use_ollama_primary = os.getenv("USE_OLLAMA_PRIMARY", "true").lower() == "true"
        self.enable_fallback = os.getenv("ENABLE_FALLBACK", "true").lower() == "true"
        self.fallback_threshold = int(os.getenv("FALLBACK_THRESHOLD", "3"))
        
        # Circuit breaker state
        self.ollama_failures = 0
        self.circuit_open = False
        
        logger.info(
            f"ModelRouter initialized: Ollama primary={self.use_ollama_primary}, "
            f"fallback={self.enable_fallback}"
        )
    
    @property
    def dashscope(self):
        """Lazy load DashScope client."""
        if self._dashscope is None:
            try:
                from .qwen_client import QwenClient, QwenConfig
                dashscope_config = QwenConfig(
                    base_url=os.getenv(
                        "DASHSCOPE_BASE_URL",
                        "https://dashscope.aliyuncs.com/compatible-mode/v1"
                    ),
                    api_key_env="DASHSCOPE_API_KEY"
                )
                self._dashscope = QwenClient(dashscope_config)
            except ImportError:
                logger.warning("DashScope client not available - qwen_client.py not found")
                self._dashscope = None
        return self._dashscope
    
    def _record_ollama_success(self):
        """Reset failure counter on success."""
        if self.ollama_failures > 0:
            logger.info(f"Ollama recovered after {self.ollama_failures} failures")
        self.ollama_failures = 0
        self.circuit_open = False
    
    def _record_ollama_failure(self):
        """Track failures and open circuit if threshold exceeded."""
        self.ollama_failures += 1
        logger.warning(f"Ollama failure #{self.ollama_failures}/{self.fallback_threshold}")
        
        if self.ollama_failures >= self.fallback_threshold:
            self.circuit_open = True
            logger.warning("Circuit breaker OPEN - routing to fallback")
    
    def _should_use_fallback(self) -> bool:
        """Determine if we should use fallback provider."""
        if not self.enable_fallback:
            return False
        if self.circuit_open:
            return True
        if not self.use_ollama_primary:
            return True
        if not self.ollama.is_available():
            return True
        return False
    
    def is_dashscope_available(self) -> bool:
        """Check if DashScope is available."""
        if self._dashscope_available is not None:
            return self._dashscope_available
        
        if self.dashscope is None:
            self._dashscope_available = False
            return False
        
        try:
            available = self.dashscope.is_available()
            self._dashscope_available = available
            return available
        except Exception as e:
            logger.warning(f"DashScope availability check failed: {e}")
            self._dashscope_available = False
            return False
    
    def chat_completion(self, **kwargs) -> Dict[str, Any]:
        """
        Route chat completion with automatic failover.
        
        Args:
            **kwargs: Arguments passed to underlying client
            
        Returns:
            Response dict from the model provider
            
        Raises:
            RuntimeError: If no providers available
        """
        # Try Ollama first (if enabled and available)
        if self.use_ollama_primary and not self.circuit_open:
            try:
                logger.debug("Routing to Ollama (local)")
                result = self.ollama.chat_completion(**kwargs)
                self._record_ollama_success()
                return result
            except Exception as e:
                logger.warning(f"Ollama failed: {e}")
                self._record_ollama_failure()
                # Fall through to fallback if enabled
        
        # Fallback to DashScope
        if self.enable_fallback and self.is_dashscope_available():
            try:
                logger.info("Routing to DashScope (cloud fallback)")
                # Map model names for DashScope
                model = kwargs.get("model")
                if model:
                    for key, mapping in DEFAULT_MODELS.items():
                        if model == mapping.ollama:
                            kwargs["model"] = mapping.dashscope
                            break
                
                return self.dashscope.create_completion(**kwargs)
            except Exception as e:
                logger.error(f"Fallback failed: {e}")
                raise
        
        # No providers available
        raise RuntimeError(
            "No available model provider - check Ollama server and DASHSCOPE_API_KEY"
        )
    
    def get_model_for_task(self, task_type: str) -> str:
        """
        Select optimal model based on task type.
        
        Args:
            task_type: One of 'voice', 'finance', 'multilingual', 'general'
            
        Returns:
            Model name for the selected provider
        """
        mapping = DEFAULT_MODELS.get(task_type, DEFAULT_MODELS["primary"])
        
        if self._should_use_fallback():
            return mapping.dashscope
        return mapping.ollama
    
    def get_provider_status(self) -> Dict[str, Any]:
        """
        Get status of all providers.
        
        Returns:
            Dict with provider availability and circuit breaker status
        """
        return {
            "ollama": {
                "available": self.ollama.is_available(),
                "primary": self.use_ollama_primary,
                "failures": self.ollama_failures,
                "circuit_open": self.circuit_open
            },
            "dashscope": {
                "available": self.is_dashscope_available(),
                "fallback_enabled": self.enable_fallback
            },
            "current_provider": "dashscope" if self._should_use_fallback() else "ollama"
        }
    
    def reset_circuit_breaker(self):
        """Manually reset the circuit breaker."""
        self.ollama_failures = 0
        self.circuit_open = False
        self.ollama._available = None
        logger.info("Circuit breaker reset")


# Task classification helper
def classify_task(text: str) -> Literal['voice', 'finance', 'multilingual', 'general']:
    """
    Classify task type based on input text.
    
    Args:
        text: User input text
        
    Returns:
        Task type string
    """
    text_lower = text.lower()
    
    # Financial keywords
    if any(kw in text_lower for kw in [
        'send', 'pay', 'transfer', 'rlusd', 'xrp', 'remittance',
        'money', 'transaction', 'balance', 'rate', 'zar', 'usd'
    ]):
        return 'finance'
    
    # African language keywords
    if any(kw in text_lower for kw in [
        'zulu', 'xhosa', 'sotho', 'isi', 'sesotho', 'setswana',
        'ngiyabonga', 'sawubona', 'enkosi', 'dumela'
    ]):
        return 'multilingual'
    
    # Short queries = voice (fast model)
    if len(text.split()) < 10:
        return 'voice'
    
    return 'general'
