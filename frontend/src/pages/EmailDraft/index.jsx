import { ArrowLeft, Copy, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { Button } from "../../components/common/Button";
import { Input, Textarea } from "../../components/common/Input";
import { Loader } from "../../components/common/Loader";
import { getApiErrorMessage } from "../../services/api";
import { getEmail, regenerateEmail } from "../../services/emailService";
import { useToast } from "../../hooks/useToast";
import { useEmailStore } from "../../store/useEmailStore";

export default function EmailDraft() {
  const { jobId } = useParams();
  const toast = useToast();
  const cachedEmail = useEmailStore((state) => state.getEmail(jobId));
  const setEmailStore = useEmailStore((state) => state.setEmail);
  const [email, setEmail] = useState(cachedEmail || null);
  const [isLoading, setLoading] = useState(!cachedEmail);
  const [isRegenerating, setRegenerating] = useState(false);

  useEffect(() => {
    let alive = true;
    async function loadEmail() {
      if (cachedEmail) {
        return;
      }
      setLoading(true);
      try {
        const data = await getEmail(jobId);
        if (!alive) return;
        setEmail(data);
        setEmailStore(jobId, data);
      } catch (error) {
        toast.error(getApiErrorMessage(error));
      } finally {
        if (alive) setLoading(false);
      }
    }
    loadEmail();
    return () => {
      alive = false;
    };
  }, [cachedEmail, jobId, setEmailStore, toast]);

  function updateField(field, value) {
    const next = { ...email, [field]: value };
    setEmail(next);
    setEmailStore(jobId, next);
  }

  async function handleRegenerate() {
    setRegenerating(true);
    try {
      const data = await regenerateEmail(jobId);
      setEmail(data);
      setEmailStore(jobId, data);
      toast.success("Email regenerated.");
    } catch (error) {
      toast.error(getApiErrorMessage(error));
    } finally {
      setRegenerating(false);
    }
  }

  async function copyEmail() {
    if (!email) return;
    await navigator.clipboard.writeText(`To: ${email.to_email || ""}\nSubject: ${email.subject}\n\n${email.body}`);
    toast.success("Email copied.");
  }

  if (isLoading) {
    return <Loader label="Generating email" />;
  }

  if (!email) {
    return (
      <section className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
        <Link to="/feed" className="inline-flex items-center gap-2 text-sm font-bold text-navy">
          <ArrowLeft size={17} aria-hidden="true" />
          Back to Feed
        </Link>
      </section>
    );
  }

  return (
    <section className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
      <div className="mb-6">
        <Link to="/feed" className="inline-flex items-center gap-2 text-sm font-bold text-navy hover:text-gold">
          <ArrowLeft size={17} aria-hidden="true" />
          Back to Feed
        </Link>
        <h1 className="mt-4 font-serif text-4xl font-bold text-navy sm:text-5xl">Application email</h1>
      </div>

      <div className="rounded-xl border border-navy/10 bg-paper p-5 shadow-newspaper">
        <div className="grid gap-4">
          <Input label="To" value={email.to_email || ""} onChange={(event) => updateField("to_email", event.target.value)} placeholder="Hiring email" />
          <Input label="Subject" value={email.subject || ""} onChange={(event) => updateField("subject", event.target.value)} />
          <Textarea label="Body" value={email.body || ""} rows={14} onChange={(event) => updateField("body", event.target.value)} />
        </div>
        <div className="mt-5 flex flex-wrap justify-end gap-3 border-t border-navy/10 pt-5">
          <Button variant="secondary" icon={RefreshCw} onClick={handleRegenerate} isLoading={isRegenerating}>
            Regenerate
          </Button>
          <Button icon={Copy} onClick={copyEmail}>
            Copy Email
          </Button>
        </div>
      </div>
    </section>
  );
}
