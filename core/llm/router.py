"""
LLM Router - Routes requests to appropriate LLM providers.
Supports OpenAI, Anthropic, Cohere, and local models with fallback capabilities.
"""

import os
import json
import asyncio
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
import httpx


class ProviderType(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    COHERE = "cohere"
    LOCAL = "local"
    OLLAMA = "ollama"


@dataclass
class Message:
    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class LLMResponse:
    model: str
    content: str
    usage: Dict[str, int]
    metadata: Dict[str, Any] = field(default_factory=dict)
    finish_reason: str = "stop"


@dataclass
class ProviderConfig:
    name: str
    provider_type: ProviderType
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    models: List[str] = field(default_factory=list)
    default_model: Optional[str] = None
    timeout: float = 60.0
    max_retries: int = 3


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers"""

    def __init__(self, config: ProviderConfig):
        self.config = config
        self.client = httpx.AsyncClient(timeout=config.timeout)

    @abstractmethod
    async def complete(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        pass

    @abstractmethod
    async def stream(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        pass

    async def close(self):
        await self.client.aclose()


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider"""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.base_url = config.base_url or "https://api.openai.com/v1"
        self.api_key = config.api_key or os.getenv("OPENAI_API_KEY", "")

    async def complete(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        model = model or self.config.default_model or "gpt-4"
        
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        response = await self.client.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers=headers
        )
        response.raise_for_status()
        data = response.json()

        return LLMResponse(
            model=data["model"],
            content=data["choices"][0]["message"]["content"],
            usage=data.get("usage", {}),
            finish_reason=data["choices"][0].get("finish_reason", "stop"),
            metadata={"provider": "openai", "id": data.get("id")}
        )

    async def stream(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        model = model or self.config.default_model or "gpt-4"

        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "stream": True
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        async with self.client.stream(
            "POST",
            f"{self.base_url}/chat/completions",
            json=payload,
            headers=headers
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]
                    except json.JSONDecodeError:
                        continue


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude API provider"""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.base_url = config.base_url or "https://api.anthropic.com/v1"
        self.api_key = config.api_key or os.getenv("ANTHROPIC_API_KEY", "")

    async def complete(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        model = model or self.config.default_model or "claude-3-sonnet-20240229"

        # Extract system message if present
        system_content = ""
        chat_messages = []
        for m in messages:
            if m.role == "system":
                system_content = m.content
            else:
                chat_messages.append({"role": m.role, "content": m.content})

        payload = {
            "model": model,
            "messages": chat_messages,
            "max_tokens": max_tokens or 4096,
            "temperature": temperature,
        }
        if system_content:
            payload["system"] = system_content

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }

        response = await self.client.post(
            f"{self.base_url}/messages",
            json=payload,
            headers=headers
        )
        response.raise_for_status()
        data = response.json()

        return LLMResponse(
            model=data["model"],
            content=data["content"][0]["text"],
            usage={
                "prompt_tokens": data["usage"]["input_tokens"],
                "completion_tokens": data["usage"]["output_tokens"],
                "total_tokens": data["usage"]["input_tokens"] + data["usage"]["output_tokens"]
            },
            finish_reason=data.get("stop_reason", "stop"),
            metadata={"provider": "anthropic", "id": data.get("id")}
        )

    async def stream(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        model = model or self.config.default_model or "claude-3-sonnet-20240229"

        system_content = ""
        chat_messages = []
        for m in messages:
            if m.role == "system":
                system_content = m.content
            else:
                chat_messages.append({"role": m.role, "content": m.content})

        payload = {
            "model": model,
            "messages": chat_messages,
            "max_tokens": max_tokens or 4096,
            "temperature": temperature,
            "stream": True
        }
        if system_content:
            payload["system"] = system_content

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }

        async with self.client.stream(
            "POST",
            f"{self.base_url}/messages",
            json=payload,
            headers=headers
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        if data["type"] == "content_block_delta":
                            yield data["delta"]["text"]
                    except (json.JSONDecodeError, KeyError):
                        continue


class OllamaProvider(BaseLLMProvider):
    """Ollama local model provider"""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.base_url = config.base_url or "http://localhost:11434"

    async def complete(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        model = model or self.config.default_model or "llama3"

        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": {
                "temperature": temperature,
            }
        }
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        response = await self.client.post(
            f"{self.base_url}/api/chat",
            json=payload
        )
        response.raise_for_status()
        data = response.json()

        return LLMResponse(
            model=data["model"],
            content=data["message"]["content"],
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
            },
            finish_reason="stop",
            metadata={"provider": "ollama", "total_duration": data.get("total_duration")}
        )

    async def stream(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        model = model or self.config.default_model or "llama3"

        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
            "options": {
                "temperature": temperature,
            }
        }
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        async with self.client.stream(
            "POST",
            f"{self.base_url}/api/chat",
            json=payload
        ) as response:
            async for line in response.aiter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        if "message" in data and "content" in data["message"]:
                            yield data["message"]["content"]
                    except json.JSONDecodeError:
                        continue


class LLMRouter:
    """
    Routes LLM requests to appropriate providers.
    Supports model selection, fallback, and load balancing.
    """

    # Model to provider mapping
    MODEL_PROVIDERS = {
        # OpenAI models
        "gpt-4": ProviderType.OPENAI,
        "gpt-4-turbo": ProviderType.OPENAI,
        "gpt-4o": ProviderType.OPENAI,
        "gpt-4o-mini": ProviderType.OPENAI,
        "gpt-3.5-turbo": ProviderType.OPENAI,
        # Anthropic models
        "claude-3-opus": ProviderType.ANTHROPIC,
        "claude-3-sonnet": ProviderType.ANTHROPIC,
        "claude-3-haiku": ProviderType.ANTHROPIC,
        "claude-3-5-sonnet": ProviderType.ANTHROPIC,
        "claude-3-opus-20240229": ProviderType.ANTHROPIC,
        "claude-3-sonnet-20240229": ProviderType.ANTHROPIC,
        "claude-3-haiku-20240307": ProviderType.ANTHROPIC,
        # Ollama/Local models
        "llama3": ProviderType.OLLAMA,
        "llama3.1": ProviderType.OLLAMA,
        "llama3.2": ProviderType.OLLAMA,
        "mistral": ProviderType.OLLAMA,
        "mixtral": ProviderType.OLLAMA,
        "codellama": ProviderType.OLLAMA,
        "phi3": ProviderType.OLLAMA,
    }

    def __init__(self):
        self.providers: Dict[ProviderType, BaseLLMProvider] = {}
        self.default_model = "gpt-4o-mini"
        self.fallback_chain: List[str] = ["gpt-4o-mini", "claude-3-haiku", "llama3"]
        self._initialized = False

    def initialize(self):
        """Initialize all available providers based on environment"""
        if self._initialized:
            return

        # Initialize OpenAI if API key is present
        if os.getenv("OPENAI_API_KEY"):
            self.providers[ProviderType.OPENAI] = OpenAIProvider(
                ProviderConfig(
                    name="openai",
                    provider_type=ProviderType.OPENAI,
                    models=["gpt-4", "gpt-4-turbo", "gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
                    default_model="gpt-4o-mini"
                )
            )

        # Initialize Anthropic if API key is present
        if os.getenv("ANTHROPIC_API_KEY"):
            self.providers[ProviderType.ANTHROPIC] = AnthropicProvider(
                ProviderConfig(
                    name="anthropic",
                    provider_type=ProviderType.ANTHROPIC,
                    models=["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"],
                    default_model="claude-3-sonnet-20240229"
                )
            )

        # Always try to initialize Ollama (local)
        self.providers[ProviderType.OLLAMA] = OllamaProvider(
            ProviderConfig(
                name="ollama",
                provider_type=ProviderType.OLLAMA,
                models=["llama3", "mistral", "codellama"],
                default_model="llama3"
            )
        )

        self._initialized = True

    def register_provider(self, provider_type: ProviderType, provider: BaseLLMProvider):
        """Register a custom LLM provider"""
        self.providers[provider_type] = provider

    def _get_provider_for_model(self, model: str) -> Optional[BaseLLMProvider]:
        """Get the appropriate provider for a model"""
        provider_type = self.MODEL_PROVIDERS.get(model)
        if provider_type and provider_type in self.providers:
            return self.providers[provider_type]
        
        # Check if model contains provider hints
        model_lower = model.lower()
        if "gpt" in model_lower:
            return self.providers.get(ProviderType.OPENAI)
        elif "claude" in model_lower:
            return self.providers.get(ProviderType.ANTHROPIC)
        elif any(x in model_lower for x in ["llama", "mistral", "phi", "codellama"]):
            return self.providers.get(ProviderType.OLLAMA)
        
        return None

    async def run(
        self,
        model_id: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        use_fallback: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Run an LLM completion request.
        
        Args:
            model_id: The model identifier
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            use_fallback: Whether to try fallback models on failure
            
        Returns:
            Response dict with model output and metadata
        """
        self.initialize()

        # Convert dict messages to Message objects
        msg_objects = [Message(role=m["role"], content=m["content"]) for m in messages]

        # Try primary model
        models_to_try = [model_id]
        if use_fallback:
            models_to_try.extend([m for m in self.fallback_chain if m != model_id])

        last_error = None
        for model in models_to_try:
            provider = self._get_provider_for_model(model)
            if not provider:
                continue

            try:
                response = await provider.complete(
                    messages=msg_objects,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
                return {
                    "model": response.model,
                    "content": response.content,
                    "usage": response.usage,
                    "finish_reason": response.finish_reason,
                    "metadata": response.metadata,
                    "status": "success"
                }
            except Exception as e:
                last_error = str(e)
                continue

        return {
            "model": model_id,
            "content": "",
            "error": last_error or "No available provider for model",
            "status": "error"
        }

    async def stream(
        self,
        model_id: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream an LLM completion request.
        Yields response chunks as they arrive.
        """
        self.initialize()

        msg_objects = [Message(role=m["role"], content=m["content"]) for m in messages]
        provider = self._get_provider_for_model(model_id)

        if not provider:
            yield {"chunk": "", "error": "No provider available", "done": True}
            return

        try:
            async for chunk in provider.stream(
                messages=msg_objects,
                model=model_id,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            ):
                yield {"chunk": chunk, "done": False}
            yield {"chunk": "", "done": True}
        except Exception as e:
            yield {"chunk": "", "error": str(e), "done": True}

    def list_models(self) -> List[Dict[str, Any]]:
        """List all available models with their providers"""
        self.initialize()
        
        models = []
        for model, provider_type in self.MODEL_PROVIDERS.items():
            if provider_type in self.providers:
                models.append({
                    "model": model,
                    "provider": provider_type.value,
                    "available": True
                })
        return models

    def list_providers(self) -> List[str]:
        """List all registered providers"""
        self.initialize()
        return [p.value for p in self.providers.keys()]

    async def close(self):
        """Close all provider connections"""
        for provider in self.providers.values():
            await provider.close()


# Singleton instance
llm_router = LLMRouter()
