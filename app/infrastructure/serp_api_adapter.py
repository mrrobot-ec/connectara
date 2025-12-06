from app.domain.ports import DiscoveryService
from typing import List
import requests
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

class SerpApiDiscoveryAdapter(DiscoveryService):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://serpapi.com/search"

    async def find_posts(self, full_name: str, username: str, education: List[str] = None) -> List[str]:
        # Logic from user's script: get_posts_similar_to_fullname
        query = f'site:linkedin.com inurl:"/posts/" intext:"{full_name}"'

        params = {
            'q': query,
            'api_key': self.api_key,
        }

        print(f"DEBUG: SerpApi Query: {query}")

        # We can run this in executor to avoid blocking
        # But requests is sync.
        # Let's wrap it.
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._fetch_posts, params)

    def _fetch_posts(self, params):
        response = requests.get(self.base_url, params=params)
        response.raise_for_status()
        data = response.json()

        all_posts = []
        first_page_results = data.get("organic_results", [])

        # Pagination logic from user script
        if "serpapi_pagination" in data:
            pagination = data["serpapi_pagination"]
            other_pages = pagination.get("other_pages") or {}

            if other_pages:
                api_key = params.get("api_key")
                page_results = {}

                def fetch_page(page_num: str, page_url: str):
                    query_params = {} if not api_key or "api_key=" in page_url else {"api_key": api_key}
                    page_response = requests.get(page_url, params=query_params, timeout=15)
                    page_response.raise_for_status()
                    p_data = page_response.json()
                    return int(page_num), p_data.get("organic_results", [])

                with ThreadPoolExecutor(max_workers=min(8, len(other_pages))) as executor:
                    futures = [
                        executor.submit(fetch_page, page_num, page_url)
                        for page_num, page_url in other_pages.items()
                    ]

                    for future in as_completed(futures):
                        try:
                            page_num, organic_results = future.result()
                        except Exception:
                            continue
                        if organic_results:
                            page_results[page_num] = organic_results
                for page_index in sorted(page_results):
                    all_posts.extend(page_results[page_index])

        all_posts.extend(first_page_results)

        # Filter out non-post URLs
        valid_post_urls = []
        for x in all_posts:
            link = x.get("link")
            if link and "/posts/" in link:
                valid_post_urls.append(link)

        return valid_post_urls
