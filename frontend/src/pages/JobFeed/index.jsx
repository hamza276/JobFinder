import { ExternalLink, Mail, PanelRightClose, RefreshCw, Trash2 } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import JobCard from "../../components/JobCard";
import { Button } from "../../components/common/Button";
import { Loader } from "../../components/common/Loader";
import { ScoreBar } from "../../components/common/ScoreBar";
import { getApiErrorMessage } from "../../services/api";
import { getJobs, markJobViewed } from "../../services/jobsService";
import { useToast } from "../../hooks/useToast";
import { useJobsStore } from "../../store/useJobsStore";
import { useProfileStore } from "../../store/useProfileStore";
import { useUIStore } from "../../store/useUIStore";

const pageSize = 10;

export default function JobFeed() {
  const navigate = useNavigate();
  const toast = useToast();
  const userId = useProfileStore((state) => state.userId);
  const jobs = useJobsStore((state) => state.jobs);
  const selectedJob = useJobsStore((state) => state.selectedJob);
  const page = useJobsStore((state) => state.page);
  const hasMore = useJobsStore((state) => state.hasMore);
  const setJobsPage = useJobsStore((state) => state.setJobsPage);
  const setSelectedJob = useJobsStore((state) => state.setSelectedJob);
  const markViewed = useJobsStore((state) => state.markViewed);
  const resetJobs = useJobsStore((state) => state.resetJobs);
  const isDrawerOpen = useUIStore((state) => state.isDrawerOpen);
  const setDrawerOpen = useUIStore((state) => state.setDrawerOpen);
  const [isLoading, setLoading] = useState(false);
  const sentinelRef = useRef(null);

  const loadPage = useCallback(
    async (targetPage, append = false) => {
      setLoading(true);
      try {
        const data = await getJobs(userId, { page: targetPage, limit: pageSize });
        setJobsPage({ jobs: data.jobs, page: data.page, hasMore: data.has_more }, append);
      } catch (error) {
        toast.error(getApiErrorMessage(error));
      } finally {
        setLoading(false);
      }
    },
    [setJobsPage, toast, userId],
  );

  useEffect(() => {
    resetJobs();
    loadPage(1, false);
  }, [loadPage, resetJobs]);

  useEffect(() => {
    if (!sentinelRef.current || !hasMore || isLoading) {
      return undefined;
    }
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          loadPage(page + 1, true);
        }
      },
      { rootMargin: "400px" },
    );
    observer.observe(sentinelRef.current);
    return () => observer.disconnect();
  }, [hasMore, isLoading, loadPage, page]);

  function openJob(job) {
    setSelectedJob(job);
    setDrawerOpen(true);
  }

  async function hideJob(job) {
    try {
      await markJobViewed(job.id, true);
      markViewed(job.id, true);
      setDrawerOpen(false);
      toast.success("Job hidden.");
    } catch (error) {
      toast.error(getApiErrorMessage(error));
    }
  }

  return (
    <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <div className="mb-8 flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <p className="text-sm font-extrabold uppercase tracking-normal text-gold">The Daily Feed</p>
          <h1 className="mt-2 font-serif text-4xl font-bold text-navy sm:text-5xl">Job stories worth opening</h1>
        </div>
        <Button variant="secondary" icon={RefreshCw} onClick={() => loadPage(1, false)} isLoading={isLoading}>
          Refresh
        </Button>
      </div>

      {!jobs.length && isLoading ? <Loader label="Loading jobs" /> : null}

      {!jobs.length && !isLoading ? (
        <div className="rounded-xl border border-dashed border-navy/20 bg-paper p-8 text-center">
          <h2 className="font-serif text-3xl font-bold text-navy">No jobs yet</h2>
          <p className="mt-2 text-sm leading-6 text-ink/65">Run a scan from the dashboard and your matched listings will appear here.</p>
        </div>
      ) : null}

      <div className="newspaper-columns">
        {jobs.map((job) => (
          <JobCard key={job.id} job={job} onSelect={openJob} />
        ))}
      </div>

      <div ref={sentinelRef}>{isLoading && jobs.length ? <Loader label="Loading more" /> : null}</div>

      <JobDrawer
        job={selectedJob}
        isOpen={isDrawerOpen}
        onClose={() => setDrawerOpen(false)}
        onEmail={(jobId) => navigate(`/email/${jobId}`)}
        onHide={hideJob}
      />
    </section>
  );
}

function JobDrawer({ job, isOpen, onClose, onEmail, onHide }) {
  if (!job) {
    return null;
  }

  return (
    <aside
      className={`fixed inset-y-0 right-0 z-40 w-full max-w-xl transform overflow-y-auto border-l border-navy/10 bg-paper shadow-newspaper transition-transform duration-200 ${
        isOpen ? "translate-x-0" : "translate-x-full"
      }`}
      aria-hidden={!isOpen}
    >
      <div className="sticky top-0 z-10 flex items-center justify-between border-b border-navy/10 bg-paper/95 px-5 py-4 backdrop-blur">
        <div>
          <p className="text-xs font-extrabold uppercase tracking-normal text-gold">{job.company || "Company"}</p>
          <h2 className="font-serif text-2xl font-bold leading-tight text-navy">{job.title || "Untitled role"}</h2>
        </div>
        <button type="button" onClick={onClose} aria-label="Close job details" className="rounded-lg p-2 hover:bg-navy/10">
          <PanelRightClose size={22} aria-hidden="true" />
        </button>
      </div>

      <div className="space-y-6 px-5 py-6">
        <div className="flex flex-wrap items-center gap-3">
          <span className="rounded-md bg-navy/10 px-2 py-1 text-xs font-bold text-navy">{job.location || "Pakistan / Remote"}</span>
          <span className="rounded-md bg-gold/20 px-2 py-1 text-xs font-bold text-navy">{job.job_type || "role"}</span>
          <ScoreBar score={job.relevance_score} />
        </div>

        {job.relevance_reason ? (
          <div className="rounded-lg bg-cream p-4 text-sm leading-6 text-ink/75">
            <span className="font-bold text-navy">Why it matches: </span>
            {job.relevance_reason}
          </div>
        ) : null}

        <div>
          <h3 className="mb-2 text-sm font-extrabold uppercase tracking-normal text-navy">Job Description</h3>
          <p className="whitespace-pre-wrap text-sm leading-7 text-ink/80">{job.description_raw || job.description_short}</p>
        </div>

        <div className="flex flex-wrap gap-3 border-t border-navy/10 pt-5">
          <Button icon={Mail} onClick={() => onEmail(job.id)}>
            Generate Email
          </Button>
          <a
            href={job.source_url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-paper px-4 py-2 text-sm font-bold text-navy ring-1 ring-navy/15 transition hover:bg-navy/5 focus:outline-none focus-visible:ring-2 focus-visible:ring-navy focus-visible:ring-offset-2"
          >
            <ExternalLink size={17} aria-hidden="true" />
            Original
          </a>
          <Button variant="danger" icon={Trash2} onClick={() => onHide(job)}>
            Hide
          </Button>
        </div>
      </div>
    </aside>
  );
}
