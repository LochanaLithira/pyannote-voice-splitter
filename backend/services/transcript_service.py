from services.pyannote_service import get_job


def get_transcript(job_id: str) -> list[dict]:
    job = get_job(job_id)
    if not job:
        return []

    transcript = job.get("transcript", [])
    labels = job.get("labels", {})

    result = []
    for turn in transcript:
        speaker = turn.get("speaker", "UNKNOWN")
        result.append({
            "speaker": speaker,
            "label": labels.get(speaker, speaker),
            "start": turn.get("start", 0.0),
            "end": turn.get("end", 0.0),
            "text": turn.get("text", ""),
        })

    return result


def get_transcript_as_text(job_id: str) -> str:
    turns = get_transcript(job_id)
    lines = []
    for turn in turns:
        name = turn["label"]
        start = round(turn["start"], 1)
        end = round(turn["end"], 1)
        lines.append(f"[{start}s - {end}s] {name}: {turn['text']}")
    return "\n".join(lines)