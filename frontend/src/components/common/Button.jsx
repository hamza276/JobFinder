import { Loader2 } from "lucide-react";

const variants = {
  primary: "bg-navy text-paper hover:bg-ink focus-visible:ring-navy",
  secondary: "bg-paper text-navy ring-1 ring-navy/15 hover:bg-navy/5 focus-visible:ring-navy",
  ghost: "bg-transparent text-navy hover:bg-navy/10 focus-visible:ring-navy",
  danger: "bg-rust text-white hover:bg-rust/90 focus-visible:ring-rust",
};

export function Button({
  children,
  className = "",
  icon: Icon,
  isLoading = false,
  variant = "primary",
  type = "button",
  ...props
}) {
  return (
    <button
      type={type}
      className={`inline-flex min-h-10 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-bold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60 ${variants[variant]} ${className}`}
      disabled={isLoading || props.disabled}
      {...props}
    >
      {isLoading ? <Loader2 size={17} className="animate-spin" aria-hidden="true" /> : Icon ? <Icon size={17} aria-hidden="true" /> : null}
      {children}
    </button>
  );
}
