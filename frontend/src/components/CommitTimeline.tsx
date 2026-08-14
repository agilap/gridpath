import Plot from "react-plotly.js"

import { CHART_COLORS, basePlotlyLayout } from "../lib/chartTheme"
import type { CommitLabelDistribution } from "../types"

type Props = {
  commits_by_year: Record<string, CommitLabelDistribution>
}

const LABEL_COLORS: Record<string, string> = {
  FEATURE:  CHART_COLORS.feature,
  BUGFIX:   CHART_COLORS.bugfix,
  REFACTOR: CHART_COLORS.refactor,
}

const LABEL_DISPLAY: Record<string, string> = {
  FEATURE:  "Feature",
  BUGFIX:   "Bug-Fix",
  REFACTOR: "Refactor",
}

export default function CommitTimeline({ commits_by_year }: Props) {
  const years = Object.keys(commits_by_year).sort()

  const traces = ["FEATURE", "BUGFIX", "REFACTOR"].map((label) => ({
    type: "bar" as const,
    name: LABEL_DISPLAY[label],
    x: years,
    y: years.map((year) => commits_by_year[year]?.[label as keyof CommitLabelDistribution] ?? 0),
    marker: { color: LABEL_COLORS[label] },
  }))

  return (
    <Plot
      data={traces}
      layout={{
        ...basePlotlyLayout,
        barmode: "group",
        xaxis: {
          gridcolor: CHART_COLORS.grid,
          linecolor: CHART_COLORS.grid,
          tickfont: { color: CHART_COLORS.text },
        },
        yaxis: {
          gridcolor: CHART_COLORS.grid,
          linecolor: CHART_COLORS.grid,
          tickfont: { color: CHART_COLORS.text },
        },
        legend: {
          orientation: "h",
          font: { color: CHART_COLORS.text },
          bgcolor: "rgba(0,0,0,0)",
        },
        margin: { t: 12, r: 16, b: 48, l: 44 },
      }}
      config={{ displayModeBar: false, responsive: true }}
      style={{ width: "100%", minHeight: 300 }}
    />
  )
}
