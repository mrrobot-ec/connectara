from googlesearch import search
import time

def test_search():
    query = "hello world"
    print(f"Testing query: '{query}'")
    try:
        results = list(search(query, num_results=5, sleep_interval=1))
        print(f"Results found: {len(results)}")
        for r in results:
            print(f" - {r}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_search()
