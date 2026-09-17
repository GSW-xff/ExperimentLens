export type Severity = 'critical' | 'warning' | 'info'

export interface EvidenceRef {
  id: string
  kind: string
  label: string
  detail?: string | null
}

export interface Project {
  id: string
  name: string
  objective: string
  created_at: string
  updated_at: string
  state: string
  sources: Array<Record<string, unknown>>
  mapping?: SchemaMapping | null
}

export interface SchemaMapping {
  run_id: string
  group: string
  seed?: string | null
  status?: string | null
  duration?: string | null
  primary_metric: string
  metric_direction: 'maximize' | 'minimize'
  baseline_group: string
  metric_columns: string[]
  parameter_columns: string[]
}

export interface GroupStat {
  group: string
  n: number
  mean: number | null
  median: number | null
  std: number | null
  ci_low: number | null
  ci_high: number | null
  values: number[]
  run_ids: string[]
  mean_duration: number | null
}

export interface Comparison {
  group: string
  baseline_group: string
  mean_delta: number
  relative_delta: number | null
  confidence_interval: [number, number]
  effect_size: number
  p_value_approx: number
  sample_size: { baseline: number; candidate: number }
  warnings: string[]
  evidence_refs: string[]
}

export interface Summary {
  primary_metric: string
  metric_direction: string
  baseline_group: string
  run_count: number
  successful_runs: number
  failed_runs: number
  group_count: number
  best_run: { run_id: string; group: string; value: number } | null
  groups: GroupStat[]
  comparison: Comparison[]
  findings_count: number
  high_priority_findings: number
  conclusion: string
}

export interface Finding {
  id: string
  type: string
  severity: Severity
  title: string
  description: string
  evidence_refs: EvidenceRef[]
  detector: string
  detector_version: string
  confidence: number
}

export interface Hypothesis {
  id: string
  description: string
  supporting_evidence: EvidenceRef[]
  contradicting_evidence: EvidenceRef[]
  uncertainties: string[]
  confidence: number
  verification_plan: string
  status: string
}

export interface Proposal {
  id: string
  title: string
  hypothesis_id: string
  changed_variable: string
  fixed_conditions: string[]
  seeds: number[]
  expected_observation: string
  interpretation: string
  priority: string
  estimated_cost: string
  status: string
}

export interface Analysis {
  summary: Summary
  findings: Finding[]
  hypotheses: Hypothesis[]
  proposals: Proposal[]
}

export interface RunRow {
  run_id: string
  group: string
  seed: string | number | null
  status: string
  duration_seconds: number | null
  metric_value: number | null
  params: Record<string, string>
}
