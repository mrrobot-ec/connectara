import requests
import json

def verify_simulation():
    url = "http://localhost:8000/messages/simulate"
    payload = {
        "text": "Simulated message for graph verification",
        "from_phone": "+19176964972",
        "to_phone": "+10000000000"
    }

    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200:
            print("SUCCESS: Simulation endpoint triggered.")
        else:
            print("FAILURE: Endpoint returned error.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verify_simulation()
