"""Integration tests for ProviderFactory."""

import pytest
import os
from unittest.mock import patch
from src.infrastructure.external.llm.provider_factory import ProviderFactory
from src.infrastructure.external.llm.providers.openai_provider import OpenAIProvider
from src.infrastructure.external.llm.providers.ollama_provider import OllamaProvider
from src.shared.utils.errors import UnsupportedProviderError


@pytest.fixture(autouse=True)
async def cleanup_factory():
    """Reset factory state before/after each test."""
    ProviderFactory.reset()
    yield
    await ProviderFactory.close_all()
    ProviderFactory.reset()


@pytest.mark.asyncio
class TestProviderFactory:
    """Test suite for ProviderFactory."""

    async def test_get_llm_provider_openai(self):
        """Test getting OpenAI LLM provider."""
        # Arrange - Set environment to use OpenAI
        with patch.dict(os.environ, {
            'LLM_PROVIDER': 'openai',
            'LLM_OPENAI_API_KEY': 'test-key'
        }):
            # Act
            provider = ProviderFactory.get_llm_provider()
            
            # Assert
            assert isinstance(provider, OpenAIProvider)

    async def test_get_llm_provider_explicit_name(self):
        """Test getting provider with explicit name."""
        # Arrange
        with patch.dict(os.environ, {
            'LLM_OPENAI_API_KEY': 'test-key'
        }):
            # Act
            provider = ProviderFactory.get_llm_provider("openai")
            
            # Assert
            assert isinstance(provider, OpenAIProvider)

    async def test_get_llm_provider_singleton(self):
        """Test singleton pattern returns same instance."""
        # Arrange
        with patch.dict(os.environ, {
            'LLM_PROVIDER': 'ollama'
        }):
            # Act
            provider1 = ProviderFactory.get_llm_provider()
            provider2 = ProviderFactory.get_llm_provider()
            
            # Assert
            assert provider1 is provider2
            assert isinstance(provider1, OllamaProvider)

    async def test_get_llm_provider_unsupported(self):
        """Test error for unsupported provider."""
        # Act & Assert
        with pytest.raises(UnsupportedProviderError):
            ProviderFactory.get_llm_provider("unsupported-provider")

    async def test_close_all_providers(self):
        """Test closing all cached providers."""
        # Arrange
        with patch.dict(os.environ, {
            'LLM_PROVIDER': 'ollama'
        }):
            provider = ProviderFactory.get_llm_provider()
            
            # Act
            await ProviderFactory.close_all()
            
            # Assert
            assert provider._client.is_closed

    async def test_reset_clears_cache(self):
        """Test reset clears cache without closing providers."""
        # Arrange
        with patch.dict(os.environ, {
            'LLM_PROVIDER': 'ollama'
        }):
            provider1 = ProviderFactory.get_llm_provider()
            
            # Act
            ProviderFactory.reset()
            provider2 = ProviderFactory.get_llm_provider()
            
            # Assert
            assert provider1 is not provider2
            assert not provider1._client.is_closed  # Not closed by reset
            
            # Clean up
            await provider1.close()

    async def test_get_embedding_provider_unsupported(self):
        """Test that Anthropic doesn't support embeddings."""
        # Arrange
        with patch.dict(os.environ, {
            'LLM_EMBEDDING_PROVIDER': 'anthropic'
        }):
            # Act & Assert
            with pytest.raises(UnsupportedProviderError, match="embedding"):
                ProviderFactory.get_embedding_provider()
