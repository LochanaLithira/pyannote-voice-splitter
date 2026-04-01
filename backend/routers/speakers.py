from fastapi import APIRouter, HTTPException
from models import SpeakerLabel, TranscriptTurn
from services.pyannote_service import get_job, set_labels
from services.transcript_service import get_transcript

router = APIRouter()


@router.post("/speakers/rename")
async def rename_speakers(payload: SpeakerLabel):
    job = get_job(payload.job_id)

    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job {payload.job_id} not found"
        )

    if job["status"] != "done":
        raise HTTPException(
            status_code=400,
            detail="Job is not done yet. Wait for diarization to complete before renaming."
        )

    set_labels(payload.job_id, payload.labels)

    return {
        "message": "Speaker labels updated",
        "labels": payload.labels
    }


@router.get("/transcript/{job_id}", response_model=list[TranscriptTurn])
async def get_job_transcript(job_id: str):
    job = get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found"
        )

    if job["status"] != "done":
        raise HTTPException(
            status_code=400,
            detail="Transcript not ready yet."
        )

    turns = get_transcript(job_id)

    if not turns:
        raise HTTPException(
            status_code=404,
            detail="No transcript found for this job. Make sure transcription was enabled."
        )

    return turns