"""Unit tests for TextExtractor service."""
import pytest
from io import BytesIO

from src.application.services.text_extractor import TextExtractor
from src.shared.utils.errors import TextExtractionError


@pytest.fixture
def text_extractor():
    """Create TextExtractor instance."""
    return TextExtractor()


@pytest.mark.asyncio
class TestTextExtractorMarkdown:
    """Test markdown text extraction."""

    async def test_extract_markdown_success(self, text_extractor):
        """Test successful markdown extraction."""
        # Arrange
        markdown_content = b"# Title\n\nThis is **bold** text.\n\n## Subtitle\n\nMore content."
        
        # Act
        result = await text_extractor.extract(markdown_content, "test.md")
        
        # Assert
        assert "# Title" in result
        assert "This is **bold** text." in result
        assert "## Subtitle" in result
        assert len(result) > 0

    async def test_extract_markdown_empty(self, text_extractor):
        """Test extraction of empty markdown file."""
        # Arrange
        markdown_content = b""
        
        # Act
        result = await text_extractor.extract(markdown_content, "test.md")
        
        # Assert
        assert result == ""

    async def test_extract_markdown_utf8(self, text_extractor):
        """Test extraction with UTF-8 characters."""
        # Arrange
        markdown_content = "# Título\n\nContenido en español: ñ, á, é".encode('utf-8')
        
        # Act
        result = await text_extractor.extract(markdown_content, "test.md")
        
        # Assert
        assert "Título" in result
        assert "español" in result
        assert "ñ" in result


@pytest.mark.asyncio
class TestTextExtractorHTML:
    """Test HTML text extraction."""

    async def test_extract_html_success(self, text_extractor):
        """Test successful HTML extraction."""
        # Arrange
        html_content = b"""
        <html>
            <head><title>Test Page</title></head>
            <body>
                <h1>Main Title</h1>
                <p>This is a paragraph.</p>
                <script>console.log('should be removed');</script>
                <style>.class { color: red; }</style>
            </body>
        </html>
        """
        
        # Act
        result = await text_extractor.extract(html_content, "test.html")
        
        # Assert
        assert "Main Title" in result
        assert "This is a paragraph." in result
        assert "console.log" not in result  # Scripts removed
        assert "color: red" not in result   # Styles removed

    async def test_extract_html_nested_tags(self, text_extractor):
        """Test extraction with nested HTML tags."""
        # Arrange
        html_content = b"""
        <div>
            <p>Outer <strong>bold <em>italic</em></strong> text</p>
        </div>
        """
        
        # Act
        result = await text_extractor.extract(html_content, "test.html")
        
        # Assert
        assert "Outer" in result
        assert "bold" in result
        assert "italic" in result
        assert "text" in result

    async def test_extract_html_empty(self, text_extractor):
        """Test extraction of empty HTML."""
        # Arrange
        html_content = b"<html><body></body></html>"
        
        # Act
        result = await text_extractor.extract(html_content, "test.html")
        
        # Assert
        assert result.strip() == ""


@pytest.mark.asyncio
class TestTextExtractorPDF:
    """Test PDF text extraction."""

    async def test_extract_pdf_simple(self, text_extractor):
        """Test extraction from a simple PDF (would need real PDF bytes)."""
        # Note: This is a placeholder - real PDF testing would require
        # creating actual PDF files or using fixtures
        # For now, we test the error handling path
        
        # Arrange - Invalid PDF content
        invalid_pdf = b"Not a PDF file"
        
        # Act & Assert
        with pytest.raises(TextExtractionError) as exc_info:
            await text_extractor.extract(invalid_pdf, "test.pdf")
        
        assert "Failed to extract text from PDF" in str(exc_info.value)


@pytest.mark.asyncio
class TestTextExtractorDOCX:
    """Test DOCX text extraction."""

    async def test_extract_docx_invalid(self, text_extractor):
        """Test extraction from invalid DOCX file."""
        # Arrange - Invalid DOCX content
        invalid_docx = b"Not a DOCX file"
        
        # Act & Assert
        with pytest.raises(TextExtractionError) as exc_info:
            await text_extractor.extract(invalid_docx, "test.docx")
        
        assert "Failed to extract text from DOCX" in str(exc_info.value)


@pytest.mark.asyncio
class TestTextExtractorFileTypeDetection:
    """Test file type detection."""

    async def test_detect_markdown_extension(self, text_extractor):
        """Test markdown file type detection."""
        # Arrange
        content = b"# Test"
        
        # Act
        result = await text_extractor.extract(content, "file.md")
        
        # Assert
        assert result == "# Test"

    async def test_detect_html_extension(self, text_extractor):
        """Test HTML file type detection."""
        # Arrange
        content = b"<p>Test</p>"
        
        # Act
        result = await text_extractor.extract(content, "file.html")
        
        # Assert
        assert "Test" in result

    async def test_unsupported_file_type(self, text_extractor):
        """Test unsupported file type."""
        # Arrange
        content = b"Test content"
        
        # Act & Assert
        with pytest.raises(TextExtractionError) as exc_info:
            await text_extractor.extract(content, "file.txt")
        
        assert "Unsupported file format" in str(exc_info.value)


@pytest.mark.asyncio
class TestTextExtractorErrorHandling:
    """Test error handling."""

    async def test_extract_corrupted_file(self, text_extractor):
        """Test handling of corrupted files."""
        # Arrange - Corrupted PDF
        corrupted_content = b"%PDF-1.4\nCorrupted data..."
        
        # Act & Assert
        with pytest.raises(TextExtractionError):
            await text_extractor.extract(corrupted_content, "corrupted.pdf")

    async def test_extract_empty_filename(self, text_extractor):
        """Test handling of empty filename."""
        # Arrange
        content = b"Test"
        
        # Act & Assert
        with pytest.raises(TextExtractionError):
            await text_extractor.extract(content, "")
