import asyncio
from playwright.async_api import async_playwright, Browser, TimeoutError as PlaywrightTimeoutError
import time
import pathlib
from bs4 import BeautifulSoup
from typing import Any, List
import os, json, requests
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, urlunparse

from src import env_path

load_dotenv(env_path)
assert os.getenv("SERP_TOKEN") is not None, "SERP_TOKEN not set in environment"
"""
1) Get posts similar to the name    
2) validate for each post that the author is the same as the name as the initial target
3) return post details for validated posts
"""

def truncate_parameters(url: str) -> str:
    """
    Normalize LinkedIn URLs to format: https://www.linkedin.com/in/username
    - Remove query parameters and fragments
    - Normalize all subdomains to 'www.linkedin.com'
    - Keep https scheme and path
    """
    parsed = urlparse(url)
    
    # Normalize LinkedIn subdomains to www.linkedin.com
    netloc = parsed.netloc
    if 'linkedin.com' in netloc:
        netloc = 'www.linkedin.com'
    
    # Keep https, normalized netloc, and path only; drop params, query, fragment
    return urlunparse(('https', netloc, parsed.path, '', '', ''))

def get_all_post_details(name: str, linkedin_profile_url: str) -> List[str]:
    return asyncio.run(_get_all_post_details(name, linkedin_profile_url))


async def _get_all_post_details(name: str, linkedin_profile_url: str) -> List[str]:
    post_urls = get_posts_similar_to_fullname(name)
    if not post_urls:
        return []

    valid_posts: List[str] = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        tasks = [headless_browse(url, browser) for url in post_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for url, result in zip(post_urls, results):
            if isinstance(result, Exception):
                print(f"[error] Failed to process {url}: {result}")
                continue
            post_text, author_name, author_linkedin_url = result # type: ignore
            if not all([post_text, author_name, author_linkedin_url]):
                print(f"[warn] Incomplete data for post {url}, skipping...")
                continue
            elif author_name and author_name.lower() == name.lower():
                if author_linkedin_url and truncate_parameters(author_linkedin_url.lower()) == linkedin_profile_url.lower():
                    valid_posts.append(post_text) # type: ignore
                    print(f"[info] Validated post from {author_name} at {author_linkedin_url}")
                # else:
                #     print(f"[warn] Author LinkedIn URL mismatch for post at {truncate_parameters(author_linkedin_url)}, skipping...") # type: ignore
        await browser.close()

    print(f"[info] Retrieved {len(valid_posts)} valid posts out of {len(post_urls)} total posts found.")
    return valid_posts


async def headless_browse(url: str, browser: Browser, screenshot_name: str | None = None):
    if screenshot_name is None:
        screenshot_name = f"screenshot_{int(time.time())}.png"

    context = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1280, "height": 720},
    )
    page = await context.new_page()

    print(f"Navigating to: {url}")
    await page.goto(url, wait_until="domcontentloaded", timeout=60_000)

    try:
        await page.wait_for_load_state("networkidle", timeout=10_000)
    except PlaywrightTimeoutError:
        print("[warn] networkidle not reached, continuing anyway...")

    await page.wait_for_timeout(750)

    html = await page.content()
    await context.close()

    return getPostDetails(html) 

def get_posts_similar_to_fullname(full_name: str):
    # Load the HTML dump
    url = "https://serpapi.com/search"
    query = 'site:linkedin.com inurl:"/posts/" intext:"' + full_name + '"'
    
    params = {
        'q': query,
        'api_key': os.getenv('SERP_TOKEN'), 
    }

    response = requests.get(url, params=params).json()
    with open("serp_result.json", "w", encoding="utf-8") as f:
        json.dump(response, f, indent=2)

        all_posts = []
        first_page_results = response.get("organic_results", [])
        
        if "serpapi_pagination" in response:
            pagination = response["serpapi_pagination"]
            other_pages = pagination.get("other_pages") or {}
            
            if other_pages:
                api_key = params.get("api_key")
                page_results = {}
                
                def fetch_page(page_num: str, page_url: str):
                    query_params = {} if not api_key or "api_key=" in page_url else {"api_key": api_key}
                    page_response = requests.get(page_url, params=query_params, timeout=15)
                    page_response.raise_for_status()
                    data = page_response.json()
                    return int(page_num), data.get("organic_results", [])
                
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
    
    # Filter out non-post URLs (directories, search pages, etc.)
    valid_post_urls = []
    for x in all_posts:
        link = x.get("link")
        if link and "/posts/" in link:
            valid_post_urls.append(link)
    
    return valid_post_urls

def getPostDetails(html: str)-> tuple[str | None, str | None, str | None]:
    post_text, author_name, author_linkedin_url = None, None, None
    try:
        # Load the HTML dump
        soup = BeautifulSoup(html, "html.parser")

        # find post description
        mb3_sections = soup.find_all("section", class_="mb-3")
        if not mb3_sections:
            raise ValueError("No sections with class 'mb-3' found")
        
        mb3_section = mb3_sections[0]
        articles = mb3_section.find_all("article")
        if not articles:
            raise ValueError("No article found in section")
        
        article = articles[0]
        p_tag = article.find("p")
        post_text = p_tag.get_text(strip=True) if p_tag else None

        # author name
        author_flexboxes = article.find_all("div", class_="flex")
        if not author_flexboxes:
            raise ValueError("No flex divs found for author")
        
        author_flexbox = author_flexboxes[0]
        author_links = author_flexbox.find_all('a', attrs={'data-tracking-control-name': 'public_post_feed-actor-name'})
        author_name = author_links[0].get_text(strip=True) if author_links else None

        # linkedin profile
        author_linkedin_url = author_links[0]['href'] if author_links and 'href' in author_links[0].attrs else None
    except Exception as e:
        print(f"[error] Exception in getPostDetails: {e}")
        
    return post_text, author_name, author_linkedin_url # type: ignore
    
posts = get_all_post_details("Andres Campoverde", "https://www.linkedin.com/in/itsandres") 
with open("posts.json", "w", encoding="utf-8") as f:
    for post in posts:
        f.write(post + "\n")
