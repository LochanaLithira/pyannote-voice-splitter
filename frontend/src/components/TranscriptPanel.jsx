import useJobStore from "../store/useJobStore";
import { formatTime } from "../utils/formatTime";
import { getPlayUrl } from "../utils/apiClient";
import useSegmentAudioPlayer from "../hooks/useSegmentAudioPlayer";

const COLORS = [
  "bg-blue-100 text-blue-800",
  "bg-purple-100 text-purple-800",
  "bg-green-100 text-green-800",
  "bg-amber-100 text-amber-800",
];

const TranscriptPanel = () => {
  const { jobId, transcript, speakers } = useJobStore();
  const { playing, loading, playSegment, stop } = useSegmentAudioPlayer();

  if (!transcript.length) {
    return (
      <div className="mt-6 p-5 bg-white border border-gray-200 rounded-xl text-center">
        <p className="text-sm text-gray-400">No transcript available.</p>
      </div>
    );
  }

  return (
    <div className="mt-6 bg-white border border-gray-200 rounded-xl overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-100">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-700">Transcript</h2>
          <button
            onClick={stop}
            disabled={!playing}
            className="text-xs text-gray-500 hover:text-gray-700 underline disabled:opacity-40"
          >
            Stop
          </button>
        </div>
      </div>
      <div className="p-5 space-y-4 max-h-96 overflow-y-auto">
        {transcript.map((turn, i) => {
          const speakerIndex = speakers.indexOf(turn.speaker);
          const colorClass = COLORS[speakerIndex % COLORS.length];
          const playUrl = jobId ? getPlayUrl(jobId, turn.speaker) : null;
          return (
            <div key={i} className="flex gap-3">
              <div className="flex-shrink-0 pt-0.5">
                <span className={`text-xs font-medium px-2 py-1 rounded-full ${colorClass}`}>
                  {turn.label || turn.speaker}
                </span>
              </div>
              <div className="flex-1">
                <p className="text-sm text-gray-800">{turn.text}</p>
                <p className="text-xs text-gray-400 mt-0.5">
                  {formatTime(turn.start)} — {formatTime(turn.end)}
                </p>
              </div>

              <div className="flex-shrink-0">
                <button
                  onClick={() => playSegment(playUrl, turn.start, turn.end)}
                  disabled={loading || !playUrl}
                  className="px-3 py-1.5 text-xs bg-gray-800 text-white rounded-lg hover:bg-gray-900 disabled:opacity-40"
                >
                  {loading ? "..." : "Play"}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default TranscriptPanel;