"""OpenAI LLM and embedding provider implementation."""

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


class OpenAIProvider(ILLMProvider):
    """OpenAI implementation of the LLM provider interface.
    
    This provider uses OpenAI's API for both embeddings and chat completions.
    Supports streaming completions for real-time responses.
    
    API Documentation: https://platform.openai.com/docs
    """

    BASE_URL = "https://api.openai.com/v1"

    def __init__(self, settings: LLMSettings) -> None:
        """Initialize the OpenAI provider.
        
        Args:
            settings: LLM configuration settings containing API key and model names.
        
        Raises:
            ValueError: If OpenAI API key is not configured.
        """
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key is required but not configured in settings")

        self.settings = settings
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(60.0, connect=10.0),  # 60s for embeddings, 10s to connect
        )
        logger.info("OpenAI provider initialized with model: %s", settings.default_llm_model)

    async def embed_text(self, text: str, model: str | None = None) -> list[float]:
        """Generate embeddings using OpenAI's embeddings API.
        
        Args:
            text: The text to embed.
            model: Optional model name. Defaults to settings.default_embedding_model.
        
        Returns:
            A list of floats representing the embedding vector (1536 dimensions
            for text-embedding-3-small).
        
        Raises:
            LLMAuthenticationError: If API key is invalid (401).
            LLMRateLimitError: If rate limit is exceeded (429).
            LLMConnectionError: If network connection fails.
            LLMProviderError: For other API errors.
        """
        embedding_model = model or self.settings.default_embedding_model

        try:
            response = await self._client.post(
                "/embeddings",
                json={
                    "input": text,
                    "model": embedding_model,
                },
            )

            if response.status_code == 401 or response.status_code == 403:
                raise LLMAuthenticationError(
                    f"OpenAI authentication failed: {response.status_code} {response.text}"
                )
            elif response.status_code == 429:
                raise LLMRateLimitError(
                    f"OpenAI rate limit exceeded: {response.text}"
                )
            elif response.status_code != 200:
                raise LLMProviderError(
                    f"OpenAI API error: {response.status_code} {response.text}"
                )

            data = response.json()
            embedding = data["data"][0]["embedding"]
            logger.debug(
                "Generated embedding for text (length: %d chars) using model: %s",
                len(text),
                embedding_model,
            )
            return embedding

        except httpx.RequestError as e:
            logger.error("OpenAI connection error: %s", str(e))
            raise LLMConnectionError(f"Failed to connect to OpenAI API: {str(e)}") from e
        except (LLMAuthenticationError, LLMRateLimitError, LLMProviderError):
            raise
        except Exception as e:
            logger.error("Unexpected error calling OpenAI embeddings API: %s", str(e))
            raise LLMProviderError(f"Unexpected error: {str(e)}") from e

    async def generate_completion(
        self, messages: list[dict], model: str | None = None, **kwargs
    ) -> str:
        """Generate a chat completion using OpenAI's chat completions API.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            model: Optional model name. Defaults to settings.default_llm_model.
            **kwargs: Additional parameters like temperature, max_tokens, etc.
        
        Returns:
            The generated completion text as a string.
        
        Raises:
            LLMAuthenticationError: If API key is invalid (401).
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
                timeout=httpx.Timeout(30.0, connect=10.0),  # 30s for completions
            )

            if response.status_code == 401 or response.status_code == 403:
                raise LLMAuthenticationError(
                    f"OpenAI authentication failed: {response.status_code} {response.text}"
                )
            elif response.status_code == 429:
                raise LLMRateLimitError(
                    f"OpenAI rate limit exceeded: {response.text}"
                )
            elif response.status_code != 200:
                raise LLMProviderError(
                    f"OpenAI API error: {response.status_code} {response.text}"
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
            logger.error("OpenAI connection error: %s", str(e))
            raise LLMConnectionError(f"Failed to connect to OpenAI API: {str(e)}") from e
        except (LLMAuthenticationError, LLMRateLimitError, LLMProviderError):
            raise
        except Exception as e:
            logger.error("Unexpected error calling OpenAI chat completions API: %s", str(e))
            raise LLMProviderError(f"Unexpected error: {str(e)}") from e

    async def generate_completion_stream(
        self, messages: list[dict], model: str | None = None, **kwargs
    ) -> AsyncIterator[str]:
        """Generate a streaming chat completion using OpenAI's streaming API.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            model: Optional model name. Defaults to settings.default_llm_model.
            **kwargs: Additional parameters like temperature, max_tokens, etc.
        
        Yields:
            Chunks of the completion text as strings.
        
        Raises:
            LLMAuthenticationError: If API key is invalid (401).
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
                timeout=httpx.Timeout(30.0, connect=10.0),
            ) as response:
                if response.status_code == 401 or response.status_code == 403:
                    error_text = await response.aread()
                    raise LLMAuthenticationError(
                        f"OpenAI authentication failed: {response.status_code} {error_text.decode()}"
                    )
                elif response.status_code == 429:
                    error_text = await response.aread()
                    raise LLMRateLimitError(
                        f"OpenAI rate limit exceeded: {error_text.decode()}"
                    )
                elif response.status_code != 200:
                    error_text = await response.aread()
                    raise LLMProviderError(
                        f"OpenAI API error: {response.status_code} {error_text.decode()}"
                    )

                logger.debug(
                    "Started streaming completion (messages: %d) using model: %s",
                    len(messages),
                    llm_model,
                )

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix
                        if data_str == "[DONE]":
                            break

                        import json
                        try:
                            data = json.loads(data_str)
                            delta = data["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                        except json.JSONDecodeError:
                            continue  # Skip malformed lines

        except httpx.RequestError as e:
            logger.error("OpenAI connection error during streaming: %s", str(e))
            raise LLMConnectionError(f"Failed to connect to OpenAI API: {str(e)}") from e
        except (LLMAuthenticationError, LLMRateLimitError, LLMProviderError):
            raise
        except Exception as e:
            logger.error("Unexpected error during OpenAI streaming: %s", str(e))
            raise LLMProviderError(f"Unexpected error: {str(e)}") from e

    async def close(self) -> None:
        """Close the HTTP client and release resources."""
        await self._client.aclose()
        logger.debug("OpenAI provider client closed")
