import os
from pydub import AudioSegment
from config import settings


def slice_and_merge(job_id: str, original_path: str, segments: list[dict]) -> dict[str, str]:
    audio = AudioSegment.from_file(original_path)

    speaker_chunks: dict[str, list[AudioSegment]] = {}

    for seg in segments:
        speaker = seg["speaker"]
        start_ms = int(seg["start"] * 1000)
        end_ms = int(seg["end"] * 1000)

        chunk = audio[start_ms:end_ms]

        if speaker not in speaker_chunks:
            speaker_chunks[speaker] = []
        speaker_chunks[speaker].append(chunk)

    job_dir = os.path.join(settings.tmp_dir, job_id)
    output_paths: dict[str, str] = {}

    for speaker, chunks in speaker_chunks.items():
        merged = chunks[0]
        for chunk in chunks[1:]:
            merged += chunk

        output_filename = f"{speaker}.wav"
        output_path = os.path.join(job_dir, output_filename)
        merged.export(output_path, format="wav")
        output_paths[speaker] = output_path

    return output_paths


def slice_and_merge_with_silence(job_id: str, original_path: str, segments: list[dict]) -> dict[str, str]:
    audio = AudioSegment.from_file(original_path)
    total_duration_ms = len(audio)

    job_dir = os.path.join(settings.tmp_dir, job_id)
    output_paths: dict[str, str] = {}

    speakers = list({seg["speaker"] for seg in segments})

    for speaker in speakers:
        timeline = AudioSegment.silent(duration=total_duration_ms)

        for seg in segments:
            if seg["speaker"] != speaker:
                continue
            start_ms = int(seg["start"] * 1000)
            end_ms = int(seg["end"] * 1000)
            chunk = audio[start_ms:end_ms]
            timeline = timeline.overlay(chunk, position=start_ms)

        output_path = os.path.join(job_dir, f"{speaker}_timeline.wav")
        timeline.export(output_path, format="wav")
        output_paths[speaker] = output_path

    return output_paths