import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
});

export const uploadAudio = (file) => {
  const formData = new FormData();
  formData.append("file", file);
  return api.post("/api/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};

export const getJobStatus = (jobId) => {
  return api.get(`/api/jobs/${jobId}`);
};

export const renameSpakers = (jobId, labels) => {
  return api.post("/api/speakers/rename", { job_id: jobId, labels });
};

export const getTranscript = (jobId) => {
  return api.get(`/api/transcript/${jobId}`);
};

export const getDownloadUrl = (jobId, speaker) => {
  return `${api.defaults.baseURL}/api/download/${jobId}/${speaker}`;
};

export const getDownloadAllUrl = (jobId) => {
  return `${api.defaults.baseURL}/api/download/${jobId}`;
};