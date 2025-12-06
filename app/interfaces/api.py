from fastapi import FastAPI, Depends, BackgroundTasks, HTTPException
from dependency_injector.wiring import inject, Provide
from app.containers import Container
from app.use_cases.analyze_profile import AnalyzeProfileUseCase
from app.use_cases.find_matches import FindMatchesUseCase
from app.domain.ports import JobRepository
from app.domain.models import AnalysisJob
from pydantic import BaseModel

app = FastAPI()

class AnalyzeRequest(BaseModel):
    username: str

@app.post("/analyze")
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

@app.get("/jobs/{job_id}")
@inject
async def get_job_status(
    job_id: str,
    job_repository: JobRepository = Depends(Provide[Container.neo4j_adapter])
):
    job = await job_repository.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job

@app.get("/matches/{username}")
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

@app.get("/health")
def health_check():
    return {"status": "ok"}
