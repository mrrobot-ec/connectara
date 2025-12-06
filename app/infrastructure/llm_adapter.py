import httpx
from app.domain.ports import LLMService
from typing import Dict, Any
import os
import logging
import json

logger = logging.getLogger(__name__)

class GeminiLLMAdapter(LLMService):
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            logger.warning("GOOGLE_API_KEY not found. LLM features will not work.")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"

    async def generate_response(self, prompt: str, context: Dict[str, Any] = None) -> str:
        if not self.api_key:
            return "I'm sorry, I cannot process your request right now (Missing API Key)."

        try:
            # Construct a prompt with context
            full_prompt = prompt
            if context:
                context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
                full_prompt = f"Context:\n{context_str}\n\nUser Message: {prompt}"

            headers = {
                "Content-Type": "application/json"
            }
            params = {
                "key": self.api_key
            }
            payload = {
                "contents": [{
                    "parts": [{"text": full_prompt}]
                }]
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(self.base_url, headers=headers, params=params, json=payload, timeout=30.0)

                if response.status_code != 200:
                    logger.error(f"Gemini API Error: {response.status_code} - {response.text}")
                    return "I'm having trouble thinking right now. Please try again later."

                data = response.json()
                # Extract text from response
                # Response structure: candidates[0].content.parts[0].text
                try:
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    return text
                except (KeyError, IndexError) as e:
                    logger.error(f"Failed to parse Gemini response: {data}")
                    return "I'm having trouble understanding the response. Please try again."

        except Exception as e:
            logger.error(f"Gemini LLM Error: {e}")
            return "I'm having trouble thinking right now. Please try again later."
