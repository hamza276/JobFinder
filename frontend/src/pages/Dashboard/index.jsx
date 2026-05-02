import { Mail, Newspaper, RefreshCw, Target, Timer, Eye } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { Button } from "../../components/common/Button";
import { Loader } from "../../components/common/Loader";
import { getApiErrorMessage } from "../../services/api";
import { getJobStats, triggerScan } from "../../services/jobsService";
import { getProfile } from "../../services/profileService";
import { useToast } from "../../hooks/useToast";
import { useProfileStore } from "../../store/useProfileStore";
import { useUIStore } from "../../store/useUIStore";

const cards = [
  { key: "total_found", label: "Jobs Found", icon: Newspaper },
  { key: "high_matches", label: "High Matches", icon: Target },
  { key: "viewed", label: "Viewed", icon: Eye },
  { key: "emails_generated", label: "Emails Ready", icon: Mail },
];

export default function Dashboard() {
  const toast = useToast();
  const userId = useProfileStore((state) => state.userId);
  const profile = useProfileStore((state) => state.profile);
  const setProfile = useProfileStore((state) => state.setProfile);
  const isScanRunning = useUIStore((state) => state.isScanRunning);
  const setScanRunning = useUIStore((state) => state.setScanRunning);
  const [stats, setStats] = useState(null);
  const [isLoading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    async function loadDashboard() {
      try {
        const [profileData, statsData] = await Promise.all([getProfile(userId), getJobStats(userId)]);
        if (!alive) return;
        setProfile(profileData);
        setStats(statsData);
      } catch (error) {
        toast.error(getApiErrorMessage(error));
      } finally {
        if (alive) setLoading(false);
      }
    }
    loadDashboard();
    return () => {
      alive = false;
    };
  }, [setProfile, toast, userId]);

  async function handleScan() {
    setScanRunning(true);
    try {
      const result = await triggerScan(userId);
      toast[result.accepted ? "success" : "info"](result.message);
      const statsData = await getJobStats(userId);
      setStats(statsData);
    } catch (error) {
      toast.error(getApiErrorMessage(error));
    } finally {
      setScanRunning(false);
    }
  }

  if (isLoading) {
    return <Loader label="Loading dashboard" />;
  }

  return (
    <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <div className="mb-8 flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
        <div>
          <p className="text-sm font-extrabold uppercase tracking-normal text-gold">Morning Brief</p>
          <h1 className="mt-2 font-serif text-4xl font-bold text-navy sm:text-5xl">
            {profile?.full_name ? `${profile.full_name}'s job desk` : "Your job desk"}
          </h1>
          <p className="mt-3 max-w-2xl text-base leading-7 text-ink/70">
            {profile?.current_title ? `${profile.current_title} roles matched to your profile.` : "Your profile is ready for job scans."}
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Button icon={RefreshCw} onClick={handleScan} isLoading={isScanRunning}>
            Scan Now
          </Button>
          <Link
            to="/feed"
            className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-paper px-4 py-2 text-sm font-bold text-navy ring-1 ring-navy/15 transition hover:bg-navy/5 focus:outline-none focus-visible:ring-2 focus-visible:ring-navy focus-visible:ring-offset-2"
          >
            <Newspaper size={17} aria-hidden="true" />
            Open Feed
          </Link>
        </div>
      </div>

      <div className="mb-6 rounded-xl border border-navy/10 bg-paper p-5 shadow-sm">
        <div className="flex flex-wrap items-center gap-3 text-sm font-bold text-navy">
          <Timer size={18} aria-hidden="true" />
          <span>Last scan: {formatDate(stats?.last_scan_at)}</span>
          <span className="text-navy/35">|</span>
          <span>Daily scan: 6:00 AM PKT</span>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map((card) => {
          const Icon = card.icon;
          return (
            <div key={card.key} className="rounded-xl border border-navy/10 bg-paper p-5 shadow-sm">
              <div className="mb-5 flex h-11 w-11 items-center justify-center rounded-lg bg-navy text-paper">
                <Icon size={20} aria-hidden="true" />
              </div>
              <p className="text-sm font-bold text-ink/55">{card.label}</p>
              <p className="mt-2 font-serif text-4xl font-bold text-navy">{stats?.[card.key] ?? 0}</p>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function formatDate(value) {
  if (!value) {
    return "not run yet";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "not run yet";
  }
  return date.toLocaleString();
}
