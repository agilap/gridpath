import { useEffect, useMemo, useState } from "react"

import { api } from "../lib/api"
import type { AnalysisResult, ProfileHookState } from "../types"

const MAX_POLL_MS = 180_000
const KNOWN_TERMINAL = new Set(["SUCCESS", "FAILURE", "REVOKED"])
const KNOWN_RUNNING = new Set(["PENDING", "PROGRESS", "STARTED"])

type AnalyzeResponse = {
  job_id: string
  estimated_seconds: number
  status: string
  result?: AnalysisResult
}

type StatusResponse = {
  status: string
  progress_pct: number
  message: string
}

export function useProfile(username: string, includePrivate: boolean): ProfileHookState {
  const [data, setData] = useState<AnalysisResult | null>(null)
  const [status, setStatus] = useState("PENDING")
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [jobId, setJobId] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    let pollTimer: number | null = null
    let startTime = 0

    const poll = async (id: string) => {
      if (cancelled) return

      if (Date.now() - startTime > MAX_POLL_MS) {
        setError("Analysis is taking longer than expected. Please try again.")
        setIsLoading(false)
        return
      }

      try {
        const { data: statusData } = await api.get<StatusResponse>(`/api/status/${id}`)
        if (cancelled) return

        setStatus(statusData.status)
        setProgress(statusData.progress_pct || 0)

        if (statusData.status === "SUCCESS") {
          const { data: result } = await api.get<AnalysisResult>(`/api/result/${id}`)
          if (cancelled) return
          setData(result)
          setIsLoading(false)
          setProgress(100)
          return
        }

        if (statusData.status === "FAILURE" || statusData.status === "REVOKED") {
          setError("Analysis failed. Please try again.")
          setIsLoading(false)
          return
        }

        if (!KNOWN_RUNNING.has(statusData.status) && KNOWN_TERMINAL.has(statusData.status) === false) {
          setError("Analysis failed with an unexpected status. Please try again.")
          setIsLoading(false)
          return
        }

        pollTimer = window.setTimeout(() => {
          void poll(id)
        }, 2000)
      } catch {
        setError("Could not fetch profile analysis status.")
        setIsLoading(false)
      }
    }

    const start = async () => {
      try {
        startTime = Date.now()
        setIsLoading(true)
        setError(null)
        setData(null)
        setStatus("PENDING")
        setProgress(0)

        const { data: analyze } = await api.post<AnalyzeResponse>("/api/analyze", {
          username,
          include_private: includePrivate,
        })

        if (cancelled) return

        setJobId(analyze.job_id)

        if (analyze.job_id === "cached" && analyze.result) {
          setData(analyze.result)
          setStatus("SUCCESS")
          setProgress(100)
          setIsLoading(false)
          return
        }

        void poll(analyze.job_id)
      } catch {
        setError("Could not start analysis. Check the username and try again.")
        setIsLoading(false)
      }
    }

    if (username) {
      void start()
    }

    return () => {
      cancelled = true
      if (pollTimer) {
        window.clearTimeout(pollTimer)
      }
    }
  }, [username, includePrivate])

  return useMemo(
    () => ({ data, status, progress, error, isLoading, jobId }),
    [data, status, progress, error, isLoading, jobId],
  )
}
