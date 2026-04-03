import os
import zipfile
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from services.pyannote_service import get_job
from config import settings

router = APIRouter()


@router.get("/download/{job_id}/{speaker}")
async def download_speaker(job_id: str, speaker: str):
    job = get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job["status"] != "done":
        raise HTTPException(status_code=400, detail="Job is not done yet.")

    output_paths = job.get("output_paths", {})

    if not output_paths:
        raise HTTPException(status_code=404, detail="No processed files found for this job.")

    if speaker not in output_paths:
        raise HTTPException(status_code=404, detail=f"Speaker {speaker} not found.")

    path = output_paths[speaker]

    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Audio file not found on disk.")

    labels = job.get("labels", {})
    label = labels.get(speaker, speaker)

    return FileResponse(
        path=path,
        media_type="audio/wav",
        filename=f"{label}.wav",
    )


@router.get("/download/{job_id}")
async def download_all(job_id: str):
    job = get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job["status"] != "done":
        raise HTTPException(status_code=400, detail="Job is not done yet.")

    output_paths = job.get("output_paths", {})

    if not output_paths:
        raise HTTPException(status_code=404, detail="No processed files found for this job.")

    labels = job.get("labels", {})
    zip_path = os.path.join(settings.tmp_dir, job_id, "all_speakers.zip")

    with zipfile.ZipFile(zip_path, "w") as zipf:
        for speaker, path in output_paths.items():
            if os.path.exists(path):
                label = labels.get(speaker, speaker)
                zipf.write(path, arcname=f"{label}.wav")

    return FileResponse(
        path=zip_path,
        media_type="application/zip",
        filename="speakers.zip",
    )