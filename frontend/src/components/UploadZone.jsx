import { useRef, useState } from "react";
import { uploadAudio } from "../utils/apiClient";
import useJobStore from "../store/useJobStore";

const ALLOWED = [".wav", ".mp3", ".m4a", ".mp4", ".ogg", ".flac"];

const UploadZone = () => {
  const { setJobId, setStatus } = useJobStore();
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const inputRef = useRef(null);

  const handleFile = async (file) => {
    const ext = "." + file.name.split(".").pop().toLowerCase();
    if (!ALLOWED.includes(ext)) {
      setErrorMsg(`Unsupported format: ${ext}`);
      return;
    }

    setErrorMsg(null);
    setUploading(true);

    try {
      const { data } = await uploadAudio(file);
      setJobId(data.job_id);
      setStatus("processing");
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || "Upload failed.");
    } finally {
      setUploading(false);
    }
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const onInputChange = (e) => {
    const file = e.target.files[0];
    if (file) handleFile(file);
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-50 p-6">
      <div className="w-full max-w-lg">
        <h1 className="text-2xl font-semibold text-gray-800 mb-2 text-center">
          SplitVoice AI
        </h1>
        <p className="text-sm text-gray-500 text-center mb-8">
          Upload a call recording and download each speaker separately
        </p>

        <div
          onClick={() => inputRef.current.click()}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors
            ${dragging
              ? "border-blue-400 bg-blue-50"
              : "border-gray-300 bg-white hover:border-blue-300 hover:bg-gray-50"
            }`}
        >
          <div className="text-4xl mb-3">🎙️</div>
          {uploading ? (
            <p className="text-sm text-blue-500 font-medium">Uploading...</p>
          ) : (
            <>
              <p className="text-sm font-medium text-gray-700">
                Drag and drop your audio file here
              </p>
              <p className="text-xs text-gray-400 mt-1">
                or click to browse
              </p>
              <p className="text-xs text-gray-400 mt-3">
                Supported: {ALLOWED.join(", ")}
              </p>
            </>
          )}
        </div>

        {errorMsg && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-600">{errorMsg}</p>
          </div>
        )}

        <input
          ref={inputRef}
          type="file"
          accept={ALLOWED.join(",")}
          className="hidden"
          onChange={onInputChange}
        />
      </div>
    </div>
  );
};

export default UploadZone;