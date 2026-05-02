import React from "react";

import { ScoreBar } from "../common/ScoreBar";

function JobCard({ job, onSelect }) {
  const initials = getInitials(job.company || job.title || "PK");

  return (
    <article className="mb-4 break-inside-avoid">
      <button
        type="button"
        onClick={() => onSelect(job)}
        className="w-full rounded-xl border border-navy/10 bg-paper p-5 text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-newspaper focus:outline-none focus-visible:ring-2 focus-visible:ring-gold"
        aria-label={`Open ${job.title || "job"} at ${job.company || "unknown company"}`}
      >
        <div className="mb-4 flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-navy font-bold text-paper">
              {initials}
            </span>
            <div>
              <p className="text-sm font-extrabold text-navy">{job.company || "Confidential company"}</p>
              <p className="text-xs font-semibold uppercase tracking-normal text-ink/55">{job.location || "Pakistan / Remote"}</p>
            </div>
          </div>
          <span className="rounded-md bg-gold/20 px-2 py-1 text-xs font-bold uppercase tracking-normal text-navy">
            {job.source_platform || "direct"}
          </span>
        </div>
        <h2 className="font-serif text-2xl font-bold leading-tight text-navy">{job.title || "Untitled role"}</h2>
        <p className="mt-3 line-clamp-2 text-sm leading-6 text-ink/75">
          {job.description_short || job.description_raw || "Full job details are available in the listing."}
        </p>
        <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-navy/10 pt-4">
          <span className="text-xs font-bold text-ink/55">{formatRelativeDate(job.posted_at || job.fetched_at)}</span>
          <ScoreBar score={job.relevance_score} />
        </div>
      </button>
    </article>
  );
}

function getInitials(value) {
  return value
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0]?.toUpperCase())
    .join("");
}

function formatRelativeDate(value) {
  if (!value) {
    return "Recently found";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Recently found";
  }
  const diffMs = Date.now() - date.getTime();
  const days = Math.floor(diffMs / 86400000);
  if (days <= 0) {
    return "Today";
  }
  if (days === 1) {
    return "1 day ago";
  }
  if (days < 30) {
    return `${days} days ago`;
  }
  return date.toLocaleDateString();
}

export default React.memo(JobCard);
