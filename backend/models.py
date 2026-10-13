from pydantic import BaseModel
from typing import Optional

class UploadResponse(BaseModel):
    job_id: str
    message: str

class JobStatus(BaseModel):
    job_id: str
    status: str          # "processing" | "done" | "error"
    speakers: list[str] = []
    error: Optional[str] = None

class SpeakerLabel(BaseModel):
    job_id: str
    labels: dict[str, str]  # e.g. {"SPEAKER_00": "Agent", "SPEAKER_01": "Customer"}

class TranscriptTurn(BaseModel):
    speaker: str
    label: Optional[str]
    start: float
    end: float
    text: str