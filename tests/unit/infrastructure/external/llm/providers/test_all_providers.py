"""Comprehensive unit tests for all LLM providers."""

import pytest
from src.infrastructure.external.llm.providers.openai_provider import OpenAIProvider
from src.infrastructure.external.llm.providers.anthropic_provider import AnthropicProvider
from src.infrastructure.external.llm.providers.ollama_provider import OllamaProvider
from src.infrastructure.external.llm.providers.openrouter_provider import OpenRouterProvider
from src.shared.config.settings import LLMSettings


@pytest.fixture
def openai_settings():
    return LLMSettings(
        llm_provider="openai",
        embedding_provider="openai",
        openai_api_key="test-key",
        anthropic_api_key=None,
        ollama_base_url="http://localhost:11434",
        openrouter_api_key=None,
        default_llm_model="gpt-4o-mini",
        default_embedding_model="text-embedding-3-small",
    )


@pytest.fixture
def anthropic_settings():
    return LLMSettings(
        llm_provider="anthropic",
        embedding_provider="openai",
        openai_api_key="test-key",
        anthropic_api_key="test-key",
        ollama_base_url="http://localhost:11434",
        openrouter_api_key=None,
        default_llm_model="claude-3-haiku-20240307",
        default_embedding_model="text-embedding-3-small",
    )


@pytest.fixture
def ollama_settings():
    return LLMSettings(
        llm_provider="ollama",
        embedding_provider="ollama",
        openai_api_key=None,
        anthropic_api_key=None,
        ollama_base_url="http://localhost:11434",
        openrouter_api_key=None,
        default_llm_model="llama2",
        default_embedding_model="nomic-embed-text",
    )


@pytest.fixture
def openrouter_settings():
    return LLMSettings(
        llm_provider="openrouter",
        embedding_provider="openai",
        openai_api_key="test-key",
        anthropic_api_key=None,
        ollama_base_url="http://localhost:11434",
        openrouter_api_key="test-key",
        default_llm_model="openai/gpt-3.5-turbo",
        default_embedding_model="text-embedding-3-small",
    )


class TestOpenAIProvider:
    """Test suite for OpenAI provider."""

    async def test_initialization_success(self, openai_settings):
        """Test successful provider initialization."""
        provider = OpenAIProvider(openai_settings)
        assert provider.settings == openai_settings
        assert provider._client is not None
        await provider.close()

    async def test_initialization_without_api_key(self):
        """Test that initialization fails without API key."""
        settings = LLMSettings(
            llm_provider="openai",
            embedding_provider="openai",
            openai_api_key=None,
            anthropic_api_key=None,
            ollama_base_url="http://localhost:11434",
            openrouter_api_key=None,
            default_llm_model="gpt-4o-mini",
            default_embedding_model="text-embedding-3-small",
        )
        with pytest.raises(ValueError, match="API key"):
            OpenAIProvider(settings)

    async def test_close(self, openai_settings):
        """Test provider cleanup."""
        provider = OpenAIProvider(openai_settings)
        await provider.close()
        assert provider._client.is_closed


class TestAnthropicProvider:
    """Test suite for Anthropic provider."""

    async def test_initialization_success(self, anthropic_settings):
        """Test successful provider initialization."""
        provider = AnthropicProvider(anthropic_settings)
        assert provider.settings == anthropic_settings
        assert provider._client is not None
        await provider.close()

    async def test_initialization_without_api_key(self):
        """Test that initialization fails without API key."""
        settings = LLMSettings(
            llm_provider="anthropic",
            embedding_provider="openai",
            openai_api_key="test",
            anthropic_api_key=None,
            ollama_base_url="http://localhost:11434",
            openrouter_api_key=None,
            default_llm_model="claude-3-haiku-20240307",
            default_embedding_model="text-embedding-3-small",
        )
        with pytest.raises(ValueError, match="API key"):
            AnthropicProvider(settings)

    async def test_embed_text_not_supported(self, anthropic_settings):
        """Test that embeddings raise NotImplementedError."""
        provider = AnthropicProvider(anthropic_settings)
        with pytest.raises(NotImplementedError, match="embeddings"):
            await provider.embed_text("test")
        await provider.close()

    async def test_close(self, anthropic_settings):
        """Test provider cleanup."""
        provider = AnthropicProvider(anthropic_settings)
        await provider.close()
        assert provider._client.is_closed


class TestOllamaProvider:
    """Test suite for Ollama provider."""

    async def test_initialization_success(self, ollama_settings):
        """Test successful provider initialization."""
        provider = OllamaProvider(ollama_settings)
        assert provider.settings == ollama_settings
        assert provider._client is not None
        await provider.close()

    async def test_close(self, ollama_settings):
        """Test provider cleanup."""
        provider = OllamaProvider(ollama_settings)
        await provider.close()
        assert provider._client.is_closed


class TestOpenRouterProvider:
    """Test suite for OpenRouter provider."""

    async def test_initialization_success(self, openrouter_settings):
        """Test successful provider initialization."""
        provider = OpenRouterProvider(openrouter_settings)
        assert provider.settings == openrouter_settings
        assert provider._client is not None
        await provider.close()

    async def test_initialization_without_api_key(self):
        """Test that initialization fails without API key."""
        settings = LLMSettings(
            llm_provider="openrouter",
            embedding_provider="openai",
            openai_api_key="test",
            anthropic_api_key=None,
            ollama_base_url="http://localhost:11434",
            openrouter_api_key=None,
            default_llm_model="openai/gpt-3.5-turbo",
            default_embedding_model="text-embedding-3-small",
        )
        with pytest.raises(ValueError, match="API key"):
            OpenRouterProvider(settings)

    async def test_embed_text_not_supported(self, openrouter_settings):
        """Test that embeddings raise NotImplementedError."""
        provider = OpenRouterProvider(openrouter_settings)
        with pytest.raises(NotImplementedError, match="embedding"):
            await provider.embed_text("test")
        await provider.close()

    async def test_close(self, openrouter_settings):
        """Test provider cleanup."""
        provider = OpenRouterProvider(openrouter_settings)
        await provider.close()
        assert provider._client.is_closed
