import { create } from "zustand";

const storedUserId = localStorage.getItem("pkjobs:user_id");

export const useProfileStore = create((set) => ({
  userId: storedUserId || "",
  profile: null,
  setUserId: (userId) => {
    if (userId) {
      localStorage.setItem("pkjobs:user_id", userId);
    } else {
      localStorage.removeItem("pkjobs:user_id");
    }
    set({ userId });
  },
  setProfile: (profile) => set({ profile }),
  resetProfile: () => {
    localStorage.removeItem("pkjobs:user_id");
    set({ userId: "", profile: null });
  },
}));
