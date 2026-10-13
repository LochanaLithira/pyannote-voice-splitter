import { useEffect, useRef } from "react";
import { getJobStatus, getTranscript } from "../utils/apiClient";
import useJobStore from "../store/useJobStore";

const useJobPolling = () => {
  const { jobId, status, setStatus, setSpeakers, setTranscript, setError } =
    useJobStore();
  const intervalRef = useRef(null);

  useEffect(() => {
    if (!jobId || status === "done" || status === "error") return;

    intervalRef.current = setInterval(async () => {
      try {
        const { data } = await getJobStatus(jobId);
        setStatus(data.status);
        setSpeakers(data.speakers);

        if (data.status === "done") {
          clearInterval(intervalRef.current);
          const { data: transcript } = await getTranscript(jobId);
          setTranscript(transcript);
        }

        if (data.status === "error") {
          clearInterval(intervalRef.current);
          setError(data.error || "Something went wrong.");
        }
      } catch (err) {
        clearInterval(intervalRef.current);
        setError("Could not reach the server.");
      }
    }, 2000);

    return () => clearInterval(intervalRef.current);
  }, [jobId, status]);
};

export default useJobPolling;