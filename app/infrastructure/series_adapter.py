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
