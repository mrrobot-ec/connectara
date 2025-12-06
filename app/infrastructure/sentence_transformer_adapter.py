from typing import List
from app.domain.ports import TextEmbedder
from sentence_transformers import SentenceTransformer
import asyncio

class SentenceTransformerAdapter(TextEmbedder):
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        # Load model (this might take a moment on first run)
        self.model = SentenceTransformer(model_name)

    async def embed(self, text: str) -> List[float]:
        # Run in executor to avoid blocking event loop
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(None, self.model.encode, text)
        return embedding.tolist()
