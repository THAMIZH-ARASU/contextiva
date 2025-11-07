"""Ollama local LLM provider implementation."""

import json
import logging
from typing import AsyncIterator

import httpx

from src.shared.config.settings import LLMSettings
from src.shared.utils.errors import (
    LLMConnectionError,
    LLMProviderError,
)

from .base import ILLMProvider

logger = logging.getLogger(__name__)


class OllamaProvider(ILLMProvider):
    """Ollama local LLM provider implementation.
    
    Ollama runs locally and supports various open-source models (llama2,
    mistral, etc.). No authentication is required.
    
    API Documentation: https://ollama.com/
    """

    def __init__(self, settings: LLMSettings) -> None:
        """Initialize the Ollama provider.
        
        Args:
            settings: LLM configuration settings containing Ollama base URL.
        """
        self.settings = settings
        self._client = httpx.AsyncClient(
            base_url=settings.ollama_base_url,
            timeout=httpx.Timeout(60.0, connect=10.0),
        )
        logger.info("Ollama provider initialized at %s", settings.ollama_base_url)

    async def embed_text(self, text: str, model: str | None = None) -> list[float]:
        """Generate embeddings using Ollama's embeddings API.
        
        Args:
            text: The text to embed.
            model: Optional model name. Defaults to settings.default_embedding_model.
        
        Returns:
            A list of floats representing the embedding vector.
        
        Raises:
            LLMConnectionError: If Ollama is not running or connection fails.
            LLMProviderError: For other API errors.
        """
        embedding_model = model or self.settings.default_embedding_model

        try:
            response = await self._client.post(
                "/api/embeddings",
                json={
                    "model": embedding_model,
                    "prompt": text,
                },
            )

            if response.status_code != 200:
                raise LLMProviderError(
                    f"Ollama API error: {response.status_code} {response.text}"
                )

            data = response.json()
            embedding = data["embedding"]
            logger.debug(
                "Generated embedding for text (length: %d chars) using model: %s",
                len(text),
                embedding_model,
            )
            return embedding

        except httpx.ConnectError as e:
            logger.error("Ollama connection error (is Ollama running?): %s", str(e))
            raise LLMConnectionError(
                f"Failed to connect to Ollama at {self.settings.ollama_base_url}. "
                f"Is Ollama running? Error: {str(e)}"
            ) from e
        except httpx.RequestError as e:
            logger.error("Ollama connection error: %s", str(e))
            raise LLMConnectionError(f"Failed to connect to Ollama API: {str(e)}") from e
        except LLMProviderError:
            raise
        except Exception as e:
            logger.error("Unexpected error calling Ollama embeddings API: %s", str(e))
            raise LLMProviderError(f"Unexpected error: {str(e)}") from e

    async def generate_completion(
        self, messages: list[dict], model: str | None = None, **kwargs
    ) -> str:
        """Generate a completion using Ollama's chat API.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            model: Optional model name. Defaults to settings.default_llm_model.
            **kwargs: Additional parameters like temperature, etc.
        
        Returns:
            The generated completion text as a string.
        
        Raises:
            LLMConnectionError: If Ollama is not running or connection fails.
            LLMProviderError: For other API errors.
        """
        llm_model = model or self.settings.default_llm_model

        try:
            response = await self._client.post(
                "/api/chat",
                json={
                    "model": llm_model,
                    "messages": messages,
                    "stream": False,
                    **kwargs,
                },
            )

            if response.status_code != 200:
                raise LLMProviderError(
                    f"Ollama API error: {response.status_code} {response.text}"
                )

            data = response.json()
            content = data["message"]["content"]
            logger.debug(
                "Generated completion (messages: %d) using model: %s",
                len(messages),
                llm_model,
            )
            return content

        except httpx.ConnectError as e:
            logger.error("Ollama connection error (is Ollama running?): %s", str(e))
            raise LLMConnectionError(
                f"Failed to connect to Ollama at {self.settings.ollama_base_url}. "
                f"Is Ollama running? Error: {str(e)}"
            ) from e
        except httpx.RequestError as e:
            logger.error("Ollama connection error: %s", str(e))
            raise LLMConnectionError(f"Failed to connect to Ollama API: {str(e)}") from e
        except LLMProviderError:
            raise
        except Exception as e:
            logger.error("Unexpected error calling Ollama chat API: %s", str(e))
            raise LLMProviderError(f"Unexpected error: {str(e)}") from e

    async def generate_completion_stream(
        self, messages: list[dict], model: str | None = None, **kwargs
    ) -> AsyncIterator[str]:
        """Generate a streaming completion using Ollama's streaming chat API.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            model: Optional model name. Defaults to settings.default_llm_model.
            **kwargs: Additional parameters like temperature, etc.
        
        Yields:
            Chunks of the completion text as strings.
        
        Raises:
            LLMConnectionError: If Ollama is not running or connection fails.
            LLMProviderError: For other API errors.
        """
        llm_model = model or self.settings.default_llm_model

        try:
            async with self._client.stream(
                "POST",
                "/api/chat",
                json={
                    "model": llm_model,
                    "messages": messages,
                    "stream": True,
                    **kwargs,
                },
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise LLMProviderError(
                        f"Ollama API error: {response.status_code} {error_text.decode()}"
                    )

                logger.debug(
                    "Started streaming completion (messages: %d) using model: %s",
                    len(messages),
                    llm_model,
                )

                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if "message" in data:
                                content = data["message"].get("content", "")
                                if content:
                                    yield content
                            if data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue

        except httpx.ConnectError as e:
            logger.error("Ollama connection error during streaming (is Ollama running?): %s", str(e))
            raise LLMConnectionError(
                f"Failed to connect to Ollama at {self.settings.ollama_base_url}. "
                f"Is Ollama running? Error: {str(e)}"
            ) from e
        except httpx.RequestError as e:
            logger.error("Ollama connection error during streaming: %s", str(e))
            raise LLMConnectionError(f"Failed to connect to Ollama API: {str(e)}") from e
        except LLMProviderError:
            raise
        except Exception as e:
            logger.error("Unexpected error during Ollama streaming: %s", str(e))
            raise LLMProviderError(f"Unexpected error: {str(e)}") from e

    async def close(self) -> None:
        """Close the HTTP client and release resources."""
        await self._client.aclose()
        logger.debug("Ollama provider client closed")
