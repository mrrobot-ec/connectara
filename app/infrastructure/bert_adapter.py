from typing import List
from app.domain.ports import PersonalityAnalyzer
from transformers import BertTokenizer, BertForSequenceClassification
import torch
import numpy as np

class BertAdapter(PersonalityAnalyzer):
    def __init__(self):
        self.model_name = "Minej/bert-base-personality"
        try:
            self.tokenizer = BertTokenizer.from_pretrained(self.model_name)
            self.model = BertForSequenceClassification.from_pretrained(self.model_name)
            self.model.eval()
        except Exception as e:
            print(f"Error loading BERT model: {e}")
            self.model = None

    async def analyze(self, text: str) -> List[float]:
        if not self.model or not text:
            return [0.0, 0.0, 0.0, 0.0, 0.0]

        try:
            # Tokenize and predict
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512, padding=True)
            with torch.no_grad():
                outputs = self.model(**inputs)

            # The model outputs raw logits. We typically normalize them or use them as is depending on the specific model's training.
            # For this specific model, let's assume logits correspond to the 5 traits.
            # We can apply sigmoid or just return logits if they are regression outputs.
            # Checking model config usually helps, but for now we'll return the raw logits as the vector.
            predictions = outputs.logits.squeeze().tolist()

            # Ensure we have 5 dimensions
            if len(predictions) != 5:
                 # Fallback if model output is different
                 return predictions[:5] if len(predictions) > 5 else predictions + [0.0] * (5 - len(predictions))

            return predictions
        except Exception as e:
            print(f"Error in Personality Analysis: {e}")
            return [0.0, 0.0, 0.0, 0.0, 0.0]
