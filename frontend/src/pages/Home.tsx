import { ChangeEvent, useState } from "react"
import { Link, useNavigate } from "react-router-dom"

import AuthButton from "../components/AuthButton"
import UsernameInput from "../components/UsernameInput"
import { useAuth } from "../hooks/useAuth"
import { SHOWCASE_USERNAME } from "../lib/constants"

export default function Home() {
  const [includePrivate, setIncludePrivate] = useState(false)
  const navigate = useNavigate()
  const { isAuthenticated, username: authUsername, avatarUrl, login, logout } = useAuth()

  const onUsernameSubmit = (clean: string) => {
    const include = isAuthenticated && includePrivate
    navigate(`/analyze/${clean}?private=${include ? "1" : "0"}`)
  }

  return (
    <main className="home-root">
      <div className="bg-orb bg-orb-a" aria-hidden="true" />
      <div className="bg-orb bg-orb-b" aria-hidden="true" />

      {/* Ghost preview — faint payoff teaser */}
      <div className="hero-ghost-preview" aria-hidden="true">
        <svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg" className="ghost-radar-svg">
          {/* Grid rings */}
          <polygon points="100,52 145,85 128,149 72,149 55,85" fill="none" stroke="#38E1FF" strokeWidth="0.75" />
          <polygon points="100,36 158,77 137,157 63,157 42,77" fill="none" stroke="#38E1FF" strokeWidth="0.75" />
          {/* Outer ring */}
          <polygon points="100,20 176,75 147,165 53,165 24,75" fill="none" stroke="#38E1FF" strokeWidth="1" />
          {/* Axis spokes */}
          <line x1="100" y1="100" x2="100"  y2="20"  stroke="#38E1FF" strokeWidth="0.5" />
          <line x1="100" y1="100" x2="176"  y2="75"  stroke="#38E1FF" strokeWidth="0.5" />
          <line x1="100" y1="100" x2="147"  y2="165" stroke="#38E1FF" strokeWidth="0.5" />
          <line x1="100" y1="100" x2="53"   y2="165" stroke="#38E1FF" strokeWidth="0.5" />
          <line x1="100" y1="100" x2="24"   y2="75"  stroke="#38E1FF" strokeWidth="0.5" />
          {/* Filled data area */}
          <polygon points="100,38 162,78 140,153 60,153 38,78" fill="rgba(56,225,255,0.15)" stroke="#38E1FF" strokeWidth="1.5" />
        </svg>
        <div className="ghost-tiles">
          <div className="ghost-tile">
            <span className="overline">Velocity</span>
            <span className="stat-number" style={{ fontSize: "1.5rem" }}>8.4</span>
          </div>
          <div className="ghost-tile">
            <span className="overline">Consistency</span>
            <span className="stat-number" style={{ fontSize: "1.5rem" }}>92%</span>
          </div>
        </div>
      </div>

      <section className="home-card">
        <header className="home-header">
          <h1 className="wordmark">GridPath</h1>
          <p className="subheadline">Turn your GitHub history into a developer fingerprint.</p>
        </header>

        <div className="username-form">
          <UsernameInput onSubmit={onUsernameSubmit} />

          {isAuthenticated && (
            <div className="private-toggle-wrap">
              <label className="private-toggle">
                <input
                  type="checkbox"
                  checked={includePrivate}
                  onChange={(e: ChangeEvent<HTMLInputElement>) => setIncludePrivate(e.target.checked)}
                />
                <span>Include private repositories {includePrivate && "🔒"}</span>
              </label>
              <p className="private-tooltip">
                We analyze your repos using your GitHub token. It never leaves our server.
              </p>
            </div>
          )}
        </div>

        {isAuthenticated ? (
          <AuthButton
            isAuthenticated={isAuthenticated}
            username={authUsername}
            avatarUrl={avatarUrl}
            login={login}
            logout={logout}
          />
        ) : (
          <AuthButton
            isAuthenticated={false}
            username={null}
            avatarUrl={null}
            login={login}
            logout={logout}
          />
        )}

        <Link to={`/analyze/${SHOWCASE_USERNAME}`} className="hero-example-link">
          See a live example →
        </Link>
      </section>
    </main>
  )
}
