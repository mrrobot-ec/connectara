import asyncio
import random
from typing import List, Optional, Tuple
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from app.domain.ports import RetrievalService
from urllib.parse import urlparse, urlunparse

class PlaywrightCrawler(RetrievalService):
    @staticmethod
    def _normalize_linkedin_url(url: str) -> str:
        """Normalize LinkedIn URLs to format: https://www.linkedin.com/in/username"""
        parsed = urlparse(url)
        netloc = parsed.netloc
        if 'linkedin.com' in netloc:
            netloc = 'www.linkedin.com'
        return urlunparse(('https', netloc, parsed.path, '', '', ''))

    async def fetch_content(self, urls: List[str]) -> List[str]:
        """Fetch content from URLs without validation."""
        return await self._fetch_content_internal(urls, validate=False)

    async def fetch_validated_content(self, urls: List[str], expected_name: str, expected_profile_url: str) -> List[str]:
        """Fetch and validate content from URLs, ensuring posts belong to the expected author."""
        return await self._fetch_content_internal(
            urls,
            validate=True,
            expected_name=expected_name,
            expected_profile_url=expected_profile_url
        )

    async def _fetch_content_internal(
        self,
        urls: List[str],
        validate: bool = False,
        expected_name: Optional[str] = None,
        expected_profile_url: Optional[str] = None
    ) -> List[str]:
        """Internal method to fetch content with optional validation."""
        if not urls:
            return []
        contents = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)

            # Process URLs in parallel using asyncio.gather
            tasks = [
                self._process_single_url(
                    browser,
                    url,
                    validate,
                    expected_name,
                    expected_profile_url
                )
                for url in urls
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for url, result in zip(urls, results):
                if isinstance(result, Exception):
                    print(f"[error] Failed to process {url}: {result}")
                    continue

                if result:  # result is the post_text if validation passed
                    contents.append(result)

            await browser.close()

        if validate:
            print(f"[info] Retrieved {len(contents)} valid posts out of {len(urls)} total posts found.")

        return contents

    async def _process_single_url(
        self,
        browser,
        url: str,
        validate: bool,
        expected_name: Optional[str],
        expected_profile_url: Optional[str]
    ) -> Optional[str]:
        """Process a single URL with optional validation."""
        try:
            # Throttling: Random delay 5-10s
            delay = random.uniform(5, 10)
            print(f"Throttling: Waiting {delay:.2f}s before fetching {url}")
            await asyncio.sleep(delay)

            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 720}
            )
            page = await context.new_page()

            print(f"Navigating to: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)

            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except PlaywrightTimeoutError:
                print("[warn] networkidle not reached, continuing anyway...")

            await page.wait_for_timeout(750)
            html = await page.content()

            await context.close()
            await page.close()

            # Parse post details
            post_text, author_name, author_linkedin_url = self._get_post_details(html)

            if not validate:
                # No validation, just return the text if available
                return post_text

            # Validation mode
            if not all([post_text, author_name, author_linkedin_url]):
                print(f"[warn] Incomplete data for post {url}, skipping...")
                return None

            # Validate author name
            if author_name and author_name.lower() == expected_name.lower():
                # Validate author profile URL
                normalized_author_url = self._normalize_linkedin_url(author_linkedin_url)
                normalized_expected_url = self._normalize_linkedin_url(expected_profile_url)

                if normalized_author_url == normalized_expected_url:
                    print(f"[info] Validated post from {author_name} at {author_linkedin_url}")
                    return post_text
                else:
                    print(f"[warn] Author LinkedIn URL mismatch for post at {url}, skipping...")
            else:
                print(f"[warn] Author name mismatch for post at {url}, skipping...")

            return None

        except Exception as e:
            print(f"[error] Error processing {url}: {e}")
            return None

    def _get_post_details(self, html: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Extract post text, author name, and author LinkedIn URL from HTML."""
        from bs4 import BeautifulSoup
        post_text, author_name, author_linkedin_url = None, None, None
        try:
            soup = BeautifulSoup(html, "html.parser")

            # find post description
            mb3_sections = soup.find_all("section", class_="mb-3")
            if not mb3_sections:
                # Try alternative selectors if layout changed?
                pass

            if mb3_sections:
                mb3_section = mb3_sections[0]
                articles = mb3_section.find_all("article")
                if articles:
                    article = articles[0]
                    p_tag = article.find("p")
                    post_text = p_tag.get_text(strip=True) if p_tag else None

                    # author name
                    author_flexboxes = article.find_all("div", class_="flex")
                    if author_flexboxes:
                        author_flexbox = author_flexboxes[0]
                        author_links = author_flexbox.find_all('a', attrs={'data-tracking-control-name': 'public_post_feed-actor-name'})
                        if author_links:
                            author_name = author_links[0].get_text(strip=True)
                            author_linkedin_url = author_links[0].get('href')

        except Exception as e:
            print(f"[error] Exception in _get_post_details: {e}")

        return post_text, author_name, author_linkedin_url

    async def extract_content(self, url: str) -> Optional[str]:
        # Reuse fetch_content logic for single URL
        results = await self.fetch_content([url])
        return results[0] if results else None
