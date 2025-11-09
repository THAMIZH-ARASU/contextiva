"""Unit tests for WebCrawler service."""
import pytest
from unittest.mock import AsyncMock, Mock, patch
import httpx

from src.infrastructure.external.crawler.crawler_client import WebCrawler, CrawledContent
from src.shared.config.settings import CrawlerSettings
from src.shared.utils.errors import CrawlError


@pytest.fixture
def crawler_settings():
    """Create test crawler settings."""
    return CrawlerSettings(
        timeout_seconds=30,
        user_agent="Contextiva/1.0",
        respect_robots_txt=True,
        max_retries=3,
    )


@pytest.fixture
def web_crawler(crawler_settings):
    """Create WebCrawler instance for testing."""
    return WebCrawler(crawler_settings)


@pytest.fixture
def sample_html():
    """Sample HTML content for testing."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page</title>
        <meta name="description" content="Test description">
        <meta name="keywords" content="test, keywords">
        <link rel="canonical" href="https://example.com/canonical">
        <script>console.log('script');</script>
        <style>.test {color: red;}</style>
    </head>
    <body>
        <h1>Main Heading</h1>
        <p>First paragraph with some text.</p>
        <h2>Subheading</h2>
        <p>Second paragraph.</p>
        <ul>
            <li>List item 1</li>
            <li>List item 2</li>
        </ul>
        <table>
            <tr><th>Header</th></tr>
            <tr><td>Cell content</td></tr>
        </table>
        <noscript>No script content</noscript>
    </body>
    </html>
    """


@pytest.fixture
def robots_txt_allowed():
    """Sample robots.txt that allows crawling."""
    return """
User-agent: *
Disallow: /admin/
Allow: /
"""


@pytest.fixture
def robots_txt_disallowed():
    """Sample robots.txt that disallows crawling."""
    return """
User-agent: *
Disallow: /
"""


class TestFetchUrl:
    """Tests for fetch_url method."""

    @pytest.mark.asyncio
    async def test_fetch_url_success(self, web_crawler):
        """Test successful URL fetch."""
        # Arrange
        test_url = "https://example.com"
        expected_html = "<html><body>Test</body></html>"

        mock_response = Mock()
        mock_response.text = expected_html
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            # Act
            result = await web_crawler.fetch_url(test_url)

            # Assert
            assert result == expected_html
            mock_client.return_value.__aenter__.return_value.get.assert_called_once()
            call_kwargs = mock_client.return_value.__aenter__.return_value.get.call_args[1]
            assert call_kwargs["headers"]["User-Agent"] == "Contextiva/1.0"
            assert call_kwargs["follow_redirects"] is True

    @pytest.mark.asyncio
    async def test_fetch_url_timeout(self, web_crawler):
        """Test URL fetch with timeout error."""
        # Arrange
        test_url = "https://example.com"

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.TimeoutException("Timeout")
            )

            # Act & Assert
            with pytest.raises(CrawlError) as exc_info:
                await web_crawler.fetch_url(test_url)

            assert "timed out" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_fetch_url_http_error(self, web_crawler):
        """Test URL fetch with HTTP status error."""
        # Arrange
        test_url = "https://example.com"

        mock_response = Mock()
        mock_response.status_code = 404

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "Not found", request=Mock(), response=mock_response
                )
            )

            # Act & Assert
            with pytest.raises(CrawlError) as exc_info:
                await web_crawler.fetch_url(test_url)

            assert "HTTP 404" in str(exc_info.value) or "404" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_fetch_url_connection_error(self, web_crawler):
        """Test URL fetch with connection error."""
        # Arrange
        test_url = "https://example.com"

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.ConnectError("Connection failed")
            )

            # Act & Assert
            with pytest.raises(CrawlError) as exc_info:
                await web_crawler.fetch_url(test_url)

            assert "connect" in str(exc_info.value).lower()


class TestExtractTextFromHtml:
    """Tests for extract_text_from_html method."""

    @pytest.mark.asyncio
    async def test_extract_text_basic(self, web_crawler, sample_html):
        """Test basic text extraction from HTML."""
        # Act
        result = await web_crawler.extract_text_from_html(sample_html, "https://example.com")

        # Assert
        assert isinstance(result, CrawledContent)
        assert "Main Heading" in result.text
        assert "First paragraph" in result.text
        assert "List item 1" in result.text
        assert "Cell content" in result.text
        # Script and style content should not be in text
        assert "console.log" not in result.text
        assert "color: red" not in result.text

    @pytest.mark.asyncio
    async def test_extract_metadata(self, web_crawler, sample_html):
        """Test metadata extraction from HTML."""
        # Act
        result = await web_crawler.extract_text_from_html(sample_html, "https://example.com")

        # Assert
        assert result.title == "Test Page"
        assert result.description == "Test description"
        assert result.canonical_url == "https://example.com/canonical"
        assert result.metadata["page_title"] == "Test Page"
        assert result.metadata["meta_description"] == "Test description"
        assert result.metadata["keywords"] == "test, keywords"

    @pytest.mark.asyncio
    async def test_extract_text_no_metadata(self, web_crawler):
        """Test text extraction from HTML with no metadata."""
        # Arrange
        html = "<html><body><p>Simple text</p></body></html>"

        # Act
        result = await web_crawler.extract_text_from_html(html, "https://example.com")

        # Assert
        assert "Simple text" in result.text
        assert result.title is None
        assert result.description is None
        assert result.canonical_url is None

    @pytest.mark.asyncio
    async def test_extract_text_preserves_structure(self, web_crawler, sample_html):
        """Test that text extraction preserves document structure."""
        # Act
        result = await web_crawler.extract_text_from_html(sample_html, "https://example.com")

        # Assert
        # Text should be separated by newlines
        assert "\n" in result.text
        # Headings and paragraphs should be separate blocks
        text_blocks = result.text.split("\n\n")
        assert len(text_blocks) > 3

    @pytest.mark.asyncio
    async def test_extract_text_invalid_html(self, web_crawler):
        """Test handling of malformed HTML."""
        # Arrange - BeautifulSoup is forgiving, so this shouldn't raise
        html = "<html><body><p>Unclosed tag"

        # Act
        result = await web_crawler.extract_text_from_html(html, "https://example.com")

        # Assert
        assert "Unclosed tag" in result.text


class TestCheckRobotsTxt:
    """Tests for check_robots_txt method."""

    @pytest.mark.asyncio
    async def test_robots_txt_allowed(self, web_crawler, robots_txt_allowed):
        """Test robots.txt allows crawling."""
        # Arrange
        test_url = "https://example.com/page"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = robots_txt_allowed
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            # Act
            result = await web_crawler.check_robots_txt(test_url)

            # Assert
            assert result is True

    @pytest.mark.asyncio
    async def test_robots_txt_disallowed(self, web_crawler, robots_txt_disallowed):
        """Test robots.txt disallows crawling."""
        # Arrange
        test_url = "https://example.com/page"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = robots_txt_disallowed
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            # Act & Assert
            with pytest.raises(CrawlError) as exc_info:
                await web_crawler.check_robots_txt(test_url)

            assert "robots.txt" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_robots_txt_not_found(self, web_crawler):
        """Test robots.txt 404 allows crawling."""
        # Arrange
        test_url = "https://example.com/page"

        mock_response = Mock()
        mock_response.status_code = 404

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            # Act
            result = await web_crawler.check_robots_txt(test_url)

            # Assert
            assert result is True

    @pytest.mark.asyncio
    async def test_robots_txt_fetch_error(self, web_crawler):
        """Test robots.txt fetch error allows crawling (fail open)."""
        # Arrange
        test_url = "https://example.com/page"

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.ConnectError("Connection failed")
            )

            # Act
            result = await web_crawler.check_robots_txt(test_url)

            # Assert
            assert result is True


class TestCrawl:
    """Tests for the crawl convenience method."""

    @pytest.mark.asyncio
    async def test_crawl_success(self, web_crawler, sample_html):
        """Test successful crawl."""
        # Arrange
        test_url = "https://example.com/page"

        # Mock robots.txt check
        with patch.object(web_crawler, "check_robots_txt", AsyncMock(return_value=True)):
            # Mock fetch
            with patch.object(web_crawler, "fetch_url", AsyncMock(return_value=sample_html)):
                # Act
                result = await web_crawler.crawl(test_url, respect_robots_txt=True)

                # Assert
                assert isinstance(result, CrawledContent)
                assert "Main Heading" in result.text
                assert result.title == "Test Page"

    @pytest.mark.asyncio
    async def test_crawl_skip_robots_txt(self, web_crawler, sample_html):
        """Test crawl skips robots.txt check when requested."""
        # Arrange
        test_url = "https://example.com/page"

        # Mock fetch
        with patch.object(web_crawler, "fetch_url", AsyncMock(return_value=sample_html)):
            with patch.object(web_crawler, "check_robots_txt", AsyncMock()) as mock_robots:
                # Act
                result = await web_crawler.crawl(test_url, respect_robots_txt=False)

                # Assert
                mock_robots.assert_not_called()
                assert isinstance(result, CrawledContent)

    @pytest.mark.asyncio
    async def test_crawl_robots_txt_blocks(self, web_crawler):
        """Test crawl raises error when robots.txt blocks."""
        # Arrange
        test_url = "https://example.com/page"

        # Mock robots.txt check to raise error
        with patch.object(
            web_crawler,
            "check_robots_txt",
            AsyncMock(side_effect=CrawlError("Blocked by robots.txt")),
        ):
            # Act & Assert
            with pytest.raises(CrawlError) as exc_info:
                await web_crawler.crawl(test_url, respect_robots_txt=True)

            assert "robots.txt" in str(exc_info.value).lower()
