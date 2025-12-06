from typing import List
from app.domain.ports import DiscoveryService
from googleapiclient.discovery import build
import os

class GoogleSearchAdapter(DiscoveryService):
    def __init__(self, api_key: str = None, cse_id: str = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.cse_id = cse_id or os.getenv("SEARCH_ENGINE_ID")
        self.service = None
        if self.api_key and self.cse_id:
            self.service = build("customsearch", "v1", developerKey=self.api_key)

    async def find_posts(self, full_name: str, username: str, education: List[str] = None) -> List[str]:
        if not self.service:
            print("Google Search API not configured. Returning empty list.")
            return []

        links = []
        print(f"Dorking with Google API for {full_name}...")

        # Helper to run query
        def run_query(query, label):
            print(f"DEBUG: Running Google Query {label}: {query}")
            try:
                res = self.service.cse().list(q=query, cx=self.cse_id).execute()
                items = res.get("items", [])
                print(f"DEBUG: Results {label}: {[i['link'] for i in items]}")
                for item in items:
                    links.append(item["link"])
            except Exception as e:
                print(f"Error in Google Dorking {label}: {e}")

        # Strategy A: Profile/Article Find
        # site:linkedin.com/in/username
        run_query(f'site:linkedin.com/in/{username}', "A")

        # Strategy B: Direct Post Find
        # inurl:"linkedin.com/posts/username"
        run_query(f'inurl:"linkedin.com/posts/{username}"', "B")

        # Strategy C: Blogs / Medium
        # (site:medium.com OR site:dev.to OR intitle:blog) "Full Name"
        run_query(f'(site:medium.com OR site:dev.to OR intitle:blog) "{full_name}"', "C")

        # Strategy D: School / Education
        if education:
            print(f"DEBUG: Education found: {education}")
            for school in education:
                run_query(f'site:linkedin.com "{full_name}" "{school}"', "D")
        else:
            print("DEBUG: No education data found for dorking.")

        # Strict Filtering
        # We only want posts authored by the user.
        # LinkedIn Post URLs format: https://www.linkedin.com/posts/username_slug-activity-...
        filtered_links = []
        for link in set(links):
            # Check if it's a direct post by the user
            if f"linkedin.com/posts/{username}" in link:
                filtered_links.append(link)
            # Check if it's an article/pulse by the user
            elif f"linkedin.com/pulse/" in link and username in link:
                filtered_links.append(link)
            # Keep profile links (Strategy A)
            elif f"linkedin.com/in/{username}" in link:
                filtered_links.append(link)
            else:
                print(f"DEBUG: Filtered out (not strict match): {link}")

        print(f"DEBUG: Found {len(filtered_links)} unique strict links: {filtered_links}")
        return filtered_links
