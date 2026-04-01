import { create } from "zustand";

const useJobStore = create((set) => ({
  jobId: null,
  status: null,
  speakers: [],
  labels: {},
  transcript: [],
  error: null,

  setJobId: (jobId) => set({ jobId }),
  setStatus: (status) => set({ status }),
  setSpeakers: (speakers) => set({ speakers }),
  setError: (error) => set({ error }),

  setLabel: (speaker, label) =>
    set((state) => ({
      labels: { ...state.labels, [speaker]: label },
    })),

  setTranscript: (transcript) => set({ transcript }),

  reset: () =>
    set({
      jobId: null,
      status: null,
      speakers: [],
      labels: {},
      transcript: [],
      error: null,
    }),
}));

export default useJobStore;