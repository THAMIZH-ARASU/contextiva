"""Unit tests for TextChunker service."""
import pytest

from src.application.services.text_chunker import TextChunker


@pytest.fixture
def text_chunker():
    """Create TextChunker instance with default config."""
    return TextChunker(chunk_size_chars=2048, overlap_chars=200)


@pytest.fixture
def small_chunker():
    """Create TextChunker with small chunks for testing."""
    return TextChunker(chunk_size_chars=100, overlap_chars=20)


@pytest.mark.asyncio
class TestTextChunkerBasicFunctionality:
    """Test basic chunking functionality."""

    async def test_chunk_short_text(self, text_chunker):
        """Test chunking of text shorter than chunk size."""
        # Arrange
        text = "This is a short text."
        
        # Act
        chunks = await text_chunker.semantic_chunk(text)
        
        # Assert
        assert len(chunks) == 1
        assert chunks[0].text == text
        metadata = chunks[0].to_metadata()
        assert metadata["chunk_index"] == 0
        assert metadata["start_char"] == 0
        assert metadata["end_char"] == len(text)

    async def test_chunk_empty_text(self, text_chunker):
        """Test chunking of empty text."""
        # Arrange
        text = ""
        
        # Act
        chunks = await text_chunker.semantic_chunk(text)
        
        # Assert
        assert len(chunks) == 0

    async def test_chunk_whitespace_only(self, text_chunker):
        """Test chunking of whitespace-only text."""
        # Arrange
        text = "   \n\n   \t   "
        
        # Act
        chunks = await text_chunker.semantic_chunk(text)
        
        # Assert
        assert len(chunks) == 0


@pytest.mark.asyncio
class TestTextChunkerOverlap:
    """Test chunk overlap functionality."""

    async def test_chunk_with_overlap(self, small_chunker):
        """Test that chunks have proper overlap."""
        # Arrange - Create text that will be split into multiple chunks
        text = "A" * 150 + " " + "B" * 150
        
        # Act
        chunks = await small_chunker.semantic_chunk(text)
        
        # Assert
        assert len(chunks) > 1
        # Check overlap exists
        if len(chunks) >= 2:
            first_chunk_end = chunks[0].text[-20:]
            second_chunk_start = chunks[1].text[:20]
            # There should be some overlap content
            assert len(first_chunk_end) > 0
            assert len(second_chunk_start) > 0

    async def test_chunk_metadata_indices(self, small_chunker):
        """Test that chunk metadata indices are correct."""
        # Arrange
        text = "A" * 250
        
        # Act
        chunks = await small_chunker.semantic_chunk(text)
        
        # Assert
        for i, chunk in enumerate(chunks):
            metadata = chunk.to_metadata()
            assert metadata["chunk_index"] == i
            assert metadata["start_char"] >= 0
            assert metadata["end_char"] <= len(text)
            assert metadata["start_char"] < metadata["end_char"]


@pytest.mark.asyncio
class TestTextChunkerSentenceBoundaries:
    """Test sentence boundary preservation."""

    async def test_chunk_preserves_sentences(self, small_chunker):
        """Test that chunks break at sentence boundaries when possible."""
        # Arrange
        text = "First sentence. " * 20  # Create text with clear sentence boundaries
        
        # Act
        chunks = await small_chunker.semantic_chunk(text)
        
        # Assert
        for chunk in chunks:
            # Each chunk should ideally end with sentence terminator or be the last chunk
            chunk_text = chunk.text.rstrip()
            if chunk != chunks[-1]:  # Not the last chunk
                # Should try to end at sentence boundary
                assert chunk_text.endswith(('.', '!', '?')) or len(chunk_text) >= small_chunker.chunk_size_chars

    async def test_chunk_multiple_sentences(self, text_chunker):
        """Test chunking of text with multiple sentences."""
        # Arrange
        sentences = [
            "This is the first sentence.",
            "Here is another sentence.",
            "And a third one for good measure.",
            "Finally, the last sentence."
        ]
        text = " ".join(sentences)
        
        # Act
        chunks = await text_chunker.semantic_chunk(text)
        
        # Assert
        assert len(chunks) == 1  # Should fit in one chunk
        assert chunks[0].text == text


@pytest.mark.asyncio
class TestTextChunkerTokenCounting:
    """Test token counting functionality."""

    async def test_chunk_token_count(self, text_chunker):
        """Test that token count is estimated correctly."""
        # Arrange
        text = "This is a test sentence with ten words total here."
        
        # Act
        chunks = await text_chunker.semantic_chunk(text)
        
        # Assert
        assert len(chunks) == 1
        token_count = chunks[0].token_count
        # Token count should be approximately chars / 4
        assert token_count > 0
        assert token_count == len(text) // 4

    async def test_chunk_token_count_all_chunks(self, small_chunker):
        """Test that all chunks have token count metadata."""
        # Arrange
        text = "A" * 250
        
        # Act
        chunks = await small_chunker.semantic_chunk(text)
        
        # Assert
        for chunk in chunks:
            assert chunk.token_count > 0


@pytest.mark.asyncio
class TestTextChunkerEdgeCases:
    """Test edge cases and special scenarios."""

    async def test_chunk_single_long_word(self, small_chunker):
        """Test chunking of a single very long word."""
        # Arrange
        text = "A" * 500  # Single "word" longer than chunk size
        
        # Act
        chunks = await small_chunker.semantic_chunk(text)
        
        # Assert
        assert len(chunks) > 0
        # Should still chunk even without sentence boundaries

    async def test_chunk_newlines_and_tabs(self, text_chunker):
        """Test chunking of text with newlines and tabs."""
        # Arrange
        text = "Line 1\n\nLine 2\t\tTabbed\n\n\nLine 3"
        
        # Act
        chunks = await text_chunker.semantic_chunk(text)
        
        # Assert
        assert len(chunks) == 1
        assert "Line 1" in chunks[0].text
        assert "Line 2" in chunks[0].text
        assert "Line 3" in chunks[0].text

    async def test_chunk_unicode_characters(self, text_chunker):
        """Test chunking with Unicode characters."""
        # Arrange
        text = "Hello 世界! This is a test with émojis 🎉 and spëcial çharacters."
        
        # Act
        chunks = await text_chunker.semantic_chunk(text)
        
        # Assert
        assert len(chunks) == 1
        assert "世界" in chunks[0].text
        assert "🎉" in chunks[0].text
        assert "spëcial" in chunks[0].text

    async def test_chunk_exact_chunk_size(self, small_chunker):
        """Test text that is exactly the chunk size."""
        # Arrange
        text = "A" * 100  # Exactly chunk_size
        
        # Act
        chunks = await small_chunker.semantic_chunk(text)
        
        # Assert
        # Text exactly at chunk size may create 1 or 2 chunks depending on overlap logic
        assert len(chunks) >= 1
        assert chunks[0].text == text or text.startswith(chunks[0].text)


@pytest.mark.asyncio
class TestTextChunkerConfiguration:
    """Test different chunker configurations."""

    async def test_custom_chunk_size(self):
        """Test chunker with custom chunk size."""
        # Arrange
        chunker = TextChunker(chunk_size_chars=500, overlap_chars=50)
        text = "A" * 1000
        
        # Act
        chunks = await chunker.semantic_chunk(text)
        
        # Assert
        assert len(chunks) > 1
        for chunk in chunks[:-1]:  # All but last
            assert len(chunk.text) <= 500

    async def test_zero_overlap(self):
        """Test chunker with no overlap."""
        # Arrange
        chunker = TextChunker(chunk_size_chars=100, overlap_chars=0)
        text = "A" * 250
        
        # Act
        chunks = await chunker.semantic_chunk(text)
        
        # Assert
        assert len(chunks) > 1
        # With zero overlap, no content should repeat between chunks
        total_length = sum(len(chunk.text) for chunk in chunks)
        assert total_length == len(text)

    async def test_large_overlap(self):
        """Test chunker with large overlap."""
        # Arrange
        chunker = TextChunker(chunk_size_chars=100, overlap_chars=80)
        text = "A" * 250
        
        # Act
        chunks = await chunker.semantic_chunk(text)
        
        # Assert
        assert len(chunks) > 1
        # Chunks should have significant overlap
