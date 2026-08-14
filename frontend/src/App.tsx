import { Suspense, lazy } from "react"
import { Navigate, Route, Routes } from "react-router-dom"

import ErrorBoundary from "./components/ErrorBoundary"
import AppShell from "./components/layout/AppShell"
import Home from "./pages/Home"

const Profile = lazy(() => import("./pages/Profile"))
const Shared  = lazy(() => import("./pages/Shared"))

function App() {
  return (
    <AppShell>
      <Suspense fallback={<div style={{ flex: 1 }} />}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route
            path="/analyze/:username"
            element={
              <ErrorBoundary>
                <Profile />
              </ErrorBoundary>
            }
          />
          <Route path="/shared/:token" element={<Shared />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </AppShell>
  )
}

export default App
