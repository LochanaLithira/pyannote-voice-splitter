import os
import zipfile
import tempfile
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from services.pyannote_service import get_job
from services.audio_service import slice_and_merge
from config import settings

router = APIRouter()


@router.get("/download/{job_id}/{speaker}")
async def download_speaker(job_id: str, speaker: str):
    job = get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found"
        )

    if job["status"] != "done":
        raise HTTPException(
            status_code=400,
            detail="Job is not done yet."
        )

    segments = job["segments"]
    original_path = job["original_path"]
    labels = job["labels"]

    speaker_segments = [s for s in segments if s["speaker"] == speaker]
    if not speaker_segments:
        raise HTTPException(
            status_code=404,
            detail=f"Speaker {speaker} not found in this job."
        )

    output_paths = slice_and_merge(job_id, original_path, segments)

    if speaker not in output_paths:
        raise HTTPException(
            status_code=500,
            detail="Audio export failed."
        )

    label = labels.get(speaker, speaker)
    filename = f"{label}.wav"

    return FileResponse(
        path=output_paths[speaker],
        media_type="audio/wav",
        filename=filename
    )


@router.get("/download/{job_id}")
async def download_all(job_id: str):
    job = get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found"
        )

    if job["status"] != "done":
        raise HTTPException(
            status_code=400,
            detail="Job is not done yet."
        )

    segments = job["segments"]
    original_path = job["original_path"]
    labels = job["labels"]

    output_paths = slice_and_merge(job_id, original_path, segments)

    zip_path = os.path.join(settings.tmp_dir, job_id, "all_speakers.zip")
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for speaker, path in output_paths.items():
            label = labels.get(speaker, speaker)
            zipf.write(path, arcname=f"{label}.wav")

    return FileResponse(
        path=zip_path,
        media_type="application/zip",
        filename="speakers.zip"
    )