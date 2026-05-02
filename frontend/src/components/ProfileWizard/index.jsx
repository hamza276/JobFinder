import { ArrowLeft, ArrowRight, Check, Save } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { getApiErrorMessage } from "../../services/api";
import { createProfile, getProfile, updateProfile } from "../../services/profileService";
import { useProfileStore } from "../../store/useProfileStore";
import { useToast } from "../../hooks/useToast";
import { Button } from "../common/Button";
import { Input, Textarea } from "../common/Input";
import { Loader } from "../common/Loader";
import { TagInput } from "../common/TagInput";

const emptyProfile = {
  full_name: "",
  current_title: "",
  experience_years: 0,
  skills: [],
  education: { degree: "", field: "", institution: "", year: "" },
  preferred_locations: ["Remote"],
  preferred_job_types: ["full-time"],
  industries: [],
  salary_min: "",
  salary_max: "",
  languages: ["English", "Urdu"],
  bio: "",
};

const steps = ["Basics", "Skills", "Education", "Preferences", "Industries"];

export function ProfileWizard() {
  const navigate = useNavigate();
  const toast = useToast();
  const userId = useProfileStore((state) => state.userId);
  const setUserId = useProfileStore((state) => state.setUserId);
  const setProfileStore = useProfileStore((state) => state.setProfile);
  const [step, setStep] = useState(0);
  const [form, setForm] = useState(emptyProfile);
  const [isLoading, setLoading] = useState(Boolean(userId));
  const [isSaving, setSaving] = useState(false);

  const progress = useMemo(() => ((step + 1) / steps.length) * 100, [step]);

  useEffect(() => {
    let alive = true;
    async function loadProfile() {
      if (!userId) {
        setLoading(false);
        return;
      }
      try {
        const profile = await getProfile(userId);
        if (!alive) return;
        setProfileStore(profile);
        setForm({
          ...emptyProfile,
          ...profile,
          salary_min: profile.salary_min ?? "",
          salary_max: profile.salary_max ?? "",
        });
      } catch (error) {
        toast.error(getApiErrorMessage(error));
      } finally {
        if (alive) setLoading(false);
      }
    }
    loadProfile();
    return () => {
      alive = false;
    };
  }, [setProfileStore, toast, userId]);

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function updateEducation(field, value) {
    setForm((current) => ({
      ...current,
      education: { ...current.education, [field]: value },
    }));
  }

  async function submitProfile() {
    if (!form.full_name.trim() || !form.current_title.trim()) {
      toast.error("Name and current title are required.");
      setStep(0);
      return;
    }

    setSaving(true);
    const payload = {
      ...form,
      experience_years: Number(form.experience_years || 0),
      salary_min: form.salary_min === "" ? null : Number(form.salary_min),
      salary_max: form.salary_max === "" ? null : Number(form.salary_max),
    };

    try {
      const profile = userId ? await updateProfile(userId, payload) : await createProfile(payload);
      setUserId(profile.user_id);
      setProfileStore(profile);
      toast.success("Profile saved.");
      navigate("/dashboard");
    } catch (error) {
      toast.error(getApiErrorMessage(error));
    } finally {
      setSaving(false);
    }
  }

  if (isLoading) {
    return <Loader label="Loading profile" />;
  }

  return (
    <section className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
      <div className="mb-8">
        <p className="text-sm font-extrabold uppercase tracking-normal text-gold">PKJobs Profile</p>
        <h1 className="mt-2 font-serif text-4xl font-bold text-navy sm:text-5xl">
          {userId ? "Tune your job brief" : "Build your job brief"}
        </h1>
      </div>

      <div className="rounded-xl border border-navy/10 bg-paper p-5 shadow-newspaper">
        <div className="mb-6">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm font-bold text-navy">
              Step {step + 1} of {steps.length}: {steps[step]}
            </p>
            <div className="flex gap-1" aria-hidden="true">
              {steps.map((item, index) => (
                <span
                  key={item}
                  className={`h-2 w-8 rounded-full ${index <= step ? "bg-gold" : "bg-navy/10"}`}
                />
              ))}
            </div>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-navy/10">
            <div className="h-full rounded-full bg-gold transition-all" style={{ width: `${progress}%` }} />
          </div>
        </div>

        {step === 0 ? (
          <WizardStep title="Basic Info">
            <div className="grid gap-4 sm:grid-cols-2">
              <Input label="Full name" name="full_name" value={form.full_name} onChange={(e) => updateField("full_name", e.target.value)} />
              <Input label="Current title" name="current_title" value={form.current_title} onChange={(e) => updateField("current_title", e.target.value)} />
              <Input label="Years of experience" name="experience_years" type="number" min="0" value={form.experience_years} onChange={(e) => updateField("experience_years", e.target.value)} />
            </div>
            <Textarea label="Short bio" name="bio" value={form.bio || ""} onChange={(e) => updateField("bio", e.target.value)} placeholder="A few lines about your strongest work." />
          </WizardStep>
        ) : null}

        {step === 1 ? (
          <WizardStep title="Skills">
            <TagInput label="Core skills" value={form.skills} onChange={(value) => updateField("skills", value)} placeholder="React, Python, SQL" />
            <TagInput label="Languages" value={form.languages} onChange={(value) => updateField("languages", value)} placeholder="English, Urdu" />
          </WizardStep>
        ) : null}

        {step === 2 ? (
          <WizardStep title="Education">
            <div className="grid gap-4 sm:grid-cols-2">
              <Input label="Degree" name="degree" value={form.education.degree || ""} onChange={(e) => updateEducation("degree", e.target.value)} />
              <Input label="Field" name="field" value={form.education.field || ""} onChange={(e) => updateEducation("field", e.target.value)} />
              <Input label="Institution" name="institution" value={form.education.institution || ""} onChange={(e) => updateEducation("institution", e.target.value)} />
              <Input label="Year" name="year" value={form.education.year || ""} onChange={(e) => updateEducation("year", e.target.value)} />
            </div>
          </WizardStep>
        ) : null}

        {step === 3 ? (
          <WizardStep title="Preferences">
            <TagInput label="Preferred locations" value={form.preferred_locations} onChange={(value) => updateField("preferred_locations", value)} placeholder="Karachi, Lahore, Remote" />
            <TagInput label="Job types" value={form.preferred_job_types} onChange={(value) => updateField("preferred_job_types", value)} placeholder="full-time, remote, contract" />
            <div className="grid gap-4 sm:grid-cols-2">
              <Input label="Salary min PKR/month" name="salary_min" type="number" min="0" value={form.salary_min} onChange={(e) => updateField("salary_min", e.target.value)} />
              <Input label="Salary max PKR/month" name="salary_max" type="number" min="0" value={form.salary_max} onChange={(e) => updateField("salary_max", e.target.value)} />
            </div>
          </WizardStep>
        ) : null}

        {step === 4 ? (
          <WizardStep title="Industries">
            <TagInput label="Industries of interest" value={form.industries} onChange={(value) => updateField("industries", value)} placeholder="FinTech, SaaS, E-commerce" />
          </WizardStep>
        ) : null}

        <div className="mt-8 flex items-center justify-between gap-3 border-t border-navy/10 pt-5">
          <Button variant="secondary" icon={ArrowLeft} onClick={() => setStep((current) => Math.max(0, current - 1))} disabled={step === 0}>
            Back
          </Button>
          {step < steps.length - 1 ? (
            <Button icon={ArrowRight} onClick={() => setStep((current) => Math.min(steps.length - 1, current + 1))}>
              Next
            </Button>
          ) : (
            <Button icon={userId ? Save : Check} onClick={submitProfile} isLoading={isSaving}>
              {userId ? "Save" : "Create Profile"}
            </Button>
          )}
        </div>
      </div>
    </section>
  );
}

function WizardStep({ title, children }) {
  return (
    <div className="space-y-5">
      <h2 className="font-serif text-3xl font-bold text-navy">{title}</h2>
      {children}
    </div>
  );
}
