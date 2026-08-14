import { useCallback, useEffect, useState } from "react"

import { api } from "../lib/api"

type AuthStatus = {
  authenticated: boolean
  username: string | null
  avatar_url: string | null
}

export function useAuth() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [username, setUsername] = useState<string | null>(null)
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null)

  const refreshStatus = useCallback(async () => {
    try {
      const { data } = await api.get<AuthStatus>("/api/auth/status")
      setIsAuthenticated(data.authenticated)
      setUsername(data.username)
      setAvatarUrl(data.avatar_url)
    } catch {
      setIsAuthenticated(false)
      setUsername(null)
      setAvatarUrl(null)
    }
  }, [])

  useEffect(() => {
    void refreshStatus()
  }, [refreshStatus])

  const login = useCallback(() => {
    window.location.href = `${import.meta.env.VITE_API_BASE_URL || "http://localhost:8001"}/api/auth/github`
  }, [])

  const logout = useCallback(async () => {
    await api.post("/api/auth/logout")
    await refreshStatus()
  }, [refreshStatus])

  return { isAuthenticated, username, avatarUrl, login, logout }
}
