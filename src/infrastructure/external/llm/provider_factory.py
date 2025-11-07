"""Factory for creating and managing LLM provider instances."""

import logging
from typing import Dict

from src.shared.config.settings import LLMSettings, load_settings
from src.shared.utils.errors import UnsupportedProviderError

from .providers.base import ILLMProvider
from .providers.anthropic_provider import AnthropicProvider
from .providers.ollama_provider import OllamaProvider
from .providers.openai_provider import OpenAIProvider
from .providers.openrouter_provider import OpenRouterProvider

logger = logging.getLogger(__name__)


class ProviderFactory:
    """Factory for creating and managing LLM provider instances.
    
    This factory implements the singleton pattern to ensure that provider
    instances are reused across the application, avoiding multiple API
    client initializations.
    
    Supported providers:
    - openai: OpenAI GPT models and embeddings
    - anthropic: Anthropic Claude models (no embeddings)
    - ollama: Local Ollama models
    - openrouter: 100+ models via OpenRouter (no embeddings)
    """

    # Singleton cache for provider instances
    _llm_providers: Dict[str, ILLMProvider] = {}
    _embedding_providers: Dict[str, ILLMProvider] = {}

    @classmethod
    def get_llm_provider(cls, provider_name: str | None = None) -> ILLMProvider:
        """Get or create an LLM provider instance.
        
        Args:
            provider_name: Optional provider name. If None, uses the value
                          from settings.llm.llm_provider. Supported values:
                          "openai", "anthropic", "ollama", "openrouter"
                          (case-insensitive).
        
        Returns:
            An instance of ILLMProvider for the specified provider.
        
        Raises:
            UnsupportedProviderError: If the provider name is not supported.
            ValueError: If provider initialization fails (e.g., missing API key).
        """
        settings = load_settings()
        provider = (provider_name or settings.llm.llm_provider).lower().strip()

        # Check singleton cache first
        if provider in cls._llm_providers:
            logger.debug("Returning cached LLM provider: %s", provider)
            return cls._llm_providers[provider]

        # Create new provider instance
        logger.info("Initializing LLM provider: %s", provider)
        
        if provider == "openai":
            instance = OpenAIProvider(settings.llm)
        elif provider == "anthropic":
            instance = AnthropicProvider(settings.llm)
        elif provider == "ollama":
            instance = OllamaProvider(settings.llm)
        elif provider == "openrouter":
            instance = OpenRouterProvider(settings.llm)
        else:
            raise UnsupportedProviderError(
                f"Unsupported LLM provider: '{provider}'. "
                f"Supported providers: openai, anthropic, ollama, openrouter"
            )

        # Cache the instance
        cls._llm_providers[provider] = instance
        logger.info("LLM provider initialized and cached: %s", provider)
        
        return instance

    @classmethod
    def get_embedding_provider(cls, provider_name: str | None = None) -> ILLMProvider:
        """Get or create an embedding provider instance.
        
        Args:
            provider_name: Optional provider name. If None, uses the value
                          from settings.llm.embedding_provider. Supported values:
                          "openai", "ollama" (case-insensitive).
        
        Returns:
            An instance of ILLMProvider that supports embeddings.
        
        Raises:
            UnsupportedProviderError: If the provider name is not supported
                                     or doesn't support embeddings.
            ValueError: If provider initialization fails (e.g., missing API key).
        """
        settings = load_settings()
        provider = (provider_name or settings.llm.embedding_provider).lower().strip()

        # Check singleton cache first
        if provider in cls._embedding_providers:
            logger.debug("Returning cached embedding provider: %s", provider)
            return cls._embedding_providers[provider]

        # Create new provider instance
        logger.info("Initializing embedding provider: %s", provider)
        
        # Only OpenAI and Ollama support embeddings
        if provider == "openai":
            instance = OpenAIProvider(settings.llm)
        elif provider == "ollama":
            instance = OllamaProvider(settings.llm)
        elif provider in ("anthropic", "openrouter"):
            raise UnsupportedProviderError(
                f"Provider '{provider}' does not support embeddings. "
                f"Use 'openai' or 'ollama' for embeddings."
            )
        else:
            raise UnsupportedProviderError(
                f"Unsupported embedding provider: '{provider}'. "
                f"Supported providers: openai, ollama"
            )

        # Cache the instance
        cls._embedding_providers[provider] = instance
        logger.info("Embedding provider initialized and cached: %s", provider)
        
        return instance

    @classmethod
    async def close_all(cls) -> None:
        """Close all provider instances and clear the cache.
        
        This should be called during application shutdown to properly
        release resources (HTTP clients, connections, etc.).
        """
        logger.info("Closing all LLM provider instances...")
        
        for provider_name, provider in cls._llm_providers.items():
            try:
                await provider.close()
                logger.debug("Closed LLM provider: %s", provider_name)
            except Exception as e:
                logger.error("Error closing LLM provider %s: %s", provider_name, str(e))
        
        for provider_name, provider in cls._embedding_providers.items():
            try:
                await provider.close()
                logger.debug("Closed embedding provider: %s", provider_name)
            except Exception as e:
                logger.error("Error closing embedding provider %s: %s", provider_name, str(e))
        
        cls._llm_providers.clear()
        cls._embedding_providers.clear()
        logger.info("All provider instances closed and cache cleared")

    @classmethod
    def reset(cls) -> None:
        """Reset the factory (clear cache without closing).
        
        This is mainly useful for testing to reset the singleton state
        between tests.
        """
        cls._llm_providers.clear()
        cls._embedding_providers.clear()
        logger.debug("Provider factory cache reset")
