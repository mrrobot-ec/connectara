import requests
import time

BASE_URL = "http://localhost:8000"
USERNAME = "test_user_linking"
PHONE = "+15550001111"

def test_phone_linking():
    # 1. Create User (via Analyze - this creates the Person node)
    print(f"1. Creating user {USERNAME}...")
    resp = requests.post(f"{BASE_URL}/analyze", json={"username": USERNAME})
    if resp.status_code != 200:
        print(f"Failed to create user: {resp.text}")
        return

    # Wait for analysis to potentially create the node (it happens in background)
    # But actually, analyze_profile creates a Job, and the background task creates the Person node eventually.
    # To be sure, we can manually create the node via Neo4j if needed, or wait.
    # Let's assume the background task runs fast enough or we can retry linking.
    time.sleep(5)

    # 2. Link Phone
    print(f"2. Linking phone {PHONE} to {USERNAME}...")
    resp = requests.post(f"{BASE_URL}/link-phone", json={"username": USERNAME, "phone_number": PHONE})
    print(f"Link response: {resp.status_code} - {resp.text}")

    if resp.status_code == 200:
        print("SUCCESS: Phone linked.")
    else:
        print("FAILURE: Could not link phone.")

if __name__ == "__main__":
    test_phone_linking()
