import { Copy, X } from "lucide-react";

import { Button } from "../common/Button";

export function EmailModal({ email, onClose }) {
  if (!email) {
    return null;
  }

  async function copyEmail() {
    await navigator.clipboard.writeText(`To: ${email.to_email || ""}\nSubject: ${email.subject}\n\n${email.body}`);
  }

  return (
    <div className="fixed inset-0 z-40 bg-navy/40 p-4" role="dialog" aria-modal="true">
      <div className="mx-auto mt-10 max-w-2xl rounded-xl bg-paper p-5 shadow-newspaper">
        <div className="mb-4 flex items-center justify-between gap-3">
          <h2 className="font-serif text-2xl font-bold text-navy">Application Email</h2>
          <button type="button" onClick={onClose} aria-label="Close email preview">
            <X size={20} aria-hidden="true" />
          </button>
        </div>
        <div className="space-y-3 text-sm">
          <p>
            <span className="font-bold text-navy">To:</span> {email.to_email || "Hiring team"}
          </p>
          <p>
            <span className="font-bold text-navy">Subject:</span> {email.subject}
          </p>
          <div className="whitespace-pre-wrap rounded-lg border border-navy/10 bg-cream p-4 leading-7">{email.body}</div>
        </div>
        <div className="mt-5 flex justify-end">
          <Button icon={Copy} onClick={copyEmail}>
            Copy
          </Button>
        </div>
      </div>
    </div>
  );
}
