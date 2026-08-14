export type CommitLabel =
  | "FEATURE"
  | "BUGFIX"
  | "REFACTOR"
  | "TEST"
  | "DOCS"
  | "CHORE"
  | "ARCHITECTURE"

export type AxisScores = {
  shipping_velocity: number
  bugfix_ratio: number
  refactor_habit: number
  test_coverage_signal: number
  architecture_churn: number
  consistency_score: number
}

export type CommitLabelDistribution = {
  FEATURE: number
  BUGFIX: number
  REFACTOR: number
  TEST: number
  DOCS: number
  CHORE: number
  ARCHITECTURE: number
}

export type FingerprintDict = {
  username: string
  total_commits_analyzed: number
  repos_analyzed: number
  date_range: string
  axes: AxisScores
  top_languages: string[]
  commit_label_distribution: CommitLabelDistribution
  peak_activity_year: string
  style_evolution: string
  raw_axis_values: Record<string, number>
}

export type AnalysisResult = {
  fingerprint: FingerprintDict
  narrative: string
  card_url?: string
  share_token?: string
  expires_at?: string
  commits_by_year?: Record<string, CommitLabelDistribution>
}

export type ProfileHookState = {
  data: AnalysisResult | null
  status: string
  progress: number
  error: string | null
  isLoading: boolean
  jobId: string | null
}
