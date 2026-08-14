import React from "react"

import Footer from "./Footer"
import TopNav from "./TopNav"

interface AppShellProps {
  children: React.ReactNode
}

export default function AppShell({ children }: AppShellProps) {
  return (
    <div className="app-shell">
      <TopNav />
      {children}
      <Footer />
    </div>
  )
}
