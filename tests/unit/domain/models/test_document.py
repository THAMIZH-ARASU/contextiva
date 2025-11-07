"""Unit tests for Document domain model."""

import pytest
from datetime import datetime
from uuid import uuid4

from src.domain.models.document import Document, DocumentType


class TestDocument:
    """Test suite for Document entity."""

    def test_create_valid_document(self):
        """Test creating a valid document."""
        # Arrange
        doc_id = uuid4()
        project_id = uuid4()
        now = datetime.utcnow()
        content_hash = "a" * 64  # Valid SHA-256 hash

        # Act
        doc = Document(
            id=doc_id,
            project_id=project_id,
            name="README.md",
            type=DocumentType.MARKDOWN,
            version="v1.0.0",
            content_hash=content_hash,
            created_at=now,
            updated_at=now,
        )

        # Assert
        assert doc.id == doc_id
        assert doc.project_id == project_id
        assert doc.name == "README.md"
        assert doc.type == DocumentType.MARKDOWN
        assert doc.version == "v1.0.0"
        assert doc.content_hash == content_hash

    def test_document_with_string_type_converts_to_enum(self):
        """Test that string type is converted to DocumentType enum."""
        # Arrange
        now = datetime.utcnow()
        content_hash = "b" * 64

        # Act
        doc = Document(
            id=uuid4(),
            project_id=uuid4(),
            name="document.pdf",
            type="pdf",  # String instead of enum
            version="1.0.0",
            content_hash=content_hash,
            created_at=now,
            updated_at=now,
        )

        # Assert
        assert doc.type == DocumentType.PDF
        assert isinstance(doc.type, DocumentType)

    def test_semantic_versioning_validation(self):
        """Test semantic version format validation."""
        now = datetime.utcnow()
        content_hash = "c" * 64

        # Valid versions
        valid_versions = ["v1.0.0", "1.0.0", "v10.20.30", "2.1.3"]
        for version in valid_versions:
            doc = Document(
                id=uuid4(),
                project_id=uuid4(),
                name="test.md",
                type=DocumentType.MARKDOWN,
                version=version,
                content_hash=content_hash,
                created_at=now,
                updated_at=now,
            )
            assert doc.version == version

    def test_invalid_semantic_version_raises_error(self):
        """Test that invalid version format raises ValueError."""
        now = datetime.utcnow()
        content_hash = "d" * 64

        invalid_versions = ["1.0", "v1", "1.0.0.0", "latest", ""]

        for version in invalid_versions:
            with pytest.raises(ValueError, match="Invalid version format"):
                Document(
                    id=uuid4(),
                    project_id=uuid4(),
                    name="test.md",
                    type=DocumentType.MARKDOWN,
                    version=version,
                    content_hash=content_hash,
                    created_at=now,
                    updated_at=now,
                )

    def test_empty_name_raises_error(self):
        """Test that empty document name raises ValueError."""
        now = datetime.utcnow()
        content_hash = "e" * 64

        with pytest.raises(ValueError, match="Document name cannot be empty"):
            Document(
                id=uuid4(),
                project_id=uuid4(),
                name="",
                type=DocumentType.MARKDOWN,
                version="1.0.0",
                content_hash=content_hash,
                created_at=now,
                updated_at=now,
            )

    def test_whitespace_only_name_raises_error(self):
        """Test that whitespace-only name raises ValueError."""
        now = datetime.utcnow()
        content_hash = "f" * 64

        with pytest.raises(ValueError, match="Document name cannot be empty"):
            Document(
                id=uuid4(),
                project_id=uuid4(),
                name="   ",
                type=DocumentType.MARKDOWN,
                version="1.0.0",
                content_hash=content_hash,
                created_at=now,
                updated_at=now,
            )

    def test_invalid_content_hash_raises_error(self):
        """Test that invalid content hash raises ValueError."""
        now = datetime.utcnow()

        # Too short
        with pytest.raises(ValueError, match="Invalid content_hash"):
            Document(
                id=uuid4(),
                project_id=uuid4(),
                name="test.md",
                type=DocumentType.MARKDOWN,
                version="1.0.0",
                content_hash="abc123",
                created_at=now,
                updated_at=now,
            )

        # Invalid characters
        with pytest.raises(ValueError, match="Invalid content_hash"):
            Document(
                id=uuid4(),
                project_id=uuid4(),
                name="test.md",
                type=DocumentType.MARKDOWN,
                version="1.0.0",
                content_hash="z" * 64,
                created_at=now,
                updated_at=now,
            )

    def test_all_document_types(self):
        """Test all supported document types."""
        now = datetime.utcnow()
        content_hash = "a" * 64

        types = [
            DocumentType.MARKDOWN,
            DocumentType.PDF,
            DocumentType.DOCX,
            DocumentType.HTML,
            DocumentType.TEXT,
        ]

        for doc_type in types:
            doc = Document(
                id=uuid4(),
                project_id=uuid4(),
                name=f"test.{doc_type.value}",
                type=doc_type,
                version="1.0.0",
                content_hash=content_hash,
                created_at=now,
                updated_at=now,
            )
            assert doc.type == doc_type
