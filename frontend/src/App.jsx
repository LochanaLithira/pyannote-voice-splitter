import useJobStore from "./store/useJobStore";
import useJobPolling from "./hooks/useJobPolling";
import UploadZone from "./components/UploadZone";
import ProcessingView from "./components/ProcessingView";
import SpeakerCard from "./components/SpeakerCard";
import TranscriptPanel from "./components/TranscriptPanel";
import { getDownloadAllUrl } from "./utils/apiClient";

const ResultsView = () => {
  const { jobId, speakers, reset } = useJobStore();

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="w-full max-w-2xl mx-auto">

        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-semibold text-gray-800">
              Call Analysis Complete
            </h1>
            <p className="text-sm text-gray-400 mt-1">Job ID: {jobId}</p>
          </div>
          <button
            onClick={reset}
            className="text-sm text-gray-500 hover:text-gray-700 underline"
          >
            Upload another
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
          {speakers.map((speaker, index) => (
            <SpeakerCard key={speaker} speaker={speaker} index={index} />
          ))}
        </div>

        <a
          href={getDownloadAllUrl(jobId)}
          download="speakers.zip"
          className="block w-full text-center text-sm px-4 py-3 bg-gray-800 text-white rounded-xl font-medium hover:bg-gray-900 transition-colors mb-2"
        >
          Download all speakers as ZIP
        </a>

        <TranscriptPanel />

      </div>
    </div>
  );
};

const App = () => {
  const { status } = useJobStore();
  useJobPolling();

  if (!status) return <UploadZone />;
  if (status === "processing" || status === "error") return <ProcessingView />;
  if (status === "done") return <ResultsView />;
};

export default App;