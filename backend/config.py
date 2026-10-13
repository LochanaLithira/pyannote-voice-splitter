from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    pyannote_api_key: str
    audo_api_key: str
    tmp_dir: str = "./tmp"
    max_file_size_mb: int = 200
    full_audio_denoise_passes: int = 1
    split_audio_denoise_passes: int = 2
    # Denoise passes for the per-speaker *timeline* audio used for segment playback.
    # Recommended default is 0 because the full audio is already denoised before diarization.
    timeline_audio_denoise_passes: int = 0
    drop_overlap_audio: bool = True
    overlap_guard_ms: int = 400                    # fallback cross-speaker guard (was 500)
    confidence_aware_overlap_drop: bool = True
    overlap_confidence_threshold: float = 65.0     # was 75.0 — more segments treated as high-conf
    high_confidence_overlap_guard_ms: int = 80     # was 120 — tighter guard for confident turns
    segment_edge_trim_ms: int = 150                # was 120 — trim a bit more off raw edges
    drop_low_confidence_turns: bool = False
    min_turn_confidence_to_keep: float = 65.0
    min_clean_segment_ms: int = 120
    # --- Sample-level confidence (new) ---
    use_sample_confidence: bool = True             # request confidence array from pyannoteAI
    sample_confidence_threshold: float = 40.0      # samples below this → blocked from all speakers
    segment_fade_ms: int = 30                      # fade-in/out applied at every chunk edge

    class Config:
        env_file = ".env"

settings = Settings()
os.makedirs(settings.tmp_dir, exist_ok=True)