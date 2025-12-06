from duckduckgo_search import DDGS

def test_ddg():
    query = "hello world"
    print(f"Testing DDG query: '{query}'")
    try:
        ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        with DDGS(headers={"User-Agent": ua}) as ddgs:
            print("Trying backend='api' with UA...")
            results = list(ddgs.text(query, max_results=5))
            print(f"API Results: {len(results)}")

            print("Trying backend='html' with UA...")
            results_html = list(ddgs.text(query, backend="html", max_results=5))
            print(f"HTML Results: {len(results_html)}")
            for r in results_html:
                print(f" - {r}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_ddg()
