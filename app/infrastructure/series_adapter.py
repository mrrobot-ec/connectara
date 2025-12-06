import httpx
from typing import List, Dict, Any
from app.domain.ports import MessagingService
import os

class SeriesMessagingAdapter(MessagingService):
    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or os.getenv("SERIES_API_KEY")
        self.base_url = base_url or os.getenv("SERIES_API_BASE_URL")

        if not self.api_key:
            raise ValueError("SERIES_API_KEY is not set")
        if not self.base_url:
            raise ValueError("SERIES_API_BASE_URL is not set")

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def create_chat(self, send_from: str, phone_numbers: List[str], message_text: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/chats"
        payload = {
            "send_from": send_from,
            "chat": {
                "phone_numbers": phone_numbers
            },
            "message": {
                "text": message_text
            }
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json()

    async def send_message(self, chat_id: str, text: str) -> Dict[str, Any]:
        if chat_id == "simulated-chat-id":
            print(f"MOCK SEND MESSAGE to {chat_id}: {text}")
            return {"id": "mock-message-id", "text": text}

        url = f"{self.base_url}/api/chats/{chat_id}/chat_messages"
        payload = {
            "message": {
                "text": text
            }
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json()

    async def check_availability(self, phone_number: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/i_message_availability/check"
        payload = {
            "phone_number": phone_number
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json()

    async def mark_as_read(self, chat_id: str) -> None:
        if chat_id == "simulated-chat-id":
            return

        url = f"{self.base_url}/api/chats/{chat_id}/mark_as_read"
        async with httpx.AsyncClient() as client:
            response = await client.put(url, headers=self.headers)
            # The docs say 204 No Content (success) or 422 if failed.
            # raise_for_status will handle 4xx/5xx
            response.raise_for_status()

    async def get_chat_messages(self, chat_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        if chat_id == "simulated-chat-id":
            return []

        url = f"{self.base_url}/api/chats/{chat_id}/chat_messages"
        params = {"per_page": limit, "page": 1} # Assuming API supports pagination like this based on List Chats
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            # The API returns a list of messages directly or a paginated object?
            # Docs say: "Response: 200 OK with messages."
            # List Chats says "paginated chat list".
            # Let's assume it returns a list or a dict with 'messages'.
            # Based on standard Series API patterns, it might be a list.
            # If it's a dict with 'data', we'll handle it.
            if isinstance(data, dict) and 'data' in data:
                return data['data']
            if isinstance(data, list):
                return data
            return []
