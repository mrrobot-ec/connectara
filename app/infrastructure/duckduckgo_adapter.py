from typing import List
from app.domain.ports import DiscoveryService
from duckduckgo_search import DDGS

class DuckDuckGoAdapter(DiscoveryService):
    async def find_posts(self, full_name: str, username: str, education: List[str] = None) -> List[str]:
        links = []
        print(f"Dorking with DuckDuckGo for {full_name}...")

        try:
            with DDGS() as ddgs:
                # Strategy A: Profile/Article Find (Relaxed)
                # site:linkedin.com/in/username
                query_a = f'site:linkedin.com/in/{username}'
                print(f"DEBUG: Running Query A: {query_a}")
                results_a = ddgs.text(query_a, max_results=5)
                print(f"DEBUG: Results A: {results_a}")
                for r in results_a:
                    links.append(r['href'])

                # Strategy B: Direct Post Find (Corrected)
                # inurl:"linkedin.com/posts/username"
                query_b = f'inurl:"linkedin.com/posts/{username}"'
                print(f"DEBUG: Running Query B: {query_b}")
                results_b = ddgs.text(query_b, max_results=5)
                print(f"DEBUG: Results B: {results_b}")
                for r in results_b:
                    links.append(r['href'])

                # Strategy C: Blogs / Medium (New)
                # site:medium.com OR site:dev.to OR intitle:blog "Full Name"
                query_c = f'(site:medium.com OR site:dev.to OR intitle:blog) "{full_name}"'
                print(f"DEBUG: Running Query C: {query_c}")
                results_c = ddgs.text(query_c, max_results=5)
                print(f"DEBUG: Results C: {results_c}")
                for r in results_c:
                    links.append(r['href'])

                # Strategy D: School / Education (New)
                if education:
                    print(f"DEBUG: Education found: {education}")
                    for school in education:
                        query_d = f'site:linkedin.com "{full_name}" "{school}"'
                        print(f"DEBUG: Running Query D: {query_d}")
                        results_d = ddgs.text(query_d, max_results=3)
                        print(f"DEBUG: Results D: {results_d}")
                        for r in results_d:
                            links.append(r['href'])
                else:
                    print("DEBUG: No education data found for dorking.")

        except Exception as e:
            print(f"Error in DuckDuckGo Search: {e}")

        unique_links = list(set(links))
        print(f"DEBUG: Found {len(unique_links)} unique links: {unique_links}")
        return unique_links
