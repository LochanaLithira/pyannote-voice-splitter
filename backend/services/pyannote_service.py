import os
import uuid
import shutil
from pyannoteai.sdk import Client
import warnings
from config import settings
from services.denoise_service import denoise_audio
from services.audio_service import slice_and_merge

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
        "confidence_data": {},  # sample-level confidence from pyannoteAI
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

        # Stage 1 — Denoise the full mixed audio first
        print(
            f"[{job_id}] Stage 1: Denoising full audio with "
            f"{settings.full_audio_denoise_passes} pass(es) before diarization..."
        )
        file_path = denoise_audio(file_path, passes=settings.full_audio_denoise_passes)
        print(f"[{job_id}] Stage 1 complete.")

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

        # Step 3 — submit diarization job
        # - exclusive=True → get exclusiveDiarization (no-overlap segments for slicing)
        # - confidence=True → get sample-level confidence array (20ms resolution)
        #   Used to identify low-confidence (ambiguous/overlapping) regions precisely
        # - turnLevelConfidence=True → per-turn confidence scores for guard-size decisions
        diarize_kwargs = {
            "model": "precision-2",
            "transcription": True,
            "exclusive": True,
            "num_speakers": 2,
            "turn_level_confidence": True,
            "confidence": settings.use_sample_confidence,  # sample-level scores array
        }

        try:
            pyannote_job_id = client.diarize(
                f"media://{object_key}",
                **diarize_kwargs,
            )
        except TypeError:
            # Older SDK versions may not support all kwargs — retry without confidence
            diarize_kwargs.pop("confidence", None)
            pyannote_job_id = client.diarize(
                f"media://{object_key}",
                **diarize_kwargs,
            )

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            result = client.retrieve(pyannote_job_id)

        output = result.get("output", {})

        # exclusiveDiarization: non-overlapping segments used for audio slicing
        segments = output.get("exclusiveDiarization", [])

        # diarization: raw segments WITH overlaps, used as confidence source
        # (these share the same timestamps as the turnLevelConfidence values)
        diarization_segments = output.get("diarization", [])

        # --- FIX: Enrich diarization segments (not exclusive segments) with confidence ---
        # The previous code tried to match exclusiveDiarization timestamps against
        # diarization timestamps — they differ, so matching always failed.
        # Correct approach: enrich diarization segments directly (same timestamps).
        confidence_by_key: dict[tuple[str, int, int], dict] = {}
        for seg in diarization_segments:
            speaker = seg.get("speaker")
            start = seg.get("start")
            end = seg.get("end")
            if speaker is None or start is None or end is None:
                continue
            key = (speaker, int(float(start) * 1000), int(float(end) * 1000))
            confidence = seg.get("confidence")
            if isinstance(confidence, (dict, int, float)):
                confidence_by_key[key] = {"confidence": confidence}

        # Apply enrichment to diarization_segments (source of truth for confidence)
        if confidence_by_key:
            enriched_diarization: list[dict] = []
            for seg in diarization_segments:
                speaker = seg.get("speaker")
                start = seg.get("start")
                end = seg.get("end")
                if speaker is None or start is None or end is None:
                    enriched_diarization.append(seg)
                    continue
                key = (speaker, int(float(start) * 1000), int(float(end) * 1000))
                extra = confidence_by_key.get(key)
                enriched_diarization.append({**seg, **extra} if extra else seg)
            diarization_segments = enriched_diarization

        # Sample-level confidence array: {score: [...], resolution: 0.02}
        # Low-confidence samples correspond to contested/overlapping regions
        confidence_data = output.get("confidence", {})
        if confidence_data:
            num_samples = len(confidence_data.get("score", []))
            resolution = confidence_data.get("resolution", 0.02)
            print(
                f"[{job_id}] sample-level confidence: {num_samples} samples "
                f"at {resolution}s resolution"
            )
        else:
            print(f"[{job_id}] No sample-level confidence data returned by API.")

        transcript = output.get("turnLevelTranscription", [])
        speakers = list({seg["speaker"] for seg in segments})

        job_store[job_id]["segments"] = segments
        job_store[job_id]["diarization_segments"] = diarization_segments
        job_store[job_id]["transcript"] = transcript
        job_store[job_id]["speakers"] = sorted(speakers)
        job_store[job_id]["confidence_data"] = confidence_data

        output_paths = slice_and_merge(
            job_id,
            file_path,
            segments,
            diarization_segments=diarization_segments,
            confidence_data=confidence_data,
        )
        job_store[job_id]["output_paths"] = output_paths

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