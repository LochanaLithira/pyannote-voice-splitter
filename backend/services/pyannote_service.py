import os
import uuid
import shutil
from pyannoteai.sdk import Client
from config import settings

client = Client(settings.pyannote_api_key)

job_store: dict[str, dict] = {}


def create_job_entry(job_id: str, original_path: str):
    job_store[job_id] = {
        "status": "processing",
        "original_path": original_path,
        "speakers": [],
        "segments": [],
        "transcript": [],
        "labels": {},
        "error": None,
    }


def get_job(job_id: str) -> dict | None:
    return job_store.get(job_id)


def save_upload(file_bytes: bytes, filename: str) -> tuple[str, str]:
    job_id = str(uuid.uuid4())
    job_dir = os.path.join(settings.tmp_dir, job_id)
    os.makedirs(job_dir, exist_ok=True)

    original_path = os.path.join(job_dir, filename)
    with open(original_path, "wb") as f:
        f.write(file_bytes)

    create_job_entry(job_id, original_path)
    return job_id, original_path


async def run_diarization(job_id: str, file_path: str):
    try:
        pyannote_job_id = client.diarize(file_path, transcription=True)
        result = client.retrieve(pyannote_job_id)

        segments = result["output"].get("diarization", [])
        transcript = result["output"].get("turnLevelTranscription", [])

        speakers = list({seg["speaker"] for seg in segments})

        job_store[job_id]["segments"] = segments
        job_store[job_id]["transcript"] = transcript
        job_store[job_id]["speakers"] = sorted(speakers)
        job_store[job_id]["status"] = "done"

    except Exception as e:
        job_store[job_id]["status"] = "error"
        job_store[job_id]["error"] = str(e)


def set_labels(job_id: str, labels: dict[str, str]):
    job_store[job_id]["labels"] = labels


def cleanup_job(job_id: str):
    job_dir = os.path.join(settings.tmp_dir, job_id)
    if os.path.exists(job_dir):
        shutil.rmtree(job_dir)
    job_store.pop(job_id, None)