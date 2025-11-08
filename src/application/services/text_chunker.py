"""Text chunking service for breaking text into semantic segments."""
import re
from typing import Any


class TextChunk:
    """Represents a chunk of text with metadata."""

    def __init__(
        self, text: str, chunk_index: int, start_char: int, end_char: int, token_count: int
    ):
        """
        Initialize a text chunk.

        Args:
            text: The chunk text content
            chunk_index: Index of this chunk in the sequence
            start_char: Starting character position in original text
            end_char: Ending character position in original text
            token_count: Approximate number of tokens (characters/4 for simplicity)
        """
        self.text = text
        self.chunk_index = chunk_index
        self.start_char = start_char
        self.end_char = end_char
        self.token_count = token_count

    def to_metadata(self) -> dict[str, Any]:
        """Convert chunk metadata to dictionary."""
        return {
            "chunk_index": self.chunk_index,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "token_count": self.token_count,
        }


class TextChunker:
    """Service for chunking text into semantic segments."""

    def __init__(
        self,
        chunk_size_chars: int = 2048,  # ~512 tokens (approx 4 chars per token)
        overlap_chars: int = 200,  # ~50 tokens overlap
        preserve_sentences: bool = True,
    ):
        """
        Initialize the text chunker.

        Args:
            chunk_size_chars: Target chunk size in characters
            overlap_chars: Overlap between chunks in characters
            preserve_sentences: Whether to preserve sentence boundaries
        """
        self.chunk_size_chars = chunk_size_chars
        self.overlap_chars = overlap_chars
        self.preserve_sentences = preserve_sentences

    async def semantic_chunk(self, text: str) -> list[TextChunk]:
        """
        Chunk text into semantic segments with overlap.

        Args:
            text: Text to chunk

        Returns:
            List of TextChunk objects with metadata
        """
        if not text or not text.strip():
            return []

        chunks: list[TextChunk] = []
        chunk_index = 0
        start_pos = 0

        while start_pos < len(text):
            # Calculate end position for this chunk
            end_pos = min(start_pos + self.chunk_size_chars, len(text))

            # If preserving sentences and not at end, adjust to sentence boundary
            if self.preserve_sentences and end_pos < len(text):
                end_pos = self._find_sentence_boundary(text, start_pos, end_pos)

            # Extract chunk text
            chunk_text = text[start_pos:end_pos].strip()

            if chunk_text:
                # Estimate token count (rough: 1 token ≈ 4 characters)
                token_count = len(chunk_text) // 4

                chunk = TextChunk(
                    text=chunk_text,
                    chunk_index=chunk_index,
                    start_char=start_pos,
                    end_char=end_pos,
                    token_count=token_count,
                )
                chunks.append(chunk)
                chunk_index += 1

            # Move start position forward, with overlap
            start_pos = end_pos - self.overlap_chars
            if start_pos <= chunks[-1].start_char if chunks else 0:
                # Avoid infinite loop - move forward at least a bit
                start_pos = end_pos

        return chunks

    def _find_sentence_boundary(self, text: str, start: int, ideal_end: int) -> int:
        """
        Find the nearest sentence boundary before the ideal end position.

        Args:
            text: Full text
            start: Start position of chunk
            ideal_end: Ideal end position

        Returns:
            Adjusted end position at sentence boundary
        """
        # Look for sentence ending punctuation: . ! ? followed by space or newline
        chunk_text = text[start:ideal_end]

        # Find all sentence boundaries in the chunk
        sentence_pattern = r'[.!?][\s\n]'
        matches = list(re.finditer(sentence_pattern, chunk_text))

        if matches:
            # Use the last sentence boundary found
            last_match = matches[-1]
            return start + last_match.end()

        # If no sentence boundary found, return ideal end
        return ideal_end
