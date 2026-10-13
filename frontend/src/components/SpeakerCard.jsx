import { useState } from "react";
import { renameSpakers, getDownloadUrl } from "../utils/apiClient";
import useJobStore from "../store/useJobStore";
import useAudioPlayer from "../hooks/useAudioPlayer";
import { formatTime } from "../utils/formatTime";

const COLORS = [
  "bg-blue-100 border-blue-300 text-blue-800",
  "bg-purple-100 border-purple-300 text-purple-800",
  "bg-green-100 border-green-300 text-green-800",
  "bg-amber-100 border-amber-300 text-amber-800",
];

const BAR_COLORS = [
  "accent-blue-500",
  "accent-purple-500",
  "accent-green-500",
  "accent-amber-500",
];

const SpeakerCard = ({ speaker, index }) => {
  const { jobId, labels, setLabel } = useJobStore();
  const [editing, setEditing] = useState(false);
  const [inputVal, setInputVal] = useState(labels[speaker] || speaker);
  const [saving, setSaving] = useState(false);

  const downloadUrl = getDownloadUrl(jobId, speaker);
  const { playing, currentTime, duration, loading, togglePlay, seek } =
    useAudioPlayer(downloadUrl);

  const currentLabel = labels[speaker] || speaker;
  const colorClass = COLORS[index % COLORS.length];
  const barColor = BAR_COLORS[index % BAR_COLORS.length];
  const progress = duration ? (currentTime / duration) * 100 : 0;

  const handleSave = async () => {
    if (!inputVal.trim()) return;
    setSaving(true);
    try {
      await renameSpakers(jobId, { ...labels, [speaker]: inputVal.trim() });
      setLabel(speaker, inputVal.trim());
      setEditing(false);
    } catch (err) {
      console.error("Rename failed", err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className={`border rounded-xl p-5 ${colorClass}`}>

      {/* Header — speaker ID + rename toggle */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium opacity-60">{speaker}</span>
        <button
          onClick={() => setEditing(!editing)}
          className="text-xs underline opacity-60 hover:opacity-100"
        >
          {editing ? "cancel" : "rename"}
        </button>
      </div>

      {/* Name / rename input */}
      {editing ? (
        <div className="flex gap-2 mb-4">
          <input
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            className="flex-1 text-sm px-3 py-1.5 rounded-lg border bg-white text-gray-800"
            placeholder="Enter name..."
            onKeyDown={(e) => e.key === "Enter" && handleSave()}
            autoFocus
          />
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-3 py-1.5 bg-white text-sm rounded-lg border font-medium hover:bg-gray-50"
          >
            {saving ? "..." : "Save"}
          </button>
        </div>
      ) : (
        <p className="text-lg font-semibold mb-4">{currentLabel}</p>
      )}

      {/* Audio player */}
      <div className="bg-white rounded-lg px-4 py-3 mb-3 border border-white/60">
        <div className="flex items-center gap-3">

          {/* Play / pause button */}
          <button
            onClick={togglePlay}
            disabled={loading}
            className="w-9 h-9 flex items-center justify-center rounded-full bg-gray-800 text-white hover:bg-gray-900 disabled:opacity-40 flex-shrink-0"
          >
            {loading ? (
              <span className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : playing ? (
              <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
                <rect x="2" y="1" width="4" height="12" rx="1"/>
                <rect x="8" y="1" width="4" height="12" rx="1"/>
              </svg>
            ) : (
              <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
                <path d="M3 1.5l9 5.5-9 5.5V1.5z"/>
              </svg>
            )}
          </button>

          {/* Seek bar + timestamps */}
          <div className="flex-1">
            <input
              type="range"
              min={0}
              max={duration || 0}
              step={0.1}
              value={currentTime}
              onChange={(e) => seek(parseFloat(e.target.value))}
              className={`w-full h-1.5 rounded-full cursor-pointer ${barColor}`}
            />
            <div className="flex justify-between mt-1">
              <span className="text-xs text-gray-400">{formatTime(currentTime)}</span>
              <span className="text-xs text-gray-400">{formatTime(duration)}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Download button */}
      <a
        href={downloadUrl}
        download={`${currentLabel}.wav`}
        className="block w-full text-center text-sm px-4 py-2 bg-white border rounded-lg font-medium hover:bg-gray-50 transition-colors"
      >
        Download audio
      </a>
    </div>
  );
};

export default SpeakerCard;