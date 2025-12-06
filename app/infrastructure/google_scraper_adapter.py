from typing import List
from googlesearch import search
from app.domain.ports import DiscoveryService
import time
import random

class GoogleScraperAdapter(DiscoveryService):
    async def find_posts(self, full_name: str, username: str, education: List[str] = None) -> List[str]:
        links = []
        print(f"Scraping Google for {full_name}...")

        try:
            # Strategy A: Profile/Article Find
            # site:linkedin.com/in/username
            query_a = f'site:linkedin.com/in/{username}'
            print(f"DEBUG: Running Google Query A: {query_a}")
            # num_results=5, sleep_interval=2 (to avoid 429)
            results_a = list(search(query_a, num_results=3, sleep_interval=random.uniform(2, 5)))
            print(f"DEBUG: Results A: {results_a}")
            links.extend(results_a)

            # Strategy B: Direct Post Find
            # site:linkedin.com/posts/username
            query_b = f'inurl:"linkedin.com/posts/{username}"'
            print(f"DEBUG: Running Google Query B: {query_b}")
            results_b = list(search(query_b, num_results=3, sleep_interval=random.uniform(2, 5)))
            print(f"DEBUG: Results B: {results_b}")
            links.extend(results_b)

            # # Strategy C: Blogs / Medium
            # query_c = f'(site:medium.com OR site:dev.to OR intitle:blog) "{full_name}"'
            # print(f"DEBUG: Running Google Query C: {query_c}")
            # results_c = list(search(query_c, num_results=10, sleep_interval=random.uniform(2, 5)))
            # print(f"DEBUG: Results C: {results_c}")
            # links.extend(results_c)

            # Strategy D: School / Education
            if education:
                print(f"DEBUG: Education found: {education}")
                for school in education:
                    query_d = f'site:linkedin.com "{full_name}" "{school}"'
                    print(f"DEBUG: Running Google Query D: {query_d}")
                    results_d = list(search(query_d, num_results=3, sleep_interval=random.uniform(2, 5)))
                    print(f"DEBUG: Results D: {results_d}")
                    links.extend(results_d)
            else:
                print("DEBUG: No education data found for dorking.")

        except Exception as e:
            print(f"Error in Google Scraper: {e}")
            # Fallback or just continue with what we have

        unique_links = list(set(links))
        print(f"DEBUG: Found {len(unique_links)} unique links: {unique_links}")
        return unique_links
