export const CHART_COLORS = {
  cyan:       "#38E1FF",
  radarFill:  "rgba(56,225,255,0.12)",
  feature:    "#2FD4A7",
  refactor:   "#6E8BFF",
  bugfix:     "#FF6E8A",
  test:       "#38E1FF",
  arch:       "#B98CFF",
  grid:       "rgba(125,165,230,0.10)",
  text:       "#9DB2D4",
  paper:      "rgba(0,0,0,0)",
} as const;

export const basePlotlyLayout: Record<string, unknown> = {
  paper_bgcolor: CHART_COLORS.paper,
  plot_bgcolor:  CHART_COLORS.paper,
  font: {
    family: "Inter, system-ui, sans-serif",
    color:  CHART_COLORS.text,
  },
  margin: { t: 20, r: 20, b: 40, l: 40 },
};
