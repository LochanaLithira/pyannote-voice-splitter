import os
import time
import requests
from config import settings

AUDO_BASE_URL = "https://api.audo.ai/v1"
HEADERS = {"x-api-key": settings.audo_api_key}


def denoise_audio(input_path: str, passes: int = 1) -> str:
    if passes < 1:
        raise ValueError("passes must be >= 1")

    for pass_num in range(1, passes + 1):
        print(f"[Audo AI] Pass {pass_num}/{passes} for {input_path}")
        _run_single_denoise_pass(input_path)

    return input_path


def _run_single_denoise_pass(input_path: str) -> str:
    print(f"[Audo AI] Uploading {input_path}...")

    # Step 1 — Upload file to Audo AI
    with open(input_path, "rb") as f:
        upload_response = requests.post(
            f"{AUDO_BASE_URL}/upload",
            headers=HEADERS,
            files={"file": f},
        )

    if upload_response.status_code != 200:
        raise Exception(f"Audo AI upload failed: {upload_response.text}")

    file_id = upload_response.json()["fileId"]
    print(f"[Audo AI] Uploaded. fileId={file_id}")

    # Step 2 — Submit noise removal job
    # noiseReductionAmount: 100 = full removal (default), lower = gentler
    job_response = requests.post(
        f"{AUDO_BASE_URL}/remove-noise",
        headers={**HEADERS, "Content-Type": "application/json"},
        json={
            "input": file_id,
            "outputExtension": "wav",
            "noiseReductionAmount": 100,
        },
    )

    if job_response.status_code != 200:
        raise Exception(f"Audo AI job submission failed: {job_response.text}")

    job_id = job_response.json()["jobId"]
    print(f"[Audo AI] Job submitted. jobId={job_id}")

    # Step 3 — Poll until done
    download_path = _poll_until_done(job_id)

    # Step 4 — Download cleaned file and overwrite the original
    _download_file(download_path, input_path)
    print(f"[Audo AI] Done. Clean file saved to {input_path}")

    return input_path


def _poll_until_done(job_id: str, max_wait_seconds: int = 300) -> str:
    status_url = f"{AUDO_BASE_URL}/remove-noise/{job_id}/status"
    elapsed = 0
    poll_interval = 3

    while elapsed < max_wait_seconds:
        response = requests.get(status_url, headers=HEADERS)

        if response.status_code != 200:
            raise Exception(f"Audo AI status check failed: {response.text}")

        data = response.json()
        state = data.get("state")

        print(f"[Audo AI] Status: {state} {data.get('percent', '')} {data.get('jobsAhead', '')}")

        if state == "succeeded":
            return data["downloadPath"]

        if state == "failed":
            raise Exception(f"Audo AI job failed: {data.get('reason', 'unknown')}")

        time.sleep(poll_interval)
        elapsed += poll_interval

    raise Exception("Audo AI job timed out after 5 minutes")


def _download_file(download_path: str, save_to: str):
    url = f"{AUDO_BASE_URL}/{download_path}"
    response = requests.get(url, headers=HEADERS)

    if response.status_code != 200:
        raise Exception(f"Audo AI download failed: {response.text}")

    with open(save_to, "wb") as f:
        f.write(response.content)