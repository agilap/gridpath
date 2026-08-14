import Plot from "react-plotly.js"

import { CHART_COLORS, basePlotlyLayout } from "../lib/chartTheme"
import type { AxisScores } from "../types"

type Props = {
  axes: AxisScores
}

export default function RadarChart({ axes }: Props) {
  const categories = [
    "Shipping\nVelocity",
    "Bug-Fix\nRatio",
    "Refactor\nHabit",
    "Test\nCoverage",
    "Architecture\nChurn",
    "Consistency",
  ]

  const values = [
    axes.shipping_velocity,
    axes.bugfix_ratio,
    axes.refactor_habit,
    axes.test_coverage_signal,
    axes.architecture_churn,
    axes.consistency_score,
  ]

  return (
    <Plot
      data={[
        {
          type: "scatterpolar",
          r: [...values, values[0]],
          theta: [...categories, categories[0]],
          fill: "toself",
          fillcolor: CHART_COLORS.radarFill,
          line: { color: CHART_COLORS.cyan, width: 3 },
          marker: { color: CHART_COLORS.cyan },
          hovertemplate: "%{theta}: %{r:.2f}<extra></extra>",
        },
      ]}
      layout={{
        ...basePlotlyLayout,
        polar: {
          bgcolor: CHART_COLORS.paper,
          radialaxis: {
            range: [0, 10],
            tickcolor: CHART_COLORS.grid,
            gridcolor: CHART_COLORS.grid,
            tickfont: { color: CHART_COLORS.text, size: 10 },
          },
          angularaxis: {
            tickcolor: CHART_COLORS.text,
            gridcolor: CHART_COLORS.grid,
            tickfont: { color: CHART_COLORS.text, size: 11 },
          },
        },
        transition: { duration: 800, easing: "cubic-in-out" },
        showlegend: false,
      }}
      config={{ displayModeBar: false, responsive: true }}
      style={{ width: "100%", height: "100%", minHeight: 380 }}
    />
  )
}
