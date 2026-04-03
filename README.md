# pyannote-voice-splitter

FastAPI + React (Vite) app that:

- Accepts an uploaded call recording
- Sends it to pyannoteAI for **speaker diarization** + **turn-level transcription**
- Lets you **rename speakers** and **download per-speaker WAVs** (or a ZIP of all speakers)

## Project layout

- `backend/` — FastAPI API server, diarization/transcription + audio export
- `frontend/` — React UI (Vite + Tailwind)

## Prerequisites

Backend:

- Python 3.10+ recommended
- A pyannoteAI API key
- FFmpeg available on your PATH (required by `pydub` for formats like mp3/m4a/mp4/ogg/flac; WAV often works without it)

Frontend:

- Node.js 18+ recommended

## Quickstart (dev)

### 1) Backend (FastAPI)

From the repo root:

PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

cmd.exe:

```bat
cd backend
python -m venv .venv
.\.venv\Scripts\activate.bat
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Environment variables (loaded from `backend/.env` when you run from the `backend/` directory):

```env
PYANNOTE_API_KEY=your_key_here
AUDO_API_KEY=your_key_here
TMP_DIR=./tmp
MAX_FILE_SIZE_MB=200
FULL_AUDIO_DENOISE_PASSES=1
SPLIT_AUDIO_DENOISE_PASSES=2
DROP_OVERLAP_AUDIO=true
OVERLAP_GUARD_MS=500
CONFIDENCE_AWARE_OVERLAP_DROP=true
OVERLAP_CONFIDENCE_THRESHOLD=75
HIGH_CONFIDENCE_OVERLAP_GUARD_MS=120
SEGMENT_EDGE_TRIM_MS=120
DROP_LOW_CONFIDENCE_TURNS=false
MIN_TURN_CONFIDENCE_TO_KEEP=65
MIN_CLEAN_SEGMENT_MS=120
```

Notes:

- The backend stores jobs **in memory** (a process restart loses all job state).

### 2) Frontend (React + Vite)

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

By default, the UI calls `http://localhost:8000`.

To point the UI at a different backend, set `VITE_API_BASE_URL`:

PowerShell:

```powershell
$env:VITE_API_BASE_URL = "http://localhost:8000"
npm run dev
```

cmd.exe:

```bat
set VITE_API_BASE_URL=http://localhost:8000
npm run dev
```

The backend CORS settings currently allow `http://localhost:5173` (Vite default). If you change the frontend origin, update `backend/main.py` accordingly.

## API overview

All routes are prefixed with `/api`.

### Upload

`POST /api/upload`

- Form-data field: `file`
- Allowed extensions: `.wav`, `.mp3`, `.m4a`, `.mp4`, `.ogg`, `.flac`
- Max size is controlled by `MAX_FILE_SIZE_MB`

Response:

```json
{ "job_id": "...", "message": "File uploaded. Diarization started." }
```

### Job status

`GET /api/jobs/{job_id}`

Returns:

```json
{
	"job_id": "...",
	"status": "processing" | "done" | "error",
	"speakers": ["SPEAKER_00", "SPEAKER_01"],
	"error": null
}
```

### Rename speakers

`POST /api/speakers/rename`

Body:

```json
{ "job_id": "...", "labels": { "SPEAKER_00": "Agent", "SPEAKER_01": "Customer" } }
```

### Transcript

`GET /api/transcript/{job_id}`

Returns a list of turns:

```json
[
	{ "speaker": "SPEAKER_00", "label": "Agent", "start": 0.0, "end": 1.2, "text": "..." }
]
```

### Download audio

- `GET /api/download/{job_id}/{speaker}` → downloads a single speaker WAV
- `GET /api/download/{job_id}` → downloads `speakers.zip`

## How it works (high level)

- Upload creates a `job_id` and stores the original file under `TMP_DIR/<job_id>/`.
- A background task denoises the full audio with Audo AI, uploads it to pyannoteAI, then runs diarization with transcription enabled.
- The current backend configuration requests **2 speakers** (`num_speakers=2`).
- Once done, speaker turns are exposed via the status/transcript endpoints.
- Download endpoints slice the processed audio into per-speaker chunks, denoise each split with Audo AI, and export WAVs.
- When `DROP_OVERLAP_AUDIO=true`, the exporter removes any region where another speaker is active (plus `OVERLAP_GUARD_MS` on both sides) before building each speaker file. This aggressively suppresses crosstalk but drops words spoken during interruptions.

## Troubleshooting

- **CORS errors in the browser**: ensure the frontend is running on `http://localhost:5173`, or update CORS in `backend/main.py`.
- **Uploads fail for mp3/m4a/mp4**: install FFmpeg and ensure it is on PATH.
- **Job never finishes / errors**: confirm `PYANNOTE_API_KEY` is valid and the machine has outbound internet access.

## Security note

Do not commit real API keys. If an API key was ever committed to git history, rotate it in your pyannoteAI account.