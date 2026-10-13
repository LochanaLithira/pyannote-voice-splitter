from fastapi import APIRouter, HTTPException
from models import JobStatus
from services.pyannote_service import get_job

router = APIRouter()


@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    job = get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found"
        )

    return JobStatus(
        job_id=job_id,
        status=job["status"],
        speakers=job["speakers"],
        error=job.get("error"),
    )