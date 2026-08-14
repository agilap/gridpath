import { useEffect, useState } from "react"
import { Link, useLocation } from "react-router-dom"

import { useAuth } from "../../hooks/useAuth"

export default function TopNav() {
  const { isAuthenticated, username, avatarUrl, login, logout } = useAuth()
  const [scrolled, setScrolled] = useState(false)
  const location = useLocation()

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24)
    window.addEventListener("scroll", onScroll, { passive: true })
    return () => window.removeEventListener("scroll", onScroll)
  }, [])

  const showNewAnalysis = location.pathname !== "/"

  return (
    <nav className={`top-nav${scrolled ? " top-nav--scrolled" : ""}`} aria-label="Main navigation">
      <div className="top-nav-inner">
        <Link to="/" className="nav-wordmark" aria-label="GridPath home">
          GridPath
        </Link>

        <div className="nav-right">
          {showNewAnalysis && (
            <Link to="/" className="btn btn-ghost nav-action-btn">
              New analysis
            </Link>
          )}

          {isAuthenticated ? (
            <div className="nav-auth-connected">
              {avatarUrl ? (
                <img src={avatarUrl} alt="GitHub avatar" className="nav-avatar" />
              ) : (
                <span className="nav-avatar nav-avatar-fallback" aria-hidden="true" />
              )}
              <span className="nav-handle">@{username}</span>
              <button
                className="disconnect-link"
                onClick={() => void logout()}
                aria-label="Disconnect GitHub account"
              >
                Disconnect
              </button>
            </div>
          ) : (
            <button className="btn btn-ghost nav-action-btn" onClick={login} aria-label="Sign in with GitHub">
              <svg viewBox="0 0 24 24" aria-hidden="true" className="github-icon">
                <path
                  fill="currentColor"
                  d="M12 .5a12 12 0 0 0-3.79 23.39c.6.11.82-.26.82-.58v-2.03c-3.34.73-4.04-1.61-4.04-1.61-.55-1.4-1.34-1.77-1.34-1.77-1.1-.75.08-.74.08-.74 1.2.09 1.84 1.25 1.84 1.25 1.08 1.85 2.84 1.32 3.53 1 .11-.78.42-1.32.76-1.63-2.67-.3-5.48-1.33-5.48-5.92 0-1.31.47-2.39 1.24-3.23-.12-.3-.54-1.52.12-3.17 0 0 1.01-.32 3.31 1.23a11.42 11.42 0 0 1 6.02 0c2.3-1.55 3.31-1.23 3.31-1.23.66 1.65.24 2.87.12 3.17.77.84 1.24 1.92 1.24 3.23 0 4.6-2.82 5.62-5.5 5.92.43.37.82 1.11.82 2.24v3.32c0 .32.21.7.82.58A12 12 0 0 0 12 .5z"
                />
              </svg>
              Sign in
            </button>
          )}
        </div>
      </div>
    </nav>
  )
}
