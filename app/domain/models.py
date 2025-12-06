from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
import uuid

class JobStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Profile(BaseModel):
    """Value Object representing raw profile data."""
    username: str
    full_name: Optional[str] = None
    headline: Optional[str] = None
    summary: Optional[str] = None
    location: Optional[str] = None
    education: Optional[List[str]] = Field(default_factory=list)
    profile_url: Optional[str] = None
    raw_data: Dict[str, Any] = Field(default_factory=dict)

class Person(BaseModel):
    """Entity representing a Person in the social graph."""
    username: str
    phone_number: Optional[str] = None
    profile: Profile
    ocean_vector: Optional[List[float]] = None # [O, C, E, A, N]
    content_embedding: Optional[List[float]] = None # Semantic embedding of summary + posts
    posts: List[str] = Field(default_factory=list)
    personality_analysis: Optional[str] = None

class AnalysisJob(BaseModel):
    """Entity representing an asynchronous analysis job."""
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    status: JobStatus = JobStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
