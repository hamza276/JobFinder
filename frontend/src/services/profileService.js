import { api } from "./api";

export async function createProfile(payload) {
  const { data } = await api.post("/api/profile", payload);
  return data;
}

export async function getProfile(userId) {
  const { data } = await api.get(`/api/profile/${userId}`);
  return data;
}

export async function updateProfile(userId, payload) {
  const { data } = await api.patch(`/api/profile/${userId}`, payload);
  return data;
}
