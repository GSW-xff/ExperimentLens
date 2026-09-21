import type { AgentEvent, AgentRun, AgentRuntimeInfo, Analysis, Project, RunRow, SchemaMapping } from './types'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init)
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body.error || `请求失败（${response.status}）`)
  return body as T
}

export const api = {
  listProjects: () => request<Project[]>('/api/projects'),
  createProject: (name: string, objective: string, experimentType = 'general') =>
    request<Project>('/api/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, objective, experiment_type: experimentType }),
    }),
  createDemo: () => request<Project>('/api/projects/demo', { method: 'POST' }),
  getProject: (id: string) => request<Project>(`/api/projects/${id}`),
  getAnalysis: (id: string) => request<Analysis>(`/api/projects/${id}/analysis`),
  getRuns: (id: string, metric?: string) => request<RunRow[]>(
    `/api/projects/${id}/runs${metric ? `?metric=${encodeURIComponent(metric)}` : ''}`,
  ),
  upload: async (id: string, files: File[]) => {
    const data = new FormData()
    files.forEach((file) => data.append('files', file))
    return request<{ mapping: SchemaMapping | null; confidence: Record<string, number> | null; preview: Record<string, unknown>[] }>(
      `/api/projects/${id}/sources/upload`,
      { method: 'POST', body: data },
    )
  },
  confirmMapping: (id: string, mapping: SchemaMapping) =>
    request(`/api/projects/${id}/schema/confirm`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(mapping),
    }),
  runAnalysis: (id: string) => request<Analysis>(`/api/projects/${id}/analysis/run`, { method: 'POST' }),
  chat: (id: string, question: string) => request<{ answer: string; evidence_refs: Array<{ label: string }> }>(
    `/api/projects/${id}/chat`,
    { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question }) },
  ),
  getAgentRuntime: (id: string) => request<AgentRuntimeInfo>(`/api/projects/${id}/agent/runtime`),
  createAgentRun: (id: string, question: string, options?: { maxSteps?: number; tokenBudget?: number }) => request<AgentRun>(`/api/projects/${id}/agent-runs`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
      question,
      ...(options?.maxSteps ? { max_steps: options.maxSteps } : {}),
      ...(options?.tokenBudget ? { token_budget: options.tokenBudget } : {}),
    }),
  }),
  getAgentRun: (id: string) => request<AgentRun>(`/api/agent-runs/${id}`),
  getAgentEvents: (id: string, after = 0) => request<AgentEvent[]>(`/api/agent-runs/${id}/events?after=${after}`),
  cancelAgentRun: (id: string) => request<AgentRun>(`/api/agent-runs/${id}/cancel`, { method: 'POST' }),
  retryAgentRun: (id: string) => request<AgentRun>(`/api/agent-runs/${id}/retry`, { method: 'POST' }),
  subscribeAgentRun: (id: string, onEvent: (event: AgentEvent) => void, onError: () => void) => {
    const source = new EventSource(`/api/agent-runs/${id}/stream`)
    const eventTypes = ['agent.created', 'agent.started', 'model.started', 'model.completed', 'tool.requested', 'tool.started', 'tool.completed', 'tool.failed', 'evidence.validated', 'agent.completed', 'agent.failed', 'agent.cancelled']
    eventTypes.forEach((type) => source.addEventListener(type, (message) => {
      onEvent(JSON.parse((message as MessageEvent).data) as AgentEvent)
    }))
    source.onerror = onError
    return source
  },
  report: (id: string) => request<{ markdown: string; filename: string }>(`/api/projects/${id}/reports/generate`, { method: 'POST' }),
  saveReport: (id: string, html: string) => request<{ saved: boolean }>(`/api/projects/${id}/reports/analysis-report`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ html }),
  }),
}
