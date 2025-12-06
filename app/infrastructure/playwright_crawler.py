import asyncio
import random
from typing import List, Optional
from playwright.async_api import async_playwright
from app.domain.ports import RetrievalService

class PlaywrightCrawler(RetrievalService):
    async def fetch_content(self, urls: List[str]) -> List[str]:
        contents = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 720}
            )

            for url in urls:
                try:
                    # Throttling: Random delay 5-10s (Reduced for speed as per user script logic, but keep some safety)
                    delay = random.uniform(5, 10)
                    print(f"Throttling: Waiting {delay:.2f}s before fetching {url}")
                    await asyncio.sleep(delay)

                    page = await context.new_page()
                    print(f"Navigating to: {url}")
                    await page.goto(url, wait_until="domcontentloaded", timeout=60000)

                    try:
                        await page.wait_for_load_state("networkidle", timeout=10000)
                    except Exception:
                        print("[warn] networkidle not reached, continuing...")

                    await page.wait_for_timeout(750)
                    html = await page.content()

                    # Parse using BeautifulSoup (User's logic)
                    post_text, author_name, author_linkedin_url = self._get_post_details(html)

                    if post_text:
                        # We could validate author here if we had the expected name.
                        # For now, just return the text.
                        # Ideally, we should return a Dict with metadata, but interface says List[str].
                        # We'll append the text.
                        contents.append(post_text)

                    await page.close()
                except Exception as e:
                    print(f"Error crawling {url}: {e}")

            await browser.close()
        return contents

    def _get_post_details(self, html: str):
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
            print(f"[error] Exception in getPostDetails: {e}")

    async def extract_content(self, url: str) -> Optional[str]:
        # Reuse fetch_content logic for single URL
        results = await self.fetch_content([url])
        return results[0] if results else None
