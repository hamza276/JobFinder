import { create } from "zustand";

export const useJobsStore = create((set) => ({
  jobs: [],
  selectedJob: null,
  page: 1,
  hasMore: true,
  setJobsPage: ({ jobs, page, hasMore }, append = false) =>
    set((state) => ({
      jobs: append ? mergeJobs(state.jobs, jobs) : jobs,
      page,
      hasMore,
    })),
  setSelectedJob: (selectedJob) => set({ selectedJob }),
  markViewed: (jobId, isHidden = false) =>
    set((state) => ({
      jobs: isHidden
        ? state.jobs.filter((job) => job.id !== jobId)
        : state.jobs.map((job) => (job.id === jobId ? { ...job, is_viewed: true } : job)),
      selectedJob: state.selectedJob?.id === jobId && isHidden ? null : state.selectedJob,
    })),
  resetJobs: () => set({ jobs: [], selectedJob: null, page: 1, hasMore: true }),
}));

function mergeJobs(current, incoming) {
  const seen = new Set(current.map((job) => job.id));
  return [...current, ...incoming.filter((job) => !seen.has(job.id))];
}
