import { create } from "zustand";

export const useEmailStore = create((set, get) => ({
  emails: {},
  setEmail: (jobId, email) =>
    set((state) => ({
      emails: { ...state.emails, [jobId]: email },
    })),
  getEmail: (jobId) => get().emails[jobId],
}));
