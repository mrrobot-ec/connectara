from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
from sentence_transformers import SentenceTransformer
import os

def download_models():
    print("Downloading Sentiment Analysis Model...")
    # distilbert-base-uncased-finetuned-sst-2-english
    pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")

    print("Downloading Sentence Transformer Model...")
    # all-MiniLM-L6-v2
    SentenceTransformer("all-MiniLM-L6-v2")

    print("Downloading Personality Model...")
    # Minej/bert-base-personality
    model_name = "Minej/bert-base-personality"
    AutoTokenizer.from_pretrained(model_name)
    AutoModelForSequenceClassification.from_pretrained(model_name)

    print("All models downloaded and cached.")

if __name__ == "__main__":
    download_models()
