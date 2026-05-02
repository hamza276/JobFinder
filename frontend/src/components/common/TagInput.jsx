import { X } from "lucide-react";
import { useState } from "react";

export function TagInput({ label, value = [], onChange, placeholder = "Type and press Enter" }) {
  const [draft, setDraft] = useState("");

  function addTag(raw) {
    const tag = raw.trim();
    if (!tag || value.some((item) => item.toLowerCase() === tag.toLowerCase())) {
      return;
    }
    onChange([...value, tag]);
    setDraft("");
  }

  function removeTag(tag) {
    onChange(value.filter((item) => item !== tag));
  }

  return (
    <div>
      <label className="mb-2 block text-sm font-bold text-navy">{label}</label>
      <div className="rounded-lg border border-navy/15 bg-paper px-2 py-2 focus-within:border-gold focus-within:ring-2 focus-within:ring-gold/30">
        <div className="flex flex-wrap gap-2">
          {value.map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center gap-1 rounded-md bg-navy/10 px-2 py-1 text-sm font-semibold text-navy"
            >
              {tag}
              <button type="button" onClick={() => removeTag(tag)} aria-label={`Remove ${tag}`}>
                <X size={14} aria-hidden="true" />
              </button>
            </span>
          ))}
          <input
            className="min-w-40 flex-1 bg-transparent px-1 py-1 text-sm outline-none placeholder:text-ink/40"
            value={draft}
            placeholder={placeholder}
            onChange={(event) => setDraft(event.target.value)}
            onBlur={() => addTag(draft)}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === ",") {
                event.preventDefault();
                addTag(draft);
              }
              if (event.key === "Backspace" && !draft && value.length) {
                removeTag(value[value.length - 1]);
              }
            }}
          />
        </div>
      </div>
    </div>
  );
}
