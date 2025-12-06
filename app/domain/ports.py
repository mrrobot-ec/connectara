from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from app.domain.models import Profile, Person, AnalysisJob, JobStatus

class ProfileFetcher(ABC):
    @abstractmethod
    async def get_profile(self, username: str) -> Profile:
        """Fetch basic profile data from external source (e.g., Piloterr)."""
        pass

class DiscoveryService(ABC):
    @abstractmethod
    async def find_posts(self, full_name: str, username: str, education: List[str] = None) -> List[str]:
        """Find URLs of posts or articles using Dorking strategies."""
        pass

class RetrievalService(ABC):
    @abstractmethod
    async def fetch_content(self, urls: List[str]) -> List[str]:
        """Fetch content from multiple URLs."""
        pass

    @abstractmethod
    async def fetch_validated_content(self, urls: List[str], expected_name: str, expected_profile_url: str) -> List[str]:
        """Fetch and validate content from URLs, ensuring posts belong to the expected author."""
        pass

    @abstractmethod
    async def extract_content(self, url: str) -> Optional[str]:
        """Fetch content from a single URL."""
        pass

class PersonalityAnalyzer(ABC):
    @abstractmethod
    async def analyze(self, text: str) -> List[float]:
        """Analyze text and return 5-dimensional OCEAN vector."""
        pass

class TextEmbedder(ABC):
    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        """Generate semantic embedding for text."""
        pass

class SentimentAnalyzer(ABC):
    @abstractmethod
    async def analyze_sentiment(self, text: str) -> float:
        """Analyze sentiment of text and return score (-1.0 to 1.0)."""
        pass

class SocialGraph(ABC):
    @abstractmethod
    async def save_profile(self, person: Person) -> None:
        """Save person and their vector to the graph."""
        pass

    @abstractmethod
    async def get_person(self, username: str) -> Optional[Person]:
        """Get person by username."""
        pass

    @abstractmethod
    async def record_interaction(self, from_username: str, to_username: str, sentiment: float, text: str) -> None:
        """Record an interaction between two users with sentiment."""
        pass

class MessagingService(ABC):
    @abstractmethod
    async def create_chat(self, send_from: str, phone_numbers: List[str], message_text: str) -> Dict[str, Any]:
        """Create a new chat and send an initial message."""
        pass

    @abstractmethod
    async def send_message(self, chat_id: str, text: str) -> Dict[str, Any]:
        """Send a message to an existing chat."""
        pass

    @abstractmethod
    async def check_availability(self, phone_number: str) -> Dict[str, Any]:
        """Check if a phone number is iMessage available."""
        pass

class EventConsumer(ABC):
    @abstractmethod
    async def start(self):
        """Start the consumer loop."""
        pass

    @abstractmethod
    async def stop(self):
        """Stop the consumer loop."""
        pass

class JobRepository(ABC):
    @abstractmethod
    async def create_job(self, job: AnalysisJob) -> None:
        pass

    @abstractmethod
    async def get_job(self, job_id: str) -> Optional[AnalysisJob]:
        pass

    @abstractmethod
    async def update_job_status(self, job_id: str, status: JobStatus, result: Optional[Dict] = None, error: Optional[str] = None) -> None:
        pass
