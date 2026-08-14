import { Suspense, lazy, useMemo } from "react"
import { useNavigate, useParams, useSearchParams } from "react-router-dom"

import NarrativePanel from "../components/NarrativePanel"
import ShareableCard from "../components/ShareableCard"
import { GlassPanel } from "../components/ui/GlassPanel"
import { StatTile } from "../components/ui/StatTile"
import { useProfile } from "../hooks/useProfile"

const RadarChart    = lazy(() => import("../components/RadarChart"))
const CommitTimeline = lazy(() => import("../components/CommitTimeline"))

const STEPS = [
  { min: 0,  max: 10,  label: "🔍 Fetching your repositories…" },
  { min: 10, max: 40,  label: "📦 Reading commit history…" },
  { min: 40, max: 75,  label: "🧠 Classifying commits with AST analysis…" },
  { min: 75, max: 90,  label: "✨ Computing your developer fingerprint…" },
  { min: 90, max: 98,  label: "✍️  Writing your career narrative…" },
  { min: 98, max: 100, label: "🎨 Rendering your card…" },
]

export default function Profile() {
  const { username = "" } = useParams()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const includePrivate = searchParams.get("private") === "1"
  const { data, error, isLoading, progress, jobId } = useProfile(username, includePrivate)

  const stepLabel = useMemo(() => {
    const found = STEPS.find((s) => progress >= s.min && progress <= s.max)
    return found?.label ?? "Finalizing…"
  }, [progress])

  if (error) {
    return (
      <main className="profile-root">
        <div className="profile-content">
          <GlassPanel className="p-8 profile-error">
            <h2 style={{ margin: "0 0 0.5rem", color: "var(--text-primary)" }}>
              Could not analyze @{username}
            </h2>
            <p className="error-text" style={{ margin: "0 0 1.25rem" }}>{error}</p>
            <button
              className="btn btn-primary"
              onClick={() => navigate(`/analyze/${username}?private=${includePrivate ? "1" : "0"}`)}
            >
              Try again
            </button>
          </GlassPanel>
        </div>
      </main>
    )
  }

  if (isLoading || !data) {
    return (
      <main className="profile-root">
        <div className="profile-content">
          <GlassPanel className="p-8 profile-loading">
            <h2 style={{ margin: "0 0 0.25rem", color: "var(--text-primary)" }}>
              Analyzing @{username}
            </h2>
            <p className="muted" style={{ margin: "0 0 1.25rem" }}>{stepLabel}</p>
            <div className="progress-track">
              <div className="progress-fill" style={{ width: `${Math.max(progress, 5)}%` }} />
            </div>
            <div className="step-list">
              {STEPS.map((step) => {
                const isDone = progress > step.max
                const isActive = progress >= step.min && progress <= step.max
                return (
                  <div
                    key={step.label}
                    className={`step-item${isDone ? " step-item--done" : ""}${isActive ? " step-item--active" : ""}`}
                  >
                    <span className="step-icon" aria-hidden="true">
                      {isDone ? "✓" : isActive ? "▶" : "·"}
                    </span>
                    <span>{step.label}</span>
                  </div>
                )
              })}
            </div>
          </GlassPanel>
        </div>
      </main>
    )
  }

  const fp = data.fingerprint
  const axes = fp.axes

  const initialShare =
    data.card_url && data.share_token
      ? {
          token: data.share_token,
          card_url: data.card_url,
          url: `${window.location.origin}/shared/${data.share_token}`,
          expires_at: "",
        }
      : undefined

  return (
    <main className="profile-root">
      <div className="profile-content">
        <header className="profile-header">
          <h1 className="profile-username">@{username}</h1>
          <p className="profile-caption">{fp.date_range} · {fp.repos_analyzed} repos</p>
        </header>

        <div className="stat-row">
          <StatTile label="Velocity"      value={axes.shipping_velocity.toFixed(1)}    hero />
          <StatTile label="Consistency"   value={`${axes.consistency_score.toFixed(0)}%`} />
          <StatTile label="Bug-Fix Ratio" value={axes.bugfix_ratio.toFixed(1)} />
          <StatTile label="Refactor"      value={axes.refactor_habit.toFixed(1)} />
          <StatTile label="Commits"       value={fp.total_commits_analyzed.toLocaleString()} />
          <StatTile label="Repos"         value={fp.repos_analyzed} />
        </div>

        <div className="dashboard-main-grid">
          <GlassPanel className="p-5 dashboard-chart-panel">
            <h3 className="panel-title">Developer Fingerprint</h3>
            <Suspense fallback={<div className="chart-skeleton" style={{ minHeight: 380 }} />}>
              <RadarChart axes={axes} />
            </Suspense>
          </GlassPanel>
          <NarrativePanel narrative={data.narrative} />
        </div>

        <GlassPanel className="p-5">
          <h3 className="panel-title">Commit Timeline</h3>
          <Suspense fallback={<div className="chart-skeleton" style={{ minHeight: 300 }} />}>
            <CommitTimeline commits_by_year={data.commits_by_year ?? {}} />
          </Suspense>
        </GlassPanel>

        <ShareableCard jobId={jobId ?? ""} initialShare={initialShare} />
      </div>
    </main>
  )
}
