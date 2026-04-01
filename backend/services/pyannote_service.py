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
        import requests
        import uuid

        headers = {
            "Authorization": f"Bearer {settings.pyannote_api_key}",
            "Content-Type": "application/json",
        }

        # Step 1 — request a pre-signed PUT URL from pyannoteAI
        object_key = f"job-{uuid.uuid4().hex}"
        media_response = requests.post(
            "https://api.pyannote.ai/v1/media/input",
            headers=headers,
            json={"url": f"media://{object_key}"},
        )

        if media_response.status_code not in (200, 201):
            raise Exception(f"Failed to get upload URL: {media_response.text}")

        presigned_url = media_response.json()["url"]

        # Step 2 — upload the actual file to the pre-signed URL
        with open(file_path, "rb") as f:
            put_response = requests.put(
                presigned_url,
                data=f,
                headers={"Content-Type": "application/octet-stream"},
            )

        if put_response.status_code not in (200, 201, 204):
            raise Exception(f"File upload failed: {put_response.text}")

        # Step 3 — submit diarization job using the media:// key
        pyannote_job_id = client.diarize(
            f"media://{object_key}",
            transcription=True,
        )
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