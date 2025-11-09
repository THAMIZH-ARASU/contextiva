"""Web crawler service for fetching and parsing web pages."""
import logging
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

from src.shared.config.settings import CrawlerSettings
from src.shared.utils.errors import CrawlError

logger = logging.getLogger(__name__)


@dataclass
class CrawledContent:
    """Container for crawled web page content and metadata."""

    text: str
    title: str | None
    description: str | None
    canonical_url: str | None
    metadata: dict[str, Any]


class WebCrawler:
    """Service for crawling and extracting content from web pages."""

    def __init__(self, settings: CrawlerSettings):
        """
        Initialize the web crawler with configuration settings.

        Args:
            settings: Crawler configuration settings
        """
        self.settings = settings
        self.timeout = httpx.Timeout(settings.timeout_seconds, connect=10.0)

    async def fetch_url(self, url: str) -> str:
        """
        Fetch raw HTML content from a URL.

        Args:
            url: URL to fetch

        Returns:
            Raw HTML content as string

        Raises:
            CrawlError: If network request fails or times out
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {"User-Agent": self.settings.user_agent}
                response = await client.get(url, headers=headers, follow_redirects=True)
                response.raise_for_status()
                return response.text

        except httpx.TimeoutException as e:
            logger.error(f"Timeout fetching URL {url}: {e}")
            raise CrawlError(f"Request timed out after {self.settings.timeout_seconds}s: {str(e)}")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching URL {url}: {e.response.status_code}")
            raise CrawlError(f"HTTP {e.response.status_code}: {str(e)}")
        except httpx.ConnectError as e:
            logger.error(f"Connection error fetching URL {url}: {e}")
            raise CrawlError(f"Failed to connect to URL: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error fetching URL {url}: {e}")
            raise CrawlError(f"Failed to fetch URL: {str(e)}")

    async def check_robots_txt(self, url: str) -> bool:
        """
        Check if crawling is allowed by robots.txt.

        Args:
            url: URL to check

        Returns:
            True if crawling is allowed, False otherwise

        Raises:
            CrawlError: If robots.txt disallows crawling
        """
        try:
            parsed_url = urlparse(url)
            robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"

            # Fetch robots.txt
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    headers = {"User-Agent": self.settings.user_agent}
                    response = await client.get(robots_url, headers=headers)

                    # If robots.txt doesn't exist (404), allow crawling
                    if response.status_code == 404:
                        logger.info(f"No robots.txt found for {parsed_url.netloc}, allowing crawl")
                        return True

                    response.raise_for_status()
                    robots_content = response.text

            except Exception as e:
                # If we can't fetch robots.txt for any reason, allow crawling
                logger.warning(f"Failed to fetch robots.txt from {robots_url}: {e}")
                return True

            # Parse robots.txt
            parser = RobotFileParser()
            parser.parse(robots_content.splitlines())

            # Check if our user agent can fetch the URL
            is_allowed = parser.can_fetch(self.settings.user_agent, url)

            if not is_allowed:
                logger.warning(f"robots.txt disallows crawling {url}")
                raise CrawlError(f"Crawling {url} is disallowed by robots.txt")

            return is_allowed

        except CrawlError:
            raise
        except Exception as e:
            logger.error(f"Error checking robots.txt for {url}: {e}")
            # On error, allow crawling (fail open)
            return True

    async def extract_text_from_html(self, html: str, url: str) -> CrawledContent:
        """
        Extract text content and metadata from HTML.

        Args:
            html: Raw HTML content
            url: Source URL for resolving relative links

        Returns:
            CrawledContent with extracted text and metadata

        Raises:
            CrawlError: If HTML parsing fails
        """
        try:
            soup = BeautifulSoup(html, "lxml")

            # Remove script and style elements
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()

            # Extract metadata
            title = None
            if soup.title:
                title = soup.title.string.strip() if soup.title.string else None

            description = None
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc:
                description = meta_desc.get("content", "").strip()

            canonical_url = None
            canonical_link = soup.find("link", attrs={"rel": "canonical"})
            if canonical_link:
                href = canonical_link.get("href")
                if href:
                    canonical_url = urljoin(url, href)

            # Extract keywords if available
            keywords = None
            meta_keywords = soup.find("meta", attrs={"name": "keywords"})
            if meta_keywords:
                keywords = meta_keywords.get("content", "").strip()

            # Extract text content preserving structure
            text_blocks: list[str] = []

            # Extract headings
            for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
                text = heading.get_text(strip=True)
                if text:
                    text_blocks.append(text)

            # Extract paragraphs
            for paragraph in soup.find_all("p"):
                text = paragraph.get_text(strip=True)
                if text:
                    text_blocks.append(text)

            # Extract list items
            for li in soup.find_all("li"):
                text = li.get_text(strip=True)
                if text:
                    text_blocks.append(text)

            # Extract table cells
            for cell in soup.find_all(["td", "th"]):
                text = cell.get_text(strip=True)
                if text:
                    text_blocks.append(text)

            # Join all text blocks with newlines
            full_text = "\n\n".join(text_blocks)

            # Build metadata dictionary
            metadata = {
                "source_url": url,
                "canonical_url": canonical_url,
                "page_title": title,
                "meta_description": description,
            }

            if keywords:
                metadata["keywords"] = keywords

            return CrawledContent(
                text=full_text,
                title=title,
                description=description,
                canonical_url=canonical_url,
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"Failed to extract text from HTML: {e}")
            raise CrawlError(f"HTML parsing failed: {str(e)}")

    async def crawl(self, url: str, respect_robots_txt: bool = True) -> CrawledContent:
        """
        Crawl a URL and extract its content.

        This is a convenience method that combines fetch, robots.txt check,
        and text extraction.

        Args:
            url: URL to crawl
            respect_robots_txt: Whether to check robots.txt before crawling

        Returns:
            CrawledContent with extracted text and metadata

        Raises:
            CrawlError: If any step of the crawling process fails
        """
        # Check robots.txt if requested
        if respect_robots_txt:
            await self.check_robots_txt(url)

        # Fetch HTML
        html = await self.fetch_url(url)

        # Extract text and metadata
        content = await self.extract_text_from_html(html, url)

        return content
