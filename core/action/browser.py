"""Browser automation module using Playwright.

This module provides an asynchronous browser automation interface.
It runs headless by default to comply with ADR 11 (Background Execution)
and provides basic primitives (navigate, click, extract_text) as well
as a high-level `search` method to solve problems mid-task (ADR 13).
"""

import asyncio
import logging
from typing import Optional

from playwright.async_api import async_playwright, Playwright, Browser, BrowserContext, Page

import os

logger = logging.getLogger(__name__)


class BrowserAutomation:
    """Manages a Playwright browser instance for background automation."""

    def __init__(self, headless: bool = False, profile_dir: str = ".jar_profile"):
        """Initialize the browser automation.
        
        Args:
            headless: Whether to run the browser in headless mode. 
                      Defaults to False so user can log in and see actions.
            profile_dir: Directory to store the persistent browser profile.
        """
        self.headless = headless
        self.profile_dir = os.path.abspath(profile_dir)
        self._playwright: Optional[Playwright] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Initialize Playwright and launch the persistent browser context."""
        async with self._lock:
            if self._playwright is not None:
                return

            try:
                self._playwright = await async_playwright().start()
                
                # Ensure profile directory exists
                os.makedirs(self.profile_dir, exist_ok=True)
                
                # Launch persistent context instead of standard browser
                self._context = await self._playwright.chromium.launch_persistent_context(
                    user_data_dir=self.profile_dir,
                    headless=self.headless,
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                
                # Persistent context automatically gives us a default page
                pages = self._context.pages
                self._page = pages[0] if pages else await self._context.new_page()
                
                logger.info(f"BrowserAutomation started (headless={self.headless}, profile={self.profile_dir})")
            except Exception as e:
                logger.error(f"Failed to start Playwright browser: {e}")
                await self.stop()
                raise

    async def stop(self) -> None:
        """Close the browser and cleanup Playwright resources."""
        async with self._lock:
            try:
                if self._context:
                    await self._context.close()
                if self._playwright:
                    await self._playwright.stop()
            except Exception as e:
                logger.warning(f"Error during browser cleanup: {e}")
            finally:
                self._page = None
                self._context = None
                self._playwright = None
                logger.info("BrowserAutomation stopped")

    async def _ensure_started(self) -> None:
        """Helper to guarantee browser is running before taking action."""
        if not self._page:
            await self.start()

    async def navigate(self, url: str) -> None:
        """Navigate to a given URL.
        
        Args:
            url: The destination URL.
        """
        await self._ensure_started()
        logger.info(f"Navigating to {url}")
        await self._page.goto(url, wait_until="domcontentloaded")

    async def click(self, selector: str) -> None:
        """Click an element on the page using a CSS or XPath selector.
        
        Args:
            selector: The element selector.
        """
        await self._ensure_started()
        logger.info(f"Clicking element: {selector}")
        await self._page.click(selector)

    async def extract_text(self, selector: str = "body") -> str:
        """Extract text content from the specified element.
        
        Args:
            selector: The element selector. Defaults to "body".
            
        Returns:
            The inner text of the element.
        """
        await self._ensure_started()
        logger.info(f"Extracting text from: {selector}")
        element = await self._page.query_selector(selector)
        if element:
            text = await element.inner_text()
            return text
        return ""

    async def search(self, query: str) -> str:
        """Perform a free web search and return a summary of results.
        
        This complies with ADR 13 (Live Web Search for Problem-Solving) 
        without needing an API key. Uses Wikipedia as a reliable source
        that doesn't aggressively block headless browsers.
        
        Args:
            query: The search query string.
            
        Returns:
            A string containing the extracted search results (titles and snippets).
        """
        await self._ensure_started()
        logger.info(f"Performing web search for: '{query}'")
        
        import urllib.parse
        encoded_query = urllib.parse.quote(query)
        search_url = f"https://en.wikipedia.org/w/index.php?search={encoded_query}&title=Special:Search&profile=advanced&fulltext=1"
        await self.navigate(search_url)
        
        # Wikipedia search results are in .mw-search-result
        results = await self._page.query_selector_all(".mw-search-result")
        
        extracted = []
        for res in results[:5]:  # Get top 5 results
            title_el = await res.query_selector(".mw-search-result-heading")
            snippet_el = await res.query_selector(".searchresult")
            
            title = await title_el.inner_text() if title_el else "No Title"
            snippet = await snippet_el.inner_text() if snippet_el else "No Snippet"
            
            extracted.append(f"Title: {title.strip()}\nSnippet: {snippet.strip()}")
            
        if not extracted:
            return "No results found."
            
        return "\n\n".join(extracted)
