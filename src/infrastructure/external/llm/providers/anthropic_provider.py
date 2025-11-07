"""Anthropic LLM provider implementation."""

import json
import logging
from typing import AsyncIterator

import httpx

from src.shared.config.settings import LLMSettings
from src.shared.utils.errors import (
    LLMAuthenticationError,
    LLMConnectionError,
    LLMProviderError,
    LLMRateLimitError,
)

from .base import ILLMProvider

logger = logging.getLogger(__name__)


class AnthropicProvider(ILLMProvider):
    """Anthropic Claude implementation of the LLM provider interface.
    
    Note: Anthropic does not provide embeddings. For embeddings, use OpenAI
    or another provider. The embed_text method raises NotImplementedError.
    
    API Documentation: https://docs.anthropic.com/
    """

    BASE_URL = "https://api.anthropic.com/v1"
    ANTHROPIC_VERSION = "2023-06-01"

    def __init__(self, settings: LLMSettings) -> None:
        """Initialize the Anthropic provider.
        
        Args:
            settings: LLM configuration settings containing API key.
        
        Raises:
            ValueError: If Anthropic API key is not configured.
        """
        if not settings.anthropic_api_key:
            raise ValueError("Anthropic API key is required but not configured in settings")

        self.settings = settings
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": self.ANTHROPIC_VERSION,
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(30.0, connect=10.0),
        )
        logger.info("Anthropic provider initialized with model: %s", settings.default_llm_model)

    async def embed_text(self, text: str, model: str | None = None) -> list[float]:
        """Anthropic does not provide embeddings.
        
        Raises:
            NotImplementedError: Always, as Anthropic doesn't support embeddings.
        """
        raise NotImplementedError(
            "Anthropic does not provide embeddings. Use OpenAI or another provider for embeddings."
        )

    async def generate_completion(
        self, messages: list[dict], model: str | None = None, **kwargs
    ) -> str:
        """Generate a completion using Anthropic's messages API.
        
        Args:
            messages: List of message dicts. Note: Anthropic requires a different
                     format than OpenAI. System messages should be extracted.
            model: Optional model name. Defaults to settings.default_llm_model
                  (e.g., claude-3-haiku-20240307).
            **kwargs: Additional parameters like max_tokens, temperature, etc.
        
        Returns:
            The generated completion text as a string.
        
        Raises:
            LLMAuthenticationError: If API key is invalid (401, 403).
            LLMRateLimitError: If rate limit is exceeded (429).
            LLMConnectionError: If network connection fails.
            LLMProviderError: For other API errors.
        """
        llm_model = model or self.settings.default_llm_model

        # Extract system message if present (Anthropic has separate system parameter)
        system_message = None
        anthropic_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                anthropic_messages.append(msg)

        payload = {
            "model": llm_model,
            "messages": anthropic_messages,
            "max_tokens": kwargs.pop("max_tokens", 1024),
            **kwargs,
        }
        
        if system_message:
            payload["system"] = system_message

        try:
            response = await self._client.post("/messages", json=payload)

            if response.status_code == 401 or response.status_code == 403:
                raise LLMAuthenticationError(
                    f"Anthropic authentication failed: {response.status_code} {response.text}"
                )
            elif response.status_code == 429:
                raise LLMRateLimitError(
                    f"Anthropic rate limit exceeded: {response.text}"
                )
            elif response.status_code != 200:
                raise LLMProviderError(
                    f"Anthropic API error: {response.status_code} {response.text}"
                )

            data = response.json()
            content = data["content"][0]["text"]
            logger.debug(
                "Generated completion (messages: %d) using model: %s",
                len(messages),
                llm_model,
            )
            return content

        except httpx.RequestError as e:
            logger.error("Anthropic connection error: %s", str(e))
            raise LLMConnectionError(f"Failed to connect to Anthropic API: {str(e)}") from e
        except (LLMAuthenticationError, LLMRateLimitError, LLMProviderError):
            raise
        except Exception as e:
            logger.error("Unexpected error calling Anthropic messages API: %s", str(e))
            raise LLMProviderError(f"Unexpected error: {str(e)}") from e

    async def generate_completion_stream(
        self, messages: list[dict], model: str | None = None, **kwargs
    ) -> AsyncIterator[str]:
        """Generate a streaming completion using Anthropic's streaming API.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            model: Optional model name. Defaults to settings.default_llm_model.
            **kwargs: Additional parameters like max_tokens, temperature, etc.
        
        Yields:
            Chunks of the completion text as strings.
        
        Raises:
            LLMAuthenticationError: If API key is invalid (401, 403).
            LLMRateLimitError: If rate limit is exceeded (429).
            LLMConnectionError: If network connection fails.
            LLMProviderError: For other API errors.
        """
        llm_model = model or self.settings.default_llm_model

        # Extract system message if present
        system_message = None
        anthropic_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                anthropic_messages.append(msg)

        payload = {
            "model": llm_model,
            "messages": anthropic_messages,
            "max_tokens": kwargs.pop("max_tokens", 1024),
            "stream": True,
            **kwargs,
        }
        
        if system_message:
            payload["system"] = system_message

        try:
            async with self._client.stream("POST", "/messages", json=payload) as response:
                if response.status_code == 401 or response.status_code == 403:
                    error_text = await response.aread()
                    raise LLMAuthenticationError(
                        f"Anthropic authentication failed: {response.status_code} {error_text.decode()}"
                    )
                elif response.status_code == 429:
                    error_text = await response.aread()
                    raise LLMRateLimitError(
                        f"Anthropic rate limit exceeded: {error_text.decode()}"
                    )
                elif response.status_code != 200:
                    error_text = await response.aread()
                    raise LLMProviderError(
                        f"Anthropic API error: {response.status_code} {error_text.decode()}"
                    )

                logger.debug(
                    "Started streaming completion (messages: %d) using model: %s",
                    len(messages),
                    llm_model,
                )

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        
                        try:
                            data = json.loads(data_str)
                            if data.get("type") == "content_block_delta":
                                delta = data.get("delta", {})
                                if delta.get("type") == "text_delta":
                                    yield delta.get("text", "")
                        except json.JSONDecodeError:
                            continue

        except httpx.RequestError as e:
            logger.error("Anthropic connection error during streaming: %s", str(e))
            raise LLMConnectionError(f"Failed to connect to Anthropic API: {str(e)}") from e
        except (LLMAuthenticationError, LLMRateLimitError, LLMProviderError):
            raise
        except Exception as e:
            logger.error("Unexpected error during Anthropic streaming: %s", str(e))
            raise LLMProviderError(f"Unexpected error: {str(e)}") from e

    async def close(self) -> None:
        """Close the HTTP client and release resources."""
        await self._client.aclose()
        logger.debug("Anthropic provider client closed")
