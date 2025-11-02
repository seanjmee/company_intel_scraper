"""
Web scraping module for company intelligence gathering
Provides functions to fetch website content and links with proper error handling
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Optional
from urllib.parse import urljoin, urlparse
import time


# Constants
DEFAULT_TIMEOUT = 10  # seconds
DEFAULT_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
MAX_CONTENT_LENGTH = 50000  # characters per page


def fetch_website_contents(url: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    """
    Fetch and extract text content from a website

    Args:
        url: The URL to fetch
        timeout: Request timeout in seconds

    Returns:
        Extracted text content from the page

    Raises:
        Exception: If fetching or parsing fails
    """
    try:
        headers = {'User-Agent': DEFAULT_USER_AGENT}
        response = requests.get(url, timeout=timeout, headers=headers)
        response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')

        # Remove script and style elements
        for script in soup(['script', 'style', 'nav', 'footer', 'header']):
            script.decompose()

        # Get text content
        text = soup.get_text(separator=' ', strip=True)

        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)

        # Truncate if too long
        if len(text) > MAX_CONTENT_LENGTH:
            text = text[:MAX_CONTENT_LENGTH] + "... [content truncated]"

        return text

    except requests.Timeout:
        raise Exception(f"Timeout fetching {url}")
    except requests.RequestException as e:
        raise Exception(f"Error fetching {url}: {str(e)}")
    except Exception as e:
        raise Exception(f"Error parsing {url}: {str(e)}")


def fetch_website_links(url: str, timeout: int = DEFAULT_TIMEOUT) -> List[str]:
    """
    Fetch all links from a website

    Args:
        url: The URL to fetch links from
        timeout: Request timeout in seconds

    Returns:
        List of absolute URLs found on the page

    Raises:
        Exception: If fetching or parsing fails
    """
    try:
        headers = {'User-Agent': DEFAULT_USER_AGENT}
        response = requests.get(url, timeout=timeout, headers=headers)
        response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract all links
        links = []
        base_domain = urlparse(url).netloc

        for anchor in soup.find_all('a', href=True):
            href = anchor['href']

            # Convert relative URLs to absolute
            absolute_url = urljoin(url, href)

            # Only include HTTP/HTTPS links from same domain
            parsed = urlparse(absolute_url)
            if parsed.scheme in ('http', 'https') and parsed.netloc == base_domain:
                links.append(absolute_url)

        # Remove duplicates while preserving order
        seen = set()
        unique_links = []
        for link in links:
            if link not in seen:
                seen.add(link)
                unique_links.append(link)

        return unique_links

    except requests.Timeout:
        raise Exception(f"Timeout fetching links from {url}")
    except requests.RequestException as e:
        raise Exception(f"Error fetching links from {url}: {str(e)}")
    except Exception as e:
        raise Exception(f"Error parsing links from {url}: {str(e)}")


def fetch_with_retry(url: str, max_retries: int = 3, backoff: float = 2.0) -> str:
    """
    Fetch website content with exponential backoff retry logic

    Args:
        url: The URL to fetch
        max_retries: Maximum number of retry attempts
        backoff: Backoff multiplier for retries

    Returns:
        Extracted text content from the page
    """
    for attempt in range(max_retries):
        try:
            return fetch_website_contents(url)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait_time = backoff ** attempt
            print(f"   ⚠️  Attempt {attempt + 1} failed, retrying in {wait_time}s...")
            time.sleep(wait_time)

    raise Exception(f"Failed to fetch {url} after {max_retries} attempts")
