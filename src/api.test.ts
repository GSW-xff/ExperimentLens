import { afterEach, describe, expect, it, vi } from 'vitest'
import { api } from './api'

describe('ExperimentLens API client', () => {
  afterEach(() => vi.restoreAllMocks())

  it('creates a project with JSON payload', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ id: 'p1', name: 'Test' }), { status: 201, headers: { 'Content-Type': 'application/json' } }))
    await api.createProject('Test', 'Compare seeds')
    expect(fetchMock).toHaveBeenCalledWith('/api/projects', expect.objectContaining({ method: 'POST' }))
    const init = fetchMock.mock.calls[0][1] as RequestInit
    expect(JSON.parse(init.body as string)).toEqual({ name: 'Test', objective: 'Compare seeds' })
  })

  it('surfaces the server validation error', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ error: '请先上传实验结果表' }), { status: 400, headers: { 'Content-Type': 'application/json' } }))
    await expect(api.getAnalysis('p1')).rejects.toThrow('请先上传实验结果表')
  })

  it('uploads every selected file using multipart form data', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ mapping: null, confidence: null, preview: [] }), { status: 200, headers: { 'Content-Type': 'application/json' } }))
    const files = [new File(['run_id,score'], 'results.csv'), new File(['ok'], 'run.log')]
    await api.upload('p1', files)
    const init = fetchMock.mock.calls[0][1] as RequestInit
    const body = init.body as FormData
    expect(body.getAll('files')).toHaveLength(2)
  })
})
