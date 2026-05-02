import { api } from "./api";

export async function getEmail(jobId) {
  const { data } = await api.get(`/api/email/${jobId}`);
  return data;
}

export async function regenerateEmail(jobId) {
  const { data } = await api.post(`/api/email/${jobId}/regenerate`);
  return data;
}
