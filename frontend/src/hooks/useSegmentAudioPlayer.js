import { useEffect, useRef, useState } from "react";

const useSegmentAudioPlayer = () => {
  const audioRef = useRef(null);
  const rangeEndRef = useRef(null);
  const pendingStartRef = useRef(null);
  const pendingEndRef = useRef(null);
  const stopTimeoutRef = useRef(null);

  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    return () => {
      const audio = audioRef.current;
      if (audio) {
        audio.pause();
        audio.src = "";
      }
      audioRef.current = null;

      if (stopTimeoutRef.current) {
        clearTimeout(stopTimeoutRef.current);
        stopTimeoutRef.current = null;
      }
    };
  }, []);

  const _clearStopTimer = () => {
    if (stopTimeoutRef.current) {
      clearTimeout(stopTimeoutRef.current);
      stopTimeoutRef.current = null;
    }
  };

  const _ensureAudio = (url) => {
    const existing = audioRef.current;
    if (existing && existing.src === url) return existing;

    if (existing) {
      existing.pause();
    }

    const audio = new Audio(url);
    audioRef.current = audio;
    setLoading(true);

    audio.addEventListener("loadedmetadata", async () => {
      setLoading(false);
      const pendingStart = pendingStartRef.current;
      const pendingEnd = pendingEndRef.current;
      if (pendingStart != null && pendingEnd != null) {
        pendingStartRef.current = null;
        pendingEndRef.current = null;
        rangeEndRef.current = pendingEnd;
        audio.currentTime = pendingStart;
        try {
          await audio.play();
          setPlaying(true);

          const durationMs = Math.max(0, (pendingEnd - pendingStart) * 1000);
          _clearStopTimer();
          stopTimeoutRef.current = window.setTimeout(() => {
            if (audioRef.current === audio) {
              audio.pause();
              rangeEndRef.current = null;
              setPlaying(false);
            }
          }, durationMs + 120);
        } catch {
          setPlaying(false);
        }
      }
    });

    audio.addEventListener("timeupdate", () => {
      const rangeEnd = rangeEndRef.current;
      if (rangeEnd != null && audio.currentTime >= rangeEnd) {
        audio.pause();
        rangeEndRef.current = null;
        _clearStopTimer();
        setPlaying(false);
      }
    });

    audio.addEventListener("ended", () => {
      rangeEndRef.current = null;
      _clearStopTimer();
      setPlaying(false);
    });

    return audio;
  };

  const playSegment = async (url, startSeconds, endSeconds) => {
    if (!url) return;
    const start = Math.max(0, Number(startSeconds) || 0);
    const end = Math.max(start, Number(endSeconds) || start);

    // A bit of padding improves audibility and reduces "misses" caused by
    // aggressive diarization boundaries and `timeupdate` cadence.
    const PAD_SEC = 0.05;
    const MIN_AUDIBLE_SEC = 0.25;

    const effectiveStart = Math.max(0, start - PAD_SEC);
    let effectiveEnd = end + PAD_SEC;
    if (effectiveEnd - effectiveStart < MIN_AUDIBLE_SEC) {
      effectiveEnd = effectiveStart + MIN_AUDIBLE_SEC;
    }

    const audio = _ensureAudio(url);
    _clearStopTimer();
    rangeEndRef.current = effectiveEnd;

    // If metadata isn't loaded yet, defer seeking+play until it is.
    if (!Number.isFinite(audio.duration) || audio.duration === 0) {
      pendingStartRef.current = effectiveStart;
      pendingEndRef.current = effectiveEnd;
      try {
        audio.load();
      } catch {
        // ignore
      }
      return;
    }

    // Clamp to duration once we know it.
    const clampedEnd = Math.min(effectiveEnd, Math.max(0, audio.duration || 0));
    rangeEndRef.current = clampedEnd;

    audio.pause();
    audio.currentTime = effectiveStart;
    try {
      await audio.play();
      setPlaying(true);

      const durationMs = Math.max(0, (clampedEnd - effectiveStart) * 1000);
      stopTimeoutRef.current = window.setTimeout(() => {
        const current = audioRef.current;
        if (!current) return;
        current.pause();
        rangeEndRef.current = null;
        setPlaying(false);
      }, durationMs + 120);
    } catch {
      setPlaying(false);
    }
  };

  const stop = () => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.pause();
    rangeEndRef.current = null;
    pendingStartRef.current = null;
    pendingEndRef.current = null;
    _clearStopTimer();
    setPlaying(false);
  };

  return { playing, loading, playSegment, stop };
};

export default useSegmentAudioPlayer;
