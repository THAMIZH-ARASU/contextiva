"""Unit tests for KnowledgeItem domain model."""

import pytest
from datetime import datetime
from uuid import uuid4

from src.domain.models.knowledge import KnowledgeItem


class TestKnowledgeItem:
    """Test suite for KnowledgeItem entity."""

    def test_create_valid_knowledge_item(self):
        """Test creating a valid knowledge item."""
        # Arrange
        item_id = uuid4()
        document_id = uuid4()
        embedding = [0.1] * 1536  # 1536-dimensional embedding
        metadata = {"source": "page 1", "chunk_size": 512}
        now = datetime.utcnow()

        # Act
        item = KnowledgeItem(
            id=item_id,
            document_id=document_id,
            chunk_text="This is a test chunk of text.",
            chunk_index=0,
            embedding=embedding,
            metadata=metadata,
            created_at=now,
        )

        # Assert
        assert item.id == item_id
        assert item.document_id == document_id
        assert item.chunk_text == "This is a test chunk of text."
        assert item.chunk_index == 0
        assert len(item.embedding) == 1536
        assert item.metadata == metadata
        assert item.created_at == now

    def test_empty_chunk_text_raises_error(self):
        """Test that empty chunk text raises ValueError."""
        with pytest.raises(ValueError, match="Chunk text cannot be empty"):
            KnowledgeItem(
                id=uuid4(),
                document_id=uuid4(),
                chunk_text="",
                chunk_index=0,
                embedding=[0.1] * 1536,
                metadata={},
                created_at=datetime.utcnow(),
            )

    def test_whitespace_only_chunk_text_raises_error(self):
        """Test that whitespace-only chunk text raises ValueError."""
        with pytest.raises(ValueError, match="Chunk text cannot be empty"):
            KnowledgeItem(
                id=uuid4(),
                document_id=uuid4(),
                chunk_text="   ",
                chunk_index=0,
                embedding=[0.1] * 1536,
                metadata={},
                created_at=datetime.utcnow(),
            )

    def test_negative_chunk_index_raises_error(self):
        """Test that negative chunk index raises ValueError."""
        with pytest.raises(ValueError, match="Chunk index must be non-negative"):
            KnowledgeItem(
                id=uuid4(),
                document_id=uuid4(),
                chunk_text="Test chunk",
                chunk_index=-1,
                embedding=[0.1] * 1536,
                metadata={},
                created_at=datetime.utcnow(),
            )

    def test_zero_chunk_index_is_valid(self):
        """Test that zero chunk index is valid."""
        item = KnowledgeItem(
            id=uuid4(),
            document_id=uuid4(),
            chunk_text="Test chunk",
            chunk_index=0,
            embedding=[0.1] * 1536,
            metadata={},
            created_at=datetime.utcnow(),
        )

        assert item.chunk_index == 0

    def test_non_list_embedding_raises_error(self):
        """Test that non-list embedding raises ValueError."""
        with pytest.raises(ValueError, match="Embedding must be a list of floats"):
            KnowledgeItem(
                id=uuid4(),
                document_id=uuid4(),
                chunk_text="Test chunk",
                chunk_index=0,
                embedding="not a list",  # type: ignore
                metadata={},
                created_at=datetime.utcnow(),
            )

    def test_empty_embedding_raises_error(self):
        """Test that empty embedding raises ValueError."""
        with pytest.raises(ValueError, match="Embedding cannot be empty"):
            KnowledgeItem(
                id=uuid4(),
                document_id=uuid4(),
                chunk_text="Test chunk",
                chunk_index=0,
                embedding=[],
                metadata={},
                created_at=datetime.utcnow(),
            )

    def test_non_numeric_embedding_values_raise_error(self):
        """Test that non-numeric embedding values raise ValueError."""
        with pytest.raises(ValueError, match="All embedding values must be numeric"):
            KnowledgeItem(
                id=uuid4(),
                document_id=uuid4(),
                chunk_text="Test chunk",
                chunk_index=0,
                embedding=[0.1, "invalid", 0.3],  # type: ignore
                metadata={},
                created_at=datetime.utcnow(),
            )

    def test_embedding_with_integers_is_valid(self):
        """Test that embedding with integers is valid."""
        item = KnowledgeItem(
            id=uuid4(),
            document_id=uuid4(),
            chunk_text="Test chunk",
            chunk_index=0,
            embedding=[1, 2, 3, 4],  # Integers are valid
            metadata={},
            created_at=datetime.utcnow(),
        )

        assert item.embedding == [1, 2, 3, 4]

    def test_non_dict_metadata_raises_error(self):
        """Test that non-dict metadata raises ValueError."""
        with pytest.raises(ValueError, match="Metadata must be a dictionary"):
            KnowledgeItem(
                id=uuid4(),
                document_id=uuid4(),
                chunk_text="Test chunk",
                chunk_index=0,
                embedding=[0.1] * 1536,
                metadata="not a dict",  # type: ignore
                created_at=datetime.utcnow(),
            )

    def test_empty_metadata_is_valid(self):
        """Test that empty metadata dict is valid."""
        item = KnowledgeItem(
            id=uuid4(),
            document_id=uuid4(),
            chunk_text="Test chunk",
            chunk_index=0,
            embedding=[0.1] * 1536,
            metadata={},
            created_at=datetime.utcnow(),
        )

        assert item.metadata == {}

    def test_metadata_with_complex_structure(self):
        """Test metadata with nested structure."""
        metadata = {
            "source": "document.pdf",
            "page": 10,
            "coordinates": {"x": 100, "y": 200},
            "tags": ["important", "review"],
        }

        item = KnowledgeItem(
            id=uuid4(),
            document_id=uuid4(),
            chunk_text="Test chunk",
            chunk_index=0,
            embedding=[0.1] * 1536,
            metadata=metadata,
            created_at=datetime.utcnow(),
        )

        assert item.metadata == metadata
        assert item.metadata["coordinates"]["x"] == 100

    def test_different_embedding_dimensions(self):
        """Test various embedding dimensions."""
        dimensions = [384, 768, 1536, 3072]

        for dim in dimensions:
            item = KnowledgeItem(
                id=uuid4(),
                document_id=uuid4(),
                chunk_text="Test chunk",
                chunk_index=0,
                embedding=[0.1] * dim,
                metadata={},
                created_at=datetime.utcnow(),
            )

            assert len(item.embedding) == dim
