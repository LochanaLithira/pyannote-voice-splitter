import os
from pydub import AudioSegment
from config import settings
from services.denoise_service import denoise_audio


def _assigned_confidence_score(seg: dict) -> float | None:
    confidence = seg.get("confidence")
    speaker = seg.get("speaker")

    if isinstance(confidence, (int, float)):
        return float(confidence)

    if isinstance(confidence, dict) and speaker in confidence:
        value = confidence.get(speaker)
        if isinstance(value, (int, float)):
            return float(value)

    return None


def _normalize_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if not intervals:
        return []

    sorted_intervals = sorted(intervals, key=lambda x: x[0])
    merged: list[tuple[int, int]] = [sorted_intervals[0]]

    for start, end in sorted_intervals[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))

    return merged


def _subtract_intervals(
    source: list[tuple[int, int]], blocked: list[tuple[int, int]], min_len_ms: int
) -> list[tuple[int, int]]:
    if not source:
        return []
    if not blocked:
        return [(s, e) for s, e in source if (e - s) >= min_len_ms]

    blocked_merged = _normalize_intervals(blocked)
    result: list[tuple[int, int]] = []

    for src_start, src_end in source:
        cursor = src_start
        for blk_start, blk_end in blocked_merged:
            if blk_end <= cursor:
                continue
            if blk_start >= src_end:
                break

            if blk_start > cursor and (blk_start - cursor) >= min_len_ms:
                result.append((cursor, blk_start))
            cursor = max(cursor, blk_end)
            if cursor >= src_end:
                break

        if cursor < src_end and (src_end - cursor) >= min_len_ms:
            result.append((cursor, src_end))

    return result


def _build_low_confidence_blocked_intervals(
    confidence_data: dict, total_duration_ms: int
) -> list[tuple[int, int]]:
    """
    Convert the sample-level confidence array from pyannoteAI into a list of
    blocked intervals (ms) where the model's confidence is below threshold.

    These regions correspond to contested / overlapping speech — the model
    itself is unsure which speaker is active. We block them from ALL speakers.

    confidence_data format: {"score": [0..100, ...], "resolution": 0.02}
    """
    scores = confidence_data.get("score", [])
    resolution = confidence_data.get("resolution", 0.02)
    if not scores:
        return []

    threshold = settings.sample_confidence_threshold
    resolution_ms = resolution * 1000  # e.g. 20ms per sample
    blocked: list[tuple[int, int]] = []
    in_block = False
    block_start = 0

    for i, score in enumerate(scores):
        sample_start_ms = int(i * resolution_ms)
        sample_end_ms = min(int((i + 1) * resolution_ms), total_duration_ms)
        is_low = score < threshold

        if is_low and not in_block:
            block_start = sample_start_ms
            in_block = True
        elif not is_low and in_block:
            blocked.append((block_start, sample_end_ms))
            in_block = False

    if in_block:
        blocked.append((block_start, total_duration_ms))

    return blocked


def _build_clean_intervals_by_speaker(
    segments: list[dict],
    total_duration_ms: int,
    diarization_segments: list[dict] | None = None,
    confidence_data: dict | None = None,
    *,
    edge_trim_ms_override: int | None = None,
    min_segment_ms_override: int | None = None,
) -> dict[str, list[tuple[int, int]]]:
    guard_ms = max(0, settings.overlap_guard_ms)
    high_conf_guard_ms = max(0, settings.high_confidence_overlap_guard_ms)
    min_segment_ms = max(
        1,
        int(min_segment_ms_override)
        if min_segment_ms_override is not None
        else settings.min_clean_segment_ms,
    )
    confidence_threshold = settings.overlap_confidence_threshold
    edge_trim_ms = max(
        0,
        int(edge_trim_ms_override)
        if edge_trim_ms_override is not None
        else settings.segment_edge_trim_ms,
    )
    drop_low_conf_turns = settings.drop_low_confidence_turns
    min_keep_confidence = settings.min_turn_confidence_to_keep

    # -----------------------------------------------------------------------
    # Layer 1: Build per-speaker intervals from exclusiveDiarization segments
    # -----------------------------------------------------------------------
    raw_by_speaker: dict[str, list[dict]] = {}
    for seg in segments:
        speaker = seg["speaker"]
        confidence_score = _assigned_confidence_score(seg)

        if (
            drop_low_conf_turns
            and confidence_score is not None
            and confidence_score < min_keep_confidence
        ):
            continue

        start_ms = max(0, int(seg["start"] * 1000) + edge_trim_ms)
        end_ms = min(total_duration_ms, int(seg["end"] * 1000) - edge_trim_ms)
        if end_ms <= start_ms:
            continue
        raw_by_speaker.setdefault(speaker, []).append(
            {
                "start": start_ms,
                "end": end_ms,
                "confidence": confidence_score,
            }
        )

    normalized_by_speaker = {
        speaker: _normalize_intervals([(i["start"], i["end"]) for i in intervals])
        for speaker, intervals in raw_by_speaker.items()
    }

    # -----------------------------------------------------------------------
    # Layer 2: Cross-speaker guard (using diarization_segments for confidence)
    # -----------------------------------------------------------------------
    # Use the richer diarization_segments (with confidence) as the blocking
    # source. Fall back to raw_by_speaker if diarization_segments not available.
    blocking_source = raw_by_speaker
    if diarization_segments:
        blocking_by_speaker: dict[str, list[dict]] = {}
        for seg in diarization_segments:
            speaker = seg.get("speaker")
            start = seg.get("start")
            end = seg.get("end")
            if speaker is None or start is None or end is None:
                continue
            confidence_score = _assigned_confidence_score(seg)
            start_ms = max(0, int(float(start) * 1000))
            end_ms = min(total_duration_ms, int(float(end) * 1000))
            if end_ms <= start_ms:
                continue
            blocking_by_speaker.setdefault(speaker, []).append(
                {"start": start_ms, "end": end_ms, "confidence": confidence_score}
            )
        blocking_source = blocking_by_speaker

    if not settings.drop_overlap_audio:
        # Skip cross-speaker blocking but still apply sample-level confidence below
        clean_by_speaker = dict(normalized_by_speaker)
    else:
        clean_by_speaker: dict[str, list[tuple[int, int]]] = {}
        for speaker, own_intervals in normalized_by_speaker.items():
            blocked: list[tuple[int, int]] = []
            for other_speaker, other_intervals in blocking_source.items():
                if other_speaker == speaker:
                    continue
                for other_interval in other_intervals:
                    interval_guard_ms = guard_ms
                    if settings.confidence_aware_overlap_drop:
                        confidence_score = other_interval.get("confidence")
                        if (
                            confidence_score is not None
                            and confidence_score >= confidence_threshold
                        ):
                            interval_guard_ms = high_conf_guard_ms

                    start_ms = other_interval["start"]
                    end_ms = other_interval["end"]
                    blocked_start = max(0, start_ms - interval_guard_ms)
                    blocked_end = min(total_duration_ms, end_ms + interval_guard_ms)
                    if blocked_end > blocked_start:
                        blocked.append((blocked_start, blocked_end))

            clean_by_speaker[speaker] = _subtract_intervals(
                own_intervals,
                blocked,
                min_len_ms=min_segment_ms,
            )

    # -----------------------------------------------------------------------
    # Layer 3: Sample-level confidence blocking (new)
    # Regions where pyannoteAI itself has low confidence = ambiguous / overlap.
    # Block these from ALL speakers regardless of who was assigned there.
    # -----------------------------------------------------------------------
    if confidence_data and settings.use_sample_confidence:
        low_conf_zones = _build_low_confidence_blocked_intervals(
            confidence_data, total_duration_ms
        )
        if low_conf_zones:
            print(
                f"[audio_service] Low-confidence blocked zones: "
                f"{len(low_conf_zones)} regions "
                f"(total {sum(e-s for s,e in low_conf_zones)}ms)"
            )
            clean_by_speaker = {
                speaker: _subtract_intervals(intervals, low_conf_zones, min_len_ms=min_segment_ms)
                for speaker, intervals in clean_by_speaker.items()
            }

    return clean_by_speaker


def _build_playback_intervals_by_speaker(
    segments: list[dict],
    total_duration_ms: int,
    *,
    edge_trim_ms: int = 0,
    min_segment_ms: int = 1,
) -> dict[str, list[tuple[int, int]]]:
    """Build intervals for UI playback.

    This is intentionally *less aggressive* than `_build_clean_intervals_by_speaker`.
    For interactive playback we prefer hearing something (even if short / overlapped)
    over dropping it entirely due to trimming/guards.

    Expected segment format: {"speaker": str, "start": float, "end": float}.
    """
    trim = max(0, int(edge_trim_ms))
    min_len = max(1, int(min_segment_ms))

    raw: dict[str, list[tuple[int, int]]] = {}
    for seg in segments or []:
        speaker = seg.get("speaker")
        start = seg.get("start")
        end = seg.get("end")
        if speaker is None or start is None or end is None:
            continue

        start_ms = max(0, int(float(start) * 1000) + trim)
        end_ms = min(total_duration_ms, int(float(end) * 1000) - trim)
        if end_ms <= start_ms:
            continue
        if (end_ms - start_ms) < min_len:
            continue

        raw.setdefault(str(speaker), []).append((start_ms, end_ms))

    return {speaker: _normalize_intervals(intervals) for speaker, intervals in raw.items()}


def slice_and_merge(
    job_id: str,
    original_path: str,
    segments: list[dict],
    diarization_segments: list[dict] | None = None,
    confidence_data: dict | None = None,
) -> dict[str, str]:
    audio = AudioSegment.from_file(original_path)
    speaker_intervals = _build_clean_intervals_by_speaker(
        segments,
        len(audio),
        diarization_segments=diarization_segments,
        confidence_data=confidence_data,
    )

    job_dir = os.path.join(settings.tmp_dir, job_id)
    output_paths: dict[str, str] = {}
    fade_ms = max(0, settings.segment_fade_ms)

    for speaker, intervals in speaker_intervals.items():
        if not intervals:
            print(f"Skipping {speaker}: no clean non-overlap intervals left after filtering.")
            continue

        # Apply fade-in/out to EACH chunk individually before joining.
        # Fading only the final merged segment (old approach) leaves all internal
        # joins as hard cuts, which causes audible clicks.
        def _fade_chunk(chunk: AudioSegment) -> AudioSegment:
            if fade_ms > 0 and len(chunk) > fade_ms * 2:
                return chunk.fade_in(fade_ms).fade_out(fade_ms)
            return chunk

        first_start, first_end = intervals[0]
        merged = _fade_chunk(audio[first_start:first_end])
        for start_ms, end_ms in intervals[1:]:
            merged += _fade_chunk(audio[start_ms:end_ms])

        output_filename = f"{speaker}.wav"
        output_path = os.path.join(job_dir, output_filename)
        merged.export(output_path, format="wav")

        # Denoise each speaker's audio via Audo AI
        print(
            f"Denoising {speaker} with {settings.split_audio_denoise_passes} pass(es)..."
        )
        denoise_audio(output_path, passes=settings.split_audio_denoise_passes)

        output_paths[speaker] = output_path

    return output_paths


def slice_and_merge_with_silence(
    job_id: str,
    original_path: str,
    segments: list[dict],
    diarization_segments: list[dict] | None = None,
    confidence_data: dict | None = None,
) -> dict[str, str]:
    audio = AudioSegment.from_file(original_path)
    total_duration_ms = len(audio)
    speaker_intervals = _build_clean_intervals_by_speaker(
        segments,
        total_duration_ms,
        diarization_segments=diarization_segments,
        confidence_data=confidence_data,
    )

    job_dir = os.path.join(settings.tmp_dir, job_id)
    output_paths: dict[str, str] = {}
    fade_ms = max(0, settings.segment_fade_ms)
    speakers = sorted(speaker_intervals.keys())

    for speaker in speakers:
        timeline = AudioSegment.silent(duration=total_duration_ms)

        for start_ms, end_ms in speaker_intervals.get(speaker, []):
            chunk = audio[start_ms:end_ms]
            # Apply per-chunk fade to reduce bleed at boundaries
            if fade_ms > 0 and len(chunk) > fade_ms * 2:
                chunk = chunk.fade_in(fade_ms).fade_out(fade_ms)
            timeline = timeline.overlay(chunk, position=start_ms)

        output_path = os.path.join(job_dir, f"{speaker}_timeline.wav")
        timeline.export(output_path, format="wav")

        # Denoise each speaker's timeline audio via Audo AI
        print(
            f"Denoising {speaker} timeline with {settings.split_audio_denoise_passes} pass(es)..."
        )
        denoise_audio(output_path, passes=settings.split_audio_denoise_passes)

        output_paths[speaker] = output_path

    return output_paths


def build_speaker_timelines(
    job_id: str,
    original_path: str,
    segments: list[dict],
    diarization_segments: list[dict] | None = None,
    confidence_data: dict | None = None,
    denoise_passes: int = 0,
) -> dict[str, str]:
    """Create per-speaker WAVs aligned to the original timeline.

    These files are intended for UI segment playback by seeking to
    timestamps (start/end). Regions outside the speaker's intervals are
    silence, so transcript/diarization timestamps line up.
    """
    audio = AudioSegment.from_file(original_path)
    total_duration_ms = len(audio)
    # For UI playback, prefer "no overlap" audio.
    # Use exclusive diarization segments (already non-overlapping), then apply the
    # same overlap/low-confidence blocking used for downloads, but *relax*
    # trim/min-length so short turns are not dropped.
    speaker_intervals = _build_clean_intervals_by_speaker(
        segments,
        total_duration_ms,
        diarization_segments=diarization_segments,
        confidence_data=confidence_data,
        edge_trim_ms_override=0,
        min_segment_ms_override=1,
    )

    job_dir = os.path.join(settings.tmp_dir, job_id)
    output_paths: dict[str, str] = {}
    fade_ms = max(0, settings.segment_fade_ms)
    speakers = sorted(speaker_intervals.keys())

    for speaker in speakers:
        timeline = AudioSegment.silent(duration=total_duration_ms)

        for start_ms, end_ms in speaker_intervals.get(speaker, []):
            chunk = audio[start_ms:end_ms]
            if fade_ms > 0 and len(chunk) > fade_ms * 2:
                chunk = chunk.fade_in(fade_ms).fade_out(fade_ms)
            timeline = timeline.overlay(chunk, position=start_ms)

        output_path = os.path.join(job_dir, f"{speaker}_timeline.wav")
        timeline.export(output_path, format="wav")

        if denoise_passes > 0:
            print(f"Denoising {speaker} timeline with {denoise_passes} pass(es)...")
            denoise_audio(output_path, passes=denoise_passes)

        output_paths[speaker] = output_path

    return output_paths