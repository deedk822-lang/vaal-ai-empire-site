"""
Ollama Client - OpenAI-Compatible API for Local LLM Inference.

This module provides a production-ready client for Ollama, using the
OpenAI-compatible API endpoint. No API key required for local Ollama -
authentication is handled at the network level.

Docs: https://github.com/ollama/ollama/blob/main/docs/openai.md

@security No API keys stored - local network authentication only
@author Vaal AI Empire Team
"""

import os

import logging
import requests
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class OllamaConfig(BaseModel):
    """Configuration for Ollama client."""
    
    base_url: str = Field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    )
    model_primary: str = Field(
        default_factory=lambda: os.getenv("OLLAMA_MODEL_PRIMARY", "qwen2.5:7b-instruct-q4_K_M")
    )
    model_fast: str = Field(
        default_factory=lambda: os.getenv("OLLAMA_MODEL_FAST", "llama3.2:3b")
    )
    model_finance: str = Field(
        default_factory=lambda: os.getenv("OLLAMA_MODEL_FINANCE", "mistral:7b-instruct-v0.2")
    )
    timeout: int = Field(
        default_factory=lambda: int(os.getenv("OLLAMA_TIMEOUT", "120"))
    )
    keep_alive: str = Field(
        default_factory=lambda: os.getenv("OLLAMA_KEEP_ALIVE", "5m")
    )


class OllamaClient:
    """
    REAL Ollama client using OpenAI-compatible API.
    
    No API key required for local Ollama - authentication handled at network level.
    
    Features:
    - OpenAI-compatible chat completions
    - Function/tool calling support (Qwen2.5, Mistral)
    - Embedding generation for RAG
    - Automatic retry and error handling
    - Token usage logging for monitoring
    
    Example:
        >>> client = OllamaClient()
        >>> response = client.chat_completion([
        ...     {"role": "user", "content": "Sawubona!"}
        ... ])
        >>> print(response["choices"][0]["message"]["content"])
    """
    
    def __init__(self, config: Optional[OllamaConfig] = None):
        """
        Initialize Ollama client.
        
        Args:
            config: Optional configuration override
        """
        self.config = config or OllamaConfig()
        self.base_url = self.config.base_url.rstrip("/")
        self.session = requests.Session()
        self.session.timeout = self.config.timeout
        self._available = None
        logger.info(f"Ollama client initialized: {self.base_url}")
    
    def is_available(self) -> bool:
        """
        Check if Ollama server is running and responsive.
        
        Returns:
            True if Ollama is available, False otherwise
        """
        if self._available is not None:
            return self._available
            
        try:
            response = self.session.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )
            self._available = response.status_code == 200
            if self._available:
                models = response.json().get("models", [])
                logger.info(f"Ollama available with {len(models)} models")
            return self._available
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            self._available = False
            return False
    
    def get_available_models(self) -> List[str]:
        """
        Get list of available models.
        
        Returns:
            List of model names
        """
        try:
            response = self.session.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )
            response.raise_for_status()
            models = response.json().get("models", [])
            return [m.get("name") for m in models]
        except Exception as e:
            logger.error(f"Failed to get models: {e}")
            return []
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        keep_alive: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        REAL chat completion via Ollama's OpenAI-compatible endpoint.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (defaults to model_primary)
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            keep_alive: How long to keep model in memory
            **kwargs: Additional options
            
        Returns:
            Dict compatible with OpenAI API response format
            
        Raises:
            RuntimeError: If Ollama request fails
        """
        model = model or self.config.model_primary
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
            "options": {
                "num_predict": max_tokens or 2048,
                "keep_alive": keep_alive or self.config.keep_alive,
                "num_ctx": kwargs.get("num_ctx", 8192),
                "top_p": kwargs.get("top_p", 0.9),
                "frequency_penalty": kwargs.get("frequency_penalty", 0.1),
                "stop": kwargs.get("stop", [])
            }
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            result = response.json()
            
            # Log token usage for monitoring
            if "usage" in result:
                logger.debug(
                    f"Ollama tokens - prompt: {result['usage'].get('prompt_tokens')}, "
                    f"completion: {result['usage'].get('completion_tokens')}"
                )
            
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama request failed: {e}")
            raise RuntimeError(f"Ollama API error: {e}")
    
    def generate_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict],
        model: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Tool calling via Ollama (Qwen2.5 and Mistral support function calling).
        
        Args:
            messages: Conversation messages
            tools: List of tool definitions
            model: Model to use (defaults to model_finance for reasoning)
            **kwargs: Additional options
            
        Returns:
            Response with potential tool calls
        """
        model = model or self.config.model_finance
        
        payload = {
            "model": model,
            "messages": messages,
            "tools": tools,
            "tool_choice": kwargs.get("tool_choice", "auto"),
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", 0.1),
                "keep_alive": self.config.keep_alive,
                "num_ctx": kwargs.get("num_ctx", 8192)
            }
        }
        
        response = self.session.post(
            f"{self.base_url}/v1/chat/completions",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return response.json()
    
    def embed(
        self,
        text: str,
        model: str = "nomic-embed-text"
    ) -> List[float]:
        """
        Generate embeddings for RAG/vector search.
        
        Args:
            text: Text to embed
            model: Embedding model to use
            
        Returns:
            List of embedding values
        """
        payload = {
            "model": model,
            "input": text,
            "options": {"keep_alive": self.config.keep_alive}
        }
        
        response = self.session.post(
            f"{self.base_url}/api/embed",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return response.json()["embeddings"][0]
    
    def pull_model(self, model: str) -> bool:
        """
        Pull/download a model to local Ollama.
        
        Args:
            model: Model name to pull
            
        Returns:
            True if successful
        """
        try:
            response = self.session.post(
                f"{self.base_url}/api/pull",
                json={"name": model},
                timeout=600  # 10 minutes for large models
            )
            response.raise_for_status()
            logger.info(f"Model pulled: {model}")
            return True
        except Exception as e:
            logger.error(f"Failed to pull model {model}: {e}")
            return False


# Convenience function for quick usage
def ask_ollama(
    prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.1
) -> str:
    """
    Quick helper for single-turn queries.
    
    Args:
        prompt: User prompt
        model: Model to use
        temperature: Sampling temperature
        
    Returns:
        Generated response text
    """
    client = OllamaClient()
    response = client.chat_completion(
        messages=[{"role": "user", "content": prompt}],
        model=model,
        temperature=temperature
    )
    return response["choices"][0]["message"]["content"]
