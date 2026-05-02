import { useMemo } from "react";

import { useUIStore } from "../store/useUIStore";

export function useToast() {
  const pushToast = useUIStore((state) => state.pushToast);
  return useMemo(
    () => ({
      info: (message) => pushToast({ message, type: "info" }),
      success: (message) => pushToast({ message, type: "success" }),
      error: (message) => pushToast({ message, type: "error" }),
    }),
    [pushToast],
  );
}
