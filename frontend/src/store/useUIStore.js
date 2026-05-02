import { create } from "zustand";

export const useUIStore = create((set) => ({
  isDrawerOpen: false,
  isScanRunning: false,
  toasts: [],
  setDrawerOpen: (isDrawerOpen) => set({ isDrawerOpen }),
  setScanRunning: (isScanRunning) => set({ isScanRunning }),
  pushToast: (toast) => {
    const id = crypto.randomUUID();
    set((state) => ({ toasts: [...state.toasts, { id, type: "info", ...toast }] }));
    window.setTimeout(() => {
      set((state) => ({ toasts: state.toasts.filter((item) => item.id !== id) }));
    }, toast.duration || 4500);
  },
  dismissToast: (id) =>
    set((state) => ({ toasts: state.toasts.filter((toast) => toast.id !== id) })),
}));
