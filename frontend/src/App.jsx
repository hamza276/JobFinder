import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { BriefcaseBusiness, LayoutDashboard, Newspaper, UserRound } from "lucide-react";

import Dashboard from "./pages/Dashboard";
import EmailDraft from "./pages/EmailDraft";
import JobFeed from "./pages/JobFeed";
import Onboarding from "./pages/Onboarding";
import { Toast } from "./components/common/Toast";
import { useProfileStore } from "./store/useProfileStore";

const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/feed", label: "Feed", icon: Newspaper },
];

function RequireProfile({ children }) {
  const userId = useProfileStore((state) => state.userId);
  if (!userId) {
    return <Navigate to="/onboarding" replace />;
  }
  return children;
}

function AppFrame({ children }) {
  const location = useLocation();
  const userId = useProfileStore((state) => state.userId);
  const showNav = userId && location.pathname !== "/onboarding";

  return (
    <div className="min-h-screen bg-cream text-ink">
      {showNav ? (
        <header className="sticky top-0 z-30 border-b border-navy/10 bg-paper/95 backdrop-blur">
          <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
            <Link to="/dashboard" className="flex items-center gap-3 font-serif text-2xl font-bold text-navy">
              <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-navy text-paper">
                <BriefcaseBusiness size={21} aria-hidden="true" />
              </span>
              PKJobs
            </Link>
            <nav className="flex items-center gap-1" aria-label="Primary">
              {navItems.map((item) => {
                const Icon = item.icon;
                const active = location.pathname === item.to;
                return (
                  <Link
                    key={item.to}
                    to={item.to}
                    className={`inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold transition ${
                      active ? "bg-navy text-paper" : "text-navy hover:bg-navy/10"
                    }`}
                  >
                    <Icon size={17} aria-hidden="true" />
                    <span className="hidden sm:inline">{item.label}</span>
                  </Link>
                );
              })}
              <Link
                to="/onboarding"
                className="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold text-navy hover:bg-navy/10"
                aria-label="Edit profile"
              >
                <UserRound size={17} aria-hidden="true" />
                <span className="hidden sm:inline">Profile</span>
              </Link>
            </nav>
          </div>
        </header>
      ) : null}
      <main>{children}</main>
      <Toast />
    </div>
  );
}

export default function App() {
  const userId = useProfileStore((state) => state.userId);

  return (
    <AppFrame>
      <Routes>
        <Route path="/" element={<Navigate to={userId ? "/dashboard" : "/onboarding"} replace />} />
        <Route path="/onboarding" element={<Onboarding />} />
        <Route
          path="/dashboard"
          element={
            <RequireProfile>
              <Dashboard />
            </RequireProfile>
          }
        />
        <Route
          path="/feed"
          element={
            <RequireProfile>
              <JobFeed />
            </RequireProfile>
          }
        />
        <Route
          path="/email/:jobId"
          element={
            <RequireProfile>
              <EmailDraft />
            </RequireProfile>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppFrame>
  );
}
