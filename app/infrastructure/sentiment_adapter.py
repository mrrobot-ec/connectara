from app.domain.ports import SentimentAnalyzer
from transformers import pipeline
import asyncio

class SentimentAdapter(SentimentAnalyzer):
    def __init__(self, model_name: str = "distilbert-base-uncased-finetuned-sst-2-english"):
        # Load pipeline (downloads model on first run)
        self.pipeline = pipeline("sentiment-analysis", model=model_name)

    async def analyze_sentiment(self, text: str) -> float:
        # Run in executor
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self.pipeline, text)

        # Result format: [{'label': 'POSITIVE', 'score': 0.99}]
        label = result[0]['label']
        score = result[0]['score']

        # Normalize to -1.0 (Negative) to 1.0 (Positive)
        if label == 'NEGATIVE':
            return -score
        else:
            return score
