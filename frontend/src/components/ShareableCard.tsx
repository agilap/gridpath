import { useState } from "react"

import { api } from "../lib/api"
import { GlassPanel } from "./ui/GlassPanel"

type ShareData = {
  token: string
  card_url: string
  url: string
  expires_at: string
}

type Props = {
  jobId?: string
  initialShare?: ShareData
}

export default function ShareableCard({ jobId = "", initialShare }: Props) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [share, setShare] = useState<ShareData | null>(initialShare ?? null)

  const generate = async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await api.post<ShareData>("/api/share", { job_id: jobId })
      if (!data.card_url || !data.url || !data.token) {
        setError("Share card data is incomplete. Please try again.")
        return
      }
      setShare(data)
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status
      if (status === 425) {
        setError("The card is not ready yet — try again in a few seconds.")
      } else {
        setError("Could not generate share card right now.")
      }
    } finally {
      setLoading(false)
    }
  }

  const copy = async () => {
    if (share?.url) await navigator.clipboard.writeText(share.url)
  }

  return (
    <GlassPanel as="section" className="p-5">
      <h3 className="panel-title">Shareable Card</h3>

      {!share && (
        <button className="btn btn-primary" onClick={() => void generate()} disabled={loading}>
          {loading ? "Generating…" : "Generate Share Card"}
        </button>
      )}

      {error && <p className="error-text" style={{ marginTop: "0.75rem" }}>{error}</p>}

      {share && (
        <div className="share-result" style={{ marginTop: share ? "0" : "1rem" }}>
          <img src={share.card_url} alt="GridPath share card" className="share-card-image" />
          <div className="share-link-row" style={{ marginTop: "0.75rem" }}>
            <input value={share.url} readOnly className="share-link-input" aria-label="Share URL" />
            <button className="btn" onClick={() => void copy()}>Copy</button>
          </div>
          <div className="share-actions">
            <a
              className="btn"
              target="_blank"
              rel="noreferrer"
              href={`https://twitter.com/intent/tweet?text=${encodeURIComponent("My GridPath fingerprint")}&url=${encodeURIComponent(share.url)}`}
            >
              Share on X
            </a>
            <a
              className="btn"
              target="_blank"
              rel="noreferrer"
              href={`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(share.url)}`}
            >
              Share on LinkedIn
            </a>
          </div>
        </div>
      )}
    </GlassPanel>
  )
}
