import numpy as np
import soundfile as sf
import noisereduce as nr
import os


def denoise_audio(input_path: str) -> str:
    data, sample_rate = sf.read(input_path)

    # Convert stereo to mono if needed
    if len(data.shape) > 1:
        data = np.mean(data, axis=1)

    # Non-stationary is best for sales calls — handles
    # variable background noise like office sounds, traffic, AC
    reduced = nr.reduce_noise(
        y=data,
        sr=sample_rate,
        stationary=False,
        prop_decrease=0.75,  # 75% noise reduction — aggressive but preserves voice
    )

    # Save denoised file alongside original
    base, ext = os.path.splitext(input_path)
    output_path = f"{base}_denoised.wav"
    sf.write(output_path, reduced, sample_rate)

    return output_path