import useJobStore from "../store/useJobStore";

const ProcessingView = () => {
  const { jobId, error, reset } = useJobStore();

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-50 p-6">
      <div className="w-full max-w-lg bg-white rounded-xl border border-gray-200 p-10 text-center">
        {error ? (
          <>
            <div className="text-4xl mb-4">❌</div>
            <h2 className="text-lg font-semibold text-gray-800 mb-2">
              Something went wrong
            </h2>
            <p className="text-sm text-red-500 mb-6">{error}</p>
            <button
              onClick={reset}
              className="px-5 py-2 bg-blue-500 text-white text-sm rounded-lg hover:bg-blue-600"
            >
              Try again
            </button>
          </>
        ) : (
          <>
            <div className="flex justify-center mb-6">
              <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
            </div>
            <h2 className="text-lg font-semibold text-gray-800 mb-2">
              Analyzing your call
            </h2>
            <p className="text-sm text-gray-500 mb-1">
              Separating speakers with pyannoteAI...
            </p>
            <p className="text-xs text-gray-400">
              Job ID: {jobId}
            </p>
          </>
        )}
      </div>
    </div>
  );
};

export default ProcessingView;