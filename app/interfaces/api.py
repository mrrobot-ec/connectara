from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from dependency_injector.wiring import inject, Provide
from app.containers import Container
from app.use_cases.analyze_profile import AnalyzeProfileUseCase
from app.use_cases.find_matches import FindMatchesUseCase
from app.domain.ports import JobRepository
from app.domain.models import AnalysisJob
from pydantic import BaseModel
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

class AnalyzeRequest(BaseModel):
    username: str

@router.post("/analyze")
@inject
async def analyze_profile(
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    use_case: AnalyzeProfileUseCase = Depends(Provide[Container.analyze_profile_use_case]),
    job_repo: JobRepository = Depends(Provide[Container.neo4j_adapter])
):
    # Create Job
    job = AnalysisJob(username=request.username)
    await job_repo.create_job(job)

    # Trigger Background Task
    background_tasks.add_task(use_case.execute, job.job_id, request.username)

    return {"job_id": job.job_id, "status": "PENDING"}

@router.get("/jobs/{job_id}")
@inject
async def get_job_status(
    job_id: str,
    job_repository: JobRepository = Depends(Provide[Container.neo4j_adapter])
):
    job = await job_repository.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job

@router.get("/matches/{username}")
@inject
async def find_matches(
    username: str,
    k: int = 10,
    use_case: FindMatchesUseCase = Depends(Provide[Container.find_matches_use_case])
):
    try:
        result = await use_case.execute(username, k)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
def health_check():
    return {"status": "ok"}

class LinkPhoneRequest(BaseModel):
    username: str
    phone_number: str

@router.post("/link-phone")
@inject
async def link_phone(
    request: LinkPhoneRequest,
    social_graph: JobRepository = Depends(Provide[Container.neo4j_adapter])
):
    # Note: Neo4jAdapter implements both JobRepository and SocialGraph
    # We are injecting it as JobRepository but it has the method.
    # Ideally we should inject as SocialGraph or a combined interface.
    # For now, we rely on the implementation.
    if not hasattr(social_graph, 'link_phone_to_user'):
         raise HTTPException(status_code=500, detail="Service does not support phone linking")

    success = await social_graph.link_phone_to_user(request.username, request.phone_number)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "linked", "username": request.username, "phone_number": request.phone_number}

from app.use_cases.messaging import ReceiveMessageUseCase

class SimulateMessageRequest(BaseModel):
    text: str
    from_phone: str
    to_phone: str

@router.post("/messages/simulate")
@inject
async def simulate_message(
    request: SimulateMessageRequest,
    use_case: ReceiveMessageUseCase = Depends(Provide[Container.receive_message_use_case])
):
    """
    Simulate an incoming Kafka message to trigger the full processing pipeline
    (Sentiment Analysis -> Graph Update).
    """
    # Construct a payload that mimics the Kafka message structure
    event = {
        "event_type": "message.received",
        "data": {
            "text": request.text,
            "chat_id": "simulated-chat-id",
            "from_phone": request.from_phone,
            "chat_handles": [
                {"identifier": request.from_phone, "is_me": False},
                {"identifier": request.to_phone, "is_me": True}
            ]
        }
    }
    
    logger.info(f"Simulating message from {request.from_phone}: {request.text}")
    
    # Reuse the existing use case logic
    await use_case.execute(event)
    
    return {"status": "simulated", "payload": event}
