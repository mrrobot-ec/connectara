import requests
import json
import time

def verify_agent():
    url = "http://localhost:8000/messages/simulate"

    # Test 1: Chat
    print("--- Test 1: Chat ---")
    payload_chat = {
        "text": "Hello, who are you?",
        "from_phone": "+19176964972",
        "to_phone": "+10000000000"
    }
    try:
        response = requests.post(url, json=payload_chat)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")

    time.sleep(2)

    # Test 2: Find Matches
    print("\n--- Test 2: Find Matches ---")
    payload_match = {
        "text": "I want to find some matches please.",
        "from_phone": "+19176964972",
        "to_phone": "+10000000000"
    }
    try:
        response = requests.post(url, json=payload_match)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verify_agent()
