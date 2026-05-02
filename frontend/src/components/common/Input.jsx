export function Input({ label, error, className = "", ...props }) {
  const id = props.id || props.name;
  return (
    <label className={`block ${className}`} htmlFor={id}>
      <span className="mb-2 block text-sm font-bold text-navy">{label}</span>
      <input
        id={id}
        className="w-full rounded-lg border border-navy/15 bg-paper px-3 py-2.5 text-sm text-ink outline-none transition placeholder:text-ink/40 focus:border-gold focus:ring-2 focus:ring-gold/30"
        {...props}
      />
      {error ? <span className="mt-1 block text-xs font-semibold text-rust">{error}</span> : null}
    </label>
  );
}

export function Textarea({ label, error, className = "", ...props }) {
  const id = props.id || props.name;
  return (
    <label className={`block ${className}`} htmlFor={id}>
      <span className="mb-2 block text-sm font-bold text-navy">{label}</span>
      <textarea
        id={id}
        className="min-h-28 w-full resize-y rounded-lg border border-navy/15 bg-paper px-3 py-2.5 text-sm leading-6 text-ink outline-none transition placeholder:text-ink/40 focus:border-gold focus:ring-2 focus:ring-gold/30"
        {...props}
      />
      {error ? <span className="mt-1 block text-xs font-semibold text-rust">{error}</span> : null}
    </label>
  );
}
