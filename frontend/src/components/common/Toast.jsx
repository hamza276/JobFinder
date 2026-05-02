import { X } from "lucide-react";

import { useUIStore } from "../../store/useUIStore";

const styles = {
  info: "border-navy/15 bg-paper text-navy",
  success: "border-forest/20 bg-forest text-white",
  error: "border-rust/20 bg-rust text-white",
};

export function Toast() {
  const toasts = useUIStore((state) => state.toasts);
  const dismissToast = useUIStore((state) => state.dismissToast);

  if (!toasts.length) {
    return null;
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 flex w-[min(92vw,380px)] flex-col gap-2" aria-live="polite">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`flex items-start justify-between gap-3 rounded-lg border px-4 py-3 text-sm font-semibold shadow-newspaper ${styles[toast.type]}`}
        >
          <span>{toast.message}</span>
          <button type="button" onClick={() => dismissToast(toast.id)} aria-label="Dismiss notification">
            <X size={16} aria-hidden="true" />
          </button>
        </div>
      ))}
    </div>
  );
}
