import { api } from "./api";

export async function getJobs(userId, { page = 1, limit = 10, includeViewed = false } = {}) {
  const { data } = await api.get(`/api/jobs/${userId}`, {
    params: { page, limit, include_viewed: includeViewed },
  });
  return data;
}

export async function getJobStats(userId) {
  const { data } = await api.get(`/api/jobs/${userId}/stats`);
  return data;
}

export async function triggerScan(userId) {
  const { data } = await api.post("/api/jobs/trigger", { user_id: userId });
  return data;
}

export async function markJobViewed(jobId, isHidden = false) {
  const { data } = await api.patch(`/api/jobs/${jobId}/viewed`, { is_hidden: isHidden });
  return data;
}
