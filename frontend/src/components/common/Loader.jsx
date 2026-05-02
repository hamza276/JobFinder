import { Loader2 } from "lucide-react";

export function Loader({ label = "Loading" }) {
  return (
    <div className="flex items-center justify-center gap-3 py-10 text-sm font-semibold text-navy/70">
      <Loader2 className="animate-spin" size={20} aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}
