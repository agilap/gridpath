import { GlassPanel } from "./ui/GlassPanel"

type Props = {
  narrative: string
}

export default function NarrativePanel({ narrative }: Props) {
  const paragraphs = narrative
    .split(/\n\n+/)
    .map((p) => p.trim())
    .filter(Boolean)

  return (
    <GlassPanel as="section" className="p-5 narrative-panel">
      <h3 className="panel-title">Career Narrative</h3>
      <div className="narrative-content">
        {paragraphs.length > 0 ? (
          paragraphs.map((paragraph, idx) => (
            <p key={`${paragraph.slice(0, 20)}-${idx}`} className="typewriter" style={{ animationDelay: `${idx * 0.4}s` }}>
              {paragraph}
            </p>
          ))
        ) : (
          <p className="muted">Narrative is still being generated.</p>
        )}
      </div>
    </GlassPanel>
  )
}
