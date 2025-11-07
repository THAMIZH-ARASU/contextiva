"""OpenRouter LLM provider implementation."""

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


class OpenRouterProvider(ILLMProvider):
    """OpenRouter LLM provider implementation.
    
    OpenRouter provides access to 100+ LLM models through a unified API.
    Uses OpenAI-compatible endpoints.
    
    Note: OpenRouter does not provide embeddings directly. The embed_text
    method raises NotImplementedError.
    
    API Documentation: https://openrouter.ai/docs
    """

    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self, settings: LLMSettings) -> None:
        """Initialize the OpenRouter provider.
        
        Args:
            settings: LLM configuration settings containing API key.
        
        Raises:
            ValueError: If OpenRouter API key is not configured.
        """
        if not settings.openrouter_api_key:
            raise ValueError("OpenRouter API key is required but not configured in settings")

        self.settings = settings
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/yourusername/contextiva",  # Optional but recommended
            },
            timeout=httpx.Timeout(30.0, connect=10.0),
        )
        logger.info("OpenRouter provider initialized with model: %s", settings.default_llm_model)

    async def embed_text(self, text: str, model: str | None = None) -> list[float]:
        """OpenRouter does not provide embeddings directly.
        
        Raises:
            NotImplementedError: Always, as OpenRouter doesn't support embeddings.
        """
        raise NotImplementedError(
            "OpenRouter does not provide embeddings directly. Use OpenAI or another provider for embeddings."
        )

    async def generate_completion(
        self, messages: list[dict], model: str | None = None, **kwargs
    ) -> str:
        """Generate a completion using OpenRouter's chat completions API.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            model: Optional model name. Defaults to settings.default_llm_model.
                  OpenRouter supports 100+ models (e.g., "anthropic/claude-3-haiku").
            **kwargs: Additional parameters like temperature, max_tokens, etc.
        
        Returns:
            The generated completion text as a string.
        
        Raises:
            LLMAuthenticationError: If API key is invalid (401, 403).
            LLMRateLimitError: If rate limit is exceeded (429).
            LLMConnectionError: If network connection fails.
            LLMProviderError: For other API errors.
        """
        llm_model = model or self.settings.default_llm_model

        try:
            response = await self._client.post(
                "/chat/completions",
                json={
                    "model": llm_model,
                    "messages": messages,
                    **kwargs,
                },
            )

            if response.status_code == 401 or response.status_code == 403:
                raise LLMAuthenticationError(
                    f"OpenRouter authentication failed: {response.status_code} {response.text}"
                )
            elif response.status_code == 429:
                raise LLMRateLimitError(
                    f"OpenRouter rate limit exceeded: {response.text}"
                )
            elif response.status_code != 200:
                raise LLMProviderError(
                    f"OpenRouter API error: {response.status_code} {response.text}"
                )

            data = response.json()
            content = data["choices"][0]["message"]["content"]
            logger.debug(
                "Generated completion (messages: %d) using model: %s",
                len(messages),
                llm_model,
            )
            return content

        except httpx.RequestError as e:
            logger.error("OpenRouter connection error: %s", str(e))
            raise LLMConnectionError(f"Failed to connect to OpenRouter API: {str(e)}") from e
        except (LLMAuthenticationError, LLMRateLimitError, LLMProviderError):
            raise
        except Exception as e:
            logger.error("Unexpected error calling OpenRouter chat completions API: %s", str(e))
            raise LLMProviderError(f"Unexpected error: {str(e)}") from e

    async def generate_completion_stream(
        self, messages: list[dict], model: str | None = None, **kwargs
    ) -> AsyncIterator[str]:
        """Generate a streaming completion using OpenRouter's streaming API.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            model: Optional model name. Defaults to settings.default_llm_model.
            **kwargs: Additional parameters like temperature, max_tokens, etc.
        
        Yields:
            Chunks of the completion text as strings.
        
        Raises:
            LLMAuthenticationError: If API key is invalid (401, 403).
            LLMRateLimitError: If rate limit is exceeded (429).
            LLMConnectionError: If network connection fails.
            LLMProviderError: For other API errors.
        """
        llm_model = model or self.settings.default_llm_model

        try:
            async with self._client.stream(
                "POST",
                "/chat/completions",
                json={
                    "model": llm_model,
                    "messages": messages,
                    "stream": True,
                    **kwargs,
                },
            ) as response:
                if response.status_code == 401 or response.status_code == 403:
                    error_text = await response.aread()
                    raise LLMAuthenticationError(
                        f"OpenRouter authentication failed: {response.status_code} {error_text.decode()}"
                    )
                elif response.status_code == 429:
                    error_text = await response.aread()
                    raise LLMRateLimitError(
                        f"OpenRouter rate limit exceeded: {error_text.decode()}"
                    )
                elif response.status_code != 200:
                    error_text = await response.aread()
                    raise LLMProviderError(
                        f"OpenRouter API error: {response.status_code} {error_text.decode()}"
                    )

                logger.debug(
                    "Started streaming completion (messages: %d) using model: %s",
                    len(messages),
                    llm_model,
                )

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break

                        try:
                            data = json.loads(data_str)
                            delta = data["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                        except json.JSONDecodeError:
                            continue

        except httpx.RequestError as e:
            logger.error("OpenRouter connection error during streaming: %s", str(e))
            raise LLMConnectionError(f"Failed to connect to OpenRouter API: {str(e)}") from e
        except (LLMAuthenticationError, LLMRateLimitError, LLMProviderError):
            raise
        except Exception as e:
            logger.error("Unexpected error during OpenRouter streaming: %s", str(e))
            raise LLMProviderError(f"Unexpected error: {str(e)}") from e

    async def close(self) -> None:
        """Close the HTTP client and release resources."""
        await self._client.aclose()
        logger.debug("OpenRouter provider client closed")
