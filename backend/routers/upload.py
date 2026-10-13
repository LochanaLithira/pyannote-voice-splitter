import asyncio
from fastapi import APIRouter, UploadFile, File, HTTPException
from models import UploadResponse
from services.pyannote_service import save_upload, run_diarization
from config import settings

router = APIRouter()

ALLOWED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".mp4", ".ogg", ".flac"}


@router.post("/upload", response_model=UploadResponse)
async def upload_audio(file: UploadFile = File(...)):
    ext = "." + file.filename.split(".")[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    file_bytes = await file.read()
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > settings.max_file_size_mb:
        raise HTTPException(
            status_code=400,
            detail=f"File too large: {size_mb:.1f}MB. Max allowed: {settings.max_file_size_mb}MB"
        )

    job_id, file_path = save_upload(file_bytes, file.filename)

    asyncio.create_task(run_diarization(job_id, file_path))

    return UploadResponse(
        job_id=job_id,
        message="File uploaded. Diarization started."
    )