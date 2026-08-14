import { Component, ErrorInfo, ReactNode } from "react"

import { GlassPanel } from "./ui/GlassPanel"

type Props = {
  children: ReactNode
}

type State = {
  hasError: boolean
}

export default class ErrorBoundary extends Component<Props, State> {
  public constructor(props: Props) {
    super(props)
    this.state = { hasError: false }
  }

  public static getDerivedStateFromError(): State {
    return { hasError: true }
  }

  public componentDidCatch(_error: Error, _errorInfo: ErrorInfo): void {
    // Intentionally swallow — user-friendly fallback shown below.
  }

  public render() {
    if (this.state.hasError) {
      return (
        <main className="profile-root">
          <div className="profile-content">
            <GlassPanel className="p-8 profile-error">
              <h2 style={{ margin: "0 0 0.5rem", color: "var(--text-primary)" }}>
                Something went wrong
              </h2>
              <p className="muted" style={{ margin: "0 0 1.25rem" }}>
                We hit an unexpected error rendering this profile.
              </p>
              <a className="btn btn-primary" href="/">
                Back to home
              </a>
            </GlassPanel>
          </div>
        </main>
      )
    }
    return this.props.children
  }
}
