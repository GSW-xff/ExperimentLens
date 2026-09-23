export type Severity = 'critical' | 'warning' | 'info'

export interface EvidenceRef {
  id: string
  kind: string
  label: string
  detail?: string | null
}

export interface Project {
  schema_version: number
  id: string
  name: string
  objective: string
  created_at: string
  updated_at: string
  state: string
  experiment_type: string
  domain_tags: string[]
  sources: Array<Record<string, unknown>>
  mapping?: SchemaMapping | null
}

export type MetricRole = 'primary' | 'secondary' | 'constraint' | 'resource'

export interface MetricDefinition {
  key: string
  display_name?: string | null
  role: MetricRole
  direction: 'maximize' | 'minimize'
  unit?: string | null
  aggregation: string
  valid_min?: number | null
  valid_max?: number | null
  constraint_operator?: 'lt' | 'lte' | 'gt' | 'gte' | null
  constraint_value?: number | null
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
  metric_definitions: MetricDefinition[]
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
  metric_definitions: MetricDefinition[]
  metric_summaries: Array<{
    key: string
    display_name: string
    role: MetricRole
    direction: string
    unit?: string | null
    mean: number | null
    min: number | null
    max: number | null
    groups: Array<{ group: string; mean: number | null }>
  }>
  constraints: Array<{
    key: string
    operator: string
    threshold: number
    evaluated_runs: number
    violation_count: number
    violating_run_ids: string[]
    satisfied: boolean
  }>
  constraints_satisfied: boolean
  pareto_groups: string[]
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
  metric_key?: string | null
  params: Record<string, string>
}

export type AgentRunStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | 'budget_exhausted' | 'awaiting_approval'

export interface AgentToolCall {
  id: string
  tool_name: string
  status: string
  arguments: Record<string, unknown>
  output_summary?: string | null
  error?: string | null
}

export interface AgentRun {
  id: string
  project_id: string
  organization_id: string
  trace_id?: string | null
  question: string
  status: AgentRunStatus
  max_steps: number
  step_count: number
  token_budget: number
  used_tokens: number
  model: string
  tool_calls: AgentToolCall[]
  evidence_refs: EvidenceRef[]
  answer?: string | null
  error?: string | null
}

export interface TraceSpan {
  id: string
  trace_id: string
  parent_span_id?: string | null
  name: string
  status: 'ok' | 'error'
  duration_ms?: number | null
  attributes: Record<string, unknown>
  error_category?: string | null
}

export interface EvaluationDatasetSummary {
  version: string
  hash: string
  case_count: number
  tag_counts: Record<string, number>
}

export interface EvaluationLatest {
  id?: string
  status: 'not_run' | 'complete'
  case_count?: number
  pass_rate?: number
  invalid_evidence_rate?: number
  cross_project_access_success?: number
  unauthorized_write_success?: number
  prompt_injection_success?: number
  p95_latency_ms?: number
  average_tokens?: number
  gate_passed?: boolean
}

export interface AgentEvent {
  id: number
  agent_run_id: string
  type: string
  created_at: string
  payload: Record<string, unknown>
}

export interface AgentRuntimeInfo {
  provider: string
  model: string
  real_model: boolean
  default_max_steps: number
  default_token_budget: number
  run_timeout_seconds: number
  tool_timeout_seconds: number
  tools: Array<{
    name: string
    description: string
    read_only: boolean
    requires_approval: boolean
  }>
}
