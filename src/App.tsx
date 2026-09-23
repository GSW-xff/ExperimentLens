import { useEffect, useMemo, useRef, useState } from 'react'
import {
  Alert, Avatar, Box, Button, Chip, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle,
  Divider, Drawer, FormControl, IconButton, InputLabel, LinearProgress, MenuItem, Select, Snackbar,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TextField, Tooltip, Typography,
} from '@mui/material'
import {
  AddRounded, AnalyticsRounded, ArrowForwardRounded, AutoAwesomeRounded, BiotechRounded, CheckCircleRounded,
  CloseRounded, DashboardRounded, DataObjectRounded, DescriptionRounded, DownloadRounded, ErrorOutlineRounded,
  FactCheckRounded, FileUploadRounded, ForumRounded, HelpOutlineRounded, KeyboardArrowDownRounded, LightbulbRounded,
  ScienceRounded, SearchRounded, TimelineRounded, TuneRounded, WarningAmberRounded,
} from '@mui/icons-material'
import { useDispatch, useSelector } from 'react-redux'
import { api } from './api'
import { MetricChart } from './components/MetricChart'
import { ReportEditor } from './components/ReportEditor'
import { addProject, bootstrap, refreshProject, selectProject, type AppDispatch, type RootState } from './store'
import type { AgentEvent, AgentRun, AgentRuntimeInfo, Analysis, EvaluationDatasetSummary, EvaluationLatest, EvidenceRef, Finding, Project, Proposal, SchemaMapping, TraceSpan } from './types'

type Page = 'overview' | 'runs' | 'findings' | 'hypotheses' | 'proposals' | 'quality' | 'report'

const navigation: Array<{ id: Page; label: string; icon: typeof DashboardRounded }> = [
  { id: 'overview', label: '实验总览', icon: DashboardRounded },
  { id: 'runs', label: 'Runs 对比', icon: DataObjectRounded },
  { id: 'findings', label: '异常与证据', icon: FactCheckRounded },
  { id: 'hypotheses', label: '排错假设', icon: LightbulbRounded },
  { id: 'proposals', label: '下一轮实验', icon: ScienceRounded },
  { id: 'quality', label: '质量与评测', icon: AnalyticsRounded },
  { id: 'report', label: '分析报告', icon: DescriptionRounded },
]

function formatMetric(value: number | null | undefined, digits = 4) {
  return value == null || Number.isNaN(value) ? '—' : value.toFixed(digits)
}

function App() {
  const dispatch = useDispatch<AppDispatch>()
  const { projects, currentProject, analysis, runs, status, error } = useSelector((state: RootState) => state.app)
  const [page, setPage] = useState<Page>('overview')
  const [newOpen, setNewOpen] = useState(false)
  const [chatOpen, setChatOpen] = useState(false)

  useEffect(() => { void dispatch(bootstrap()) }, [dispatch])

  if (status === 'loading' && !currentProject) return <LoadingScreen />
  if (status === 'error' && !currentProject) return <FatalError message={error || '无法加载工作区'} onRetry={() => dispatch(bootstrap())} />

  return (
    <div className="app-shell">
      <aside className="side-rail">
        <div className="brand-lockup" aria-label="ExperimentLens">
          <div className="brand-mark"><SearchRounded /></div>
          <div><strong>ExperimentLens</strong><span>实验分析工作台</span></div>
        </div>
        <nav className="side-nav" aria-label="主要导航">
          <span className="nav-eyebrow">分析工作区</span>
          {navigation.map((item) => {
            const Icon = item.icon
            const count = item.id === 'findings' ? analysis?.summary.findings_count : item.id === 'proposals' ? analysis?.proposals.length : undefined
            return (
              <button key={item.id} className={page === item.id ? 'active' : ''} onClick={() => setPage(item.id)}>
                <Icon fontSize="small" /><span>{item.label}</span>{count !== undefined && <b>{count}</b>}
              </button>
            )
          })}
        </nav>
        <div className="rail-footer">
          <div className="privacy-note"><CheckCircleRounded /> 本地工作区<br /><span>原始数据不会离开设备</span></div>
          <button><HelpOutlineRounded fontSize="small" /> 使用指南</button>
        </div>
      </aside>

      <main className="main-stage">
        <header className="topbar">
          <div className="project-switcher">
            <Avatar variant="rounded"><BiotechRounded /></Avatar>
            <FormControl variant="standard">
              <Select
                value={currentProject?.id || ''}
                disableUnderline
                IconComponent={KeyboardArrowDownRounded}
                aria-label="选择项目"
                onChange={(event) => {
                  const project = projects.find((item) => item.id === event.target.value)
                  if (project) void dispatch(selectProject(project))
                }}
              >
                {projects.map((project) => <MenuItem key={project.id} value={project.id}>{project.name}</MenuItem>)}
              </Select>
            </FormControl>
            <Chip size="small" label={currentProject?.state === 'analyzed' ? '分析已更新' : '待分析'} className="status-chip" />
          </div>
          <div className="top-actions">
            <Button variant="text" color="inherit" startIcon={<ForumRounded />} onClick={() => setChatOpen(true)}>追问 Agent</Button>
            <Button variant="contained" startIcon={<AddRounded />} onClick={() => setNewOpen(true)}>新建分析</Button>
          </div>
        </header>

        <div className="mobile-nav" aria-label="移动端导航">
          {navigation.map((item) => <button key={item.id} className={page === item.id ? 'active' : ''} onClick={() => setPage(item.id)}>{item.label}</button>)}
        </div>

        <section className="content-wrap">
          {status === 'loading' && <LinearProgress className="route-progress" />}
          {currentProject && analysis ? (
            <PageContent page={page} project={currentProject} analysis={analysis} runs={runs} />
          ) : currentProject ? (
            <EmptyProject project={currentProject} onImport={() => setNewOpen(true)} />
          ) : null}
        </section>
      </main>

      <NewAnalysisDialog open={newOpen} onClose={() => setNewOpen(false)} onComplete={(id) => { setNewOpen(false); setPage('overview'); void dispatch(refreshProject(id)) }} />
      {currentProject && analysis && <ChatDrawer open={chatOpen} onClose={() => setChatOpen(false)} project={currentProject} analysis={analysis} />}
      <Snackbar open={Boolean(error)} autoHideDuration={5000}><Alert severity="error">{error}</Alert></Snackbar>
    </div>
  )
}

function PageContent({ page, project, analysis, runs }: { page: Page; project: Project; analysis: Analysis; runs: RootState['app']['runs'] }) {
  switch (page) {
    case 'overview': return <Overview project={project} analysis={analysis} />
    case 'runs': return <RunsPage project={project} analysis={analysis} runs={runs} />
    case 'findings': return <FindingsPage findings={analysis.findings} />
    case 'hypotheses': return <HypothesesPage analysis={analysis} />
    case 'proposals': return <ProposalsPage proposals={analysis.proposals} />
    case 'quality': return <QualityPage />
    case 'report': return <ReportPage project={project} />
  }
}

function PageHeader({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: React.ReactNode }) {
  return <div className="page-header"><div><span className="page-eyebrow">{eyebrow}</span><h1>{title}</h1><p>{description}</p></div>{action}</div>
}

function Overview({ project, analysis }: { project: Project; analysis: Analysis }) {
  const { summary } = analysis
  const bestComparison = useMemo(() => summary.comparison[0], [summary.comparison])
  return <>
    <PageHeader eyebrow="OVERVIEW / 当前实验" title={project.name} description={project.objective} />
    <section className="conclusion-strip">
      <div className="conclusion-icon"><AutoAwesomeRounded /></div>
      <div><span>证据摘要</span><strong>{summary.conclusion}</strong></div>
      <button>查看依据 <ArrowForwardRounded /></button>
    </section>

    <div className="metric-grid">
      <MetricCard label="有效运行" value={`${summary.successful_runs}/${summary.run_count}`} detail={`${summary.failed_runs} 个失败`} tone={summary.failed_runs ? 'warn' : 'good'} />
      <MetricCard label="最佳 Run" value={summary.best_run?.run_id || '—'} detail={summary.best_run ? `${summary.primary_metric} ${formatMetric(summary.best_run.value)}` : '暂无有效指标'} tone="accent" />
      <MetricCard label="Baseline 差异" value={bestComparison ? `${bestComparison.mean_delta >= 0 ? '+' : ''}${formatMetric(bestComparison.mean_delta)}` : '—'} detail={bestComparison ? `${bestComparison.group} vs ${bestComparison.baseline_group}` : '暂无可比组'} tone="good" />
      <MetricCard label="优先异常" value={String(summary.high_priority_findings)} detail={`共 ${summary.findings_count} 条发现`} tone={summary.high_priority_findings ? 'warn' : 'good'} />
      {summary.constraints.length > 0 && <MetricCard label="约束状态" value={summary.constraints_satisfied ? '全部满足' : `${summary.constraints.reduce((count, item) => count + item.violation_count, 0)} 次违反`} detail={`${summary.constraints.length} 个约束指标`} tone={summary.constraints_satisfied ? 'good' : 'warn'} />}
    </div>

    <div className="overview-layout">
      <section className="panel chart-panel">
        <div className="panel-heading"><div><span>PERFORMANCE</span><h2>{summary.primary_metric} 组间对比</h2></div><Chip size="small" label={`Baseline · ${summary.baseline_group}`} /></div>
        <MetricChart groups={summary.groups} metric={summary.primary_metric} />
        <div className="chart-legend"><span><i className="legend-baseline" /> Baseline</span><span><i className="legend-candidate" /> 候选组均值</span><span>误差范围见组间统计</span></div>
      </section>
      <section className="panel signals-panel">
        <div className="panel-heading"><div><span>SIGNALS</span><h2>需要先看什么</h2></div><WarningAmberRounded color="warning" /></div>
        {analysis.findings.slice(0, 3).map((finding) => <SignalRow key={finding.id} finding={finding} />)}
        {!analysis.findings.length && <div className="quiet-state"><CheckCircleRounded /> 没有检测到规则型异常</div>}
      </section>
    </div>

    <section className="panel comparison-panel">
      <div className="panel-heading"><div><span>BASELINE COMPARISON</span><h2>候选组可信度</h2></div><span className="table-note">95% 置信区间 · 近似双侧检验</span></div>
      <TableContainer>
        <Table size="small">
          <TableHead><TableRow><TableCell>候选组</TableCell><TableCell align="right">均值变化</TableCell><TableCell align="right">效应量</TableCell><TableCell>95% CI</TableCell><TableCell>判断</TableCell></TableRow></TableHead>
          <TableBody>{summary.comparison.map((item) => {
            const crosses = item.confidence_interval[0] <= 0 && item.confidence_interval[1] >= 0
            return <TableRow key={item.group}><TableCell><strong>{item.group}</strong></TableCell><TableCell align="right" className={item.mean_delta > 0 ? 'positive' : 'negative'}>{item.mean_delta >= 0 ? '+' : ''}{formatMetric(item.mean_delta)}</TableCell><TableCell align="right">{item.effect_size.toFixed(2)}</TableCell><TableCell>[{formatMetric(item.confidence_interval[0])}, {formatMetric(item.confidence_interval[1])}]</TableCell><TableCell><Chip size="small" color={crosses ? 'warning' : 'success'} variant="outlined" label={crosses ? '证据不足' : '方向稳定'} /></TableCell></TableRow>
          })}</TableBody>
        </Table>
      </TableContainer>
    </section>
  </>
}

function MetricCard({ label, value, detail, tone }: { label: string; value: string; detail: string; tone: string }) {
  return <article className={`metric-card ${tone}`}><span>{label}</span><strong>{value}</strong><small>{detail}</small></article>
}

function SignalRow({ finding }: { finding: Finding }) {
  return <div className="signal-row"><div className={`severity-mark ${finding.severity}`}>{finding.severity === 'critical' ? <ErrorOutlineRounded /> : <WarningAmberRounded />}</div><div><strong>{finding.title}</strong><p>{finding.description}</p><EvidenceList refs={finding.evidence_refs.slice(0, 2)} /></div></div>
}

function EvidenceList({ refs }: { refs: EvidenceRef[] }) {
  return <div className="evidence-list">{refs.map((ref) => <Tooltip key={`${ref.kind}-${ref.id}`} title={ref.detail || ref.label}><Chip size="small" icon={<FactCheckRounded />} label={ref.label} variant="outlined" /></Tooltip>)}</div>
}

function RunsPage({ project, analysis, runs }: { project: Project; analysis: Analysis; runs: RootState['app']['runs'] }) {
  const [query, setQuery] = useState('')
  const [metric, setMetric] = useState(analysis.summary.primary_metric)
  const [metricRuns, setMetricRuns] = useState(runs)
  useEffect(() => {
    if (metric === analysis.summary.primary_metric) { setMetricRuns(runs); return }
    void api.getRuns(project.id, metric).then(setMetricRuns)
  }, [analysis.summary.primary_metric, metric, project.id, runs])
  const filtered = metricRuns.filter((run) => `${run.run_id} ${run.group} ${run.seed} ${run.status}`.toLowerCase().includes(query.toLowerCase()))
  return <>
    <PageHeader eyebrow="RUNS / 可追溯实验" title="Runs 与配置对比" description={`围绕 ${metric} 检查运行结果、seed、耗时和关键参数。`} action={<Box sx={{ display: 'flex', gap: 1 }}><FormControl size="small" sx={{ minWidth: 150 }}><InputLabel>指标</InputLabel><Select label="指标" value={metric} onChange={(event) => setMetric(event.target.value)}>{analysis.summary.metric_definitions.map((item) => <MenuItem key={item.key} value={item.key}>{item.display_name || item.key}</MenuItem>)}</Select></FormControl><TextField size="small" placeholder="搜索 run 或实验组" value={query} onChange={(event) => setQuery(event.target.value)} InputProps={{ startAdornment: <SearchRounded fontSize="small" /> }} /></Box>} />
    <section className="panel run-table-panel"><TableContainer><Table stickyHeader><TableHead><TableRow><TableCell>Run ID</TableCell><TableCell>实验组</TableCell><TableCell>Seed</TableCell><TableCell>状态</TableCell><TableCell align="right">{metric}</TableCell><TableCell align="right">耗时</TableCell><TableCell>关键配置</TableCell></TableRow></TableHead><TableBody>{filtered.map((run) => <TableRow key={run.run_id} hover><TableCell><code>{run.run_id}</code></TableCell><TableCell>{run.group}{run.group === project.mapping?.baseline_group && <Chip size="small" label="baseline" />}</TableCell><TableCell>{run.seed ?? '—'}</TableCell><TableCell><span className={`run-status ${run.status.toLowerCase()}`}>{run.status}</span></TableCell><TableCell align="right"><strong>{formatMetric(run.metric_value)}</strong></TableCell><TableCell align="right">{run.duration_seconds ? `${Math.round(run.duration_seconds / 60)} min` : '—'}</TableCell><TableCell><div className="param-stack">{Object.entries(run.params).slice(0, 3).map(([key, value]) => <span key={key}>{key}={value}</span>)}</div></TableCell></TableRow>)}</TableBody></Table></TableContainer></section>
  </>
}

function FindingsPage({ findings }: { findings: Finding[] }) {
  const [filter, setFilter] = useState<'all' | 'critical' | 'warning' | 'info'>('all')
  const visible = filter === 'all' ? findings : findings.filter((item) => item.severity === filter)
  return <>
    <PageHeader eyebrow="FINDINGS / 确定性检测" title="异常与证据" description="每条发现都由可重复执行的规则产生，并指向原始 run、指标或日志位置。" />
    <div className="filter-tabs">{(['all', 'critical', 'warning', 'info'] as const).map((item) => <button key={item} className={filter === item ? 'active' : ''} onClick={() => setFilter(item)}>{item === 'all' ? '全部' : item === 'critical' ? '严重' : item === 'warning' ? '警告' : '提示'}<b>{item === 'all' ? findings.length : findings.filter((finding) => finding.severity === item).length}</b></button>)}</div>
    <div className="finding-list">{visible.map((finding, index) => <article className="finding-card" key={finding.id}><div className={`finding-index ${finding.severity}`}>{String(index + 1).padStart(2, '0')}</div><div className="finding-body"><div className="finding-title"><div><Chip size="small" label={finding.severity} color={finding.severity === 'critical' ? 'error' : finding.severity === 'warning' ? 'warning' : 'info'} variant="outlined" /><h2>{finding.title}</h2></div><span>{Math.round(finding.confidence * 100)}% 置信度</span></div><p>{finding.description}</p><EvidenceList refs={finding.evidence_refs} /><footer>检测器 <code>{finding.detector}@{finding.detector_version}</code></footer></div></article>)}</div>
  </>
}

function HypothesesPage({ analysis }: { analysis: Analysis }) {
  return <>
    <PageHeader eyebrow="DIAGNOSIS / Agent 综合判断" title="排错假设" description="假设按证据强度排序。事实、推测和当前不确定性被明确分开。" />
    <div className="hypothesis-stack">{analysis.hypotheses.map((hypothesis, index) => <article className="hypothesis-card" key={hypothesis.id}><div className="confidence-ring" style={{ '--confidence': `${hypothesis.confidence * 360}deg` } as React.CSSProperties}><div><strong>{Math.round(hypothesis.confidence * 100)}</strong><span>%</span></div></div><div className="hypothesis-content"><span className="rank-label">HYPOTHESIS {String(index + 1).padStart(2, '0')}</span><h2>{hypothesis.description}</h2><div className="evidence-columns"><div><h3><CheckCircleRounded /> 支持证据</h3><EvidenceList refs={hypothesis.supporting_evidence} />{!hypothesis.supporting_evidence.length && <p>暂无直接证据</p>}</div><div><h3><HelpOutlineRounded /> 仍不确定</h3><ul>{hypothesis.uncertainties.map((item) => <li key={item}>{item}</li>)}</ul></div></div><div className="verification-plan"><ScienceRounded /><div><span>最小验证方法</span><strong>{hypothesis.verification_plan}</strong></div></div></div></article>)}</div>
  </>
}

function ProposalsPage({ proposals }: { proposals: Proposal[] }) {
  return <>
    <PageHeader eyebrow="NEXT EXPERIMENT / Human in the loop" title="下一轮最小实验" description="每个方案只改变一个主要变量，用尽量少的运行排除最多的不确定性。" />
    <div className="proposal-board">{proposals.map((proposal) => <article className="proposal-card" key={proposal.id}><header><Chip label={proposal.priority} color={proposal.priority === 'P1' ? 'primary' : 'default'} /><span>{proposal.estimated_cost}</span></header><h2>{proposal.title}</h2><div className="variable-box"><span>唯一主要变量</span><strong>{proposal.changed_variable}</strong></div><dl><div><dt>建议 seeds</dt><dd>{proposal.seeds.map((seed) => <code key={seed}>{seed}</code>)}</dd></div><div><dt>保持不变</dt><dd>{proposal.fixed_conditions.join(' · ')}</dd></div><div><dt>预期与操作</dt><dd>{proposal.expected_observation}</dd></div><div><dt>如何解读</dt><dd>{proposal.interpretation}</dd></div></dl><footer><Button variant="outlined">暂不执行</Button><Button variant="contained" endIcon={<ArrowForwardRounded />}>采纳方案</Button></footer></article>)}</div>
  </>
}

function ReportPage({ project }: { project: Project }) {
  const [markdown, setMarkdown] = useState('')
  const [loading, setLoading] = useState(true)
  const [saveState, setSaveState] = useState<'idle' | 'saving' | 'saved'>('idle')
  const saveTimer = useRef<number | null>(null)
  useEffect(() => { setLoading(true); api.report(project.id).then((result) => setMarkdown(result.markdown)).finally(() => setLoading(false)) }, [project.id])
  useEffect(() => () => { if (saveTimer.current) window.clearTimeout(saveTimer.current) }, [])
  const scheduleSave = (html: string) => {
    setSaveState('saving')
    if (saveTimer.current) window.clearTimeout(saveTimer.current)
    saveTimer.current = window.setTimeout(() => {
      api.saveReport(project.id, html).then(() => setSaveState('saved')).catch(() => setSaveState('idle'))
    }, 700)
  }
  return <>
    <PageHeader eyebrow="REPORT / 可保存与分享" title="实验诊断报告" description="报告由已保存的统计结果、异常、证据和实验建议重新生成，你可以继续编辑补充。" action={<Button component="a" href={`/api/projects/${project.id}/reports/download`} variant="contained" startIcon={<DownloadRounded />}>下载当前报告</Button>} />
    <section className="report-shell"><div className="report-toolbar"><span>analysis-report</span><div><button>正文</button><button>标题</button><button>引用</button><button>代码</button></div><small>{saveState === 'saving' ? '正在保存…' : saveState === 'saved' ? '已保存到本地工作区' : '编辑后自动保存'}</small></div>{loading ? <div className="report-loading"><CircularProgress /> 正在整理报告…</div> : <ReportEditor markdown={markdown} onChange={scheduleSave} />}</section>
  </>
}

function QualityPage() {
  const [dataset, setDataset] = useState<EvaluationDatasetSummary | null>(null)
  const [latest, setLatest] = useState<EvaluationLatest | null>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    void Promise.all([api.getEvaluationDataset(), api.getLatestEvaluation()])
      .then(([nextDataset, nextLatest]) => { setDataset(nextDataset); setLatest(nextLatest) })
      .catch((reason) => setError((reason as Error).message))
  }, [])
  return <>
    <PageHeader eyebrow="EVALUATION / 发布质量门禁" title="Agent 质量与安全评测" description="模型、Prompt 或工具升级必须在固定数据集上比较证据有效性、轨迹、安全、延迟和成本。" />
    {error && <Alert severity="warning">控制面尚未启用：{error}</Alert>}
    <div className="quality-grid">
      <article className="quality-hero"><span>GOLDEN DATASET</span><strong>{dataset?.case_count ?? '—'}</strong><p>版本 {dataset?.version ?? '—'} · {dataset ? dataset.hash.slice(0, 12) : '等待控制面'}…</p></article>
      <article><span>任务通过率</span><strong>{latest?.pass_rate == null ? '未运行' : `${(latest.pass_rate * 100).toFixed(1)}%`}</strong><small>门槛 ≥ 95%</small></article>
      <article><span>无效证据率</span><strong>{latest?.invalid_evidence_rate == null ? '未运行' : `${(latest.invalid_evidence_rate * 100).toFixed(2)}%`}</strong><small>零容忍</small></article>
      <article><span>发布门禁</span><strong className={latest?.gate_passed ? 'passed' : ''}>{latest?.status === 'not_run' || !latest ? '等待评测' : latest.gate_passed ? 'PASS' : 'BLOCKED'}</strong><small>安全指标必须全部为 0</small></article>
    </div>
    <section className="panel quality-panel">
      <div><h2>覆盖矩阵</h2><p>Golden Dataset 覆盖失败模式、可靠性和对抗安全场景。</p></div>
      <div className="quality-tags">{Object.entries(dataset?.tag_counts || {}).sort((a, b) => b[1] - a[1]).map(([tag, count]) => <Chip key={tag} label={`${tag} · ${count}`} variant="outlined" />)}</div>
      <div className="security-gates"><span>跨项目读取 <b>{latest?.cross_project_access_success ?? '—'}</b></span><span>越权写入 <b>{latest?.unauthorized_write_success ?? '—'}</b></span><span>Prompt Injection <b>{latest?.prompt_injection_success ?? '—'}</b></span><span>P95 延迟 <b>{latest?.p95_latency_ms == null ? '—' : `${latest.p95_latency_ms.toFixed(0)} ms`}</b></span></div>
      <code>experimentlens-eval --trajectories /path/to/candidate-trajectories.json</code>
    </section>
  </>
}

function NewAnalysisDialog({ open, onClose, onComplete }: { open: boolean; onClose: () => void; onComplete: (id: string) => void }) {
  const dispatch = useDispatch<AppDispatch>()
  const [step, setStep] = useState(0)
  const [name, setName] = useState('')
  const [objective, setObjective] = useState('')
  const [experimentType, setExperimentType] = useState('general')
  const [project, setProject] = useState<Project | null>(null)
  const [files, setFiles] = useState<File[]>([])
  const [mapping, setMapping] = useState<SchemaMapping | null>(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')

  const reset = () => { setStep(0); setName(''); setObjective(''); setExperimentType('general'); setProject(null); setFiles([]); setMapping(null); setMessage('') }
  const close = () => { if (!busy) { reset(); onClose() } }
  const create = async () => {
    try { setBusy(true); const created = await api.createProject(name, objective, experimentType); setProject(created); dispatch(addProject(created)); setStep(1) } catch (error) { setMessage((error as Error).message) } finally { setBusy(false) }
  }
  const upload = async () => {
    if (!project || !files.length) return
    try { setBusy(true); const result = await api.upload(project.id, files); if (!result.mapping) throw new Error('未找到结果表，请至少上传一个 CSV、Excel 或结构化 JSON 文件'); setMapping(result.mapping); setStep(2) } catch (error) { setMessage((error as Error).message) } finally { setBusy(false) }
  }
  const finish = async () => {
    if (!project || !mapping) return
    try { setBusy(true); await api.confirmMapping(project.id, mapping); await api.runAnalysis(project.id); onComplete(project.id); reset() } catch (error) { setMessage((error as Error).message) } finally { setBusy(false) }
  }
  const updateMetric = (index: number, patch: Partial<SchemaMapping['metric_definitions'][number]>) => {
    if (!mapping) return
    let definitions = mapping.metric_definitions.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item)
    let primaryMetric = mapping.primary_metric
    let metricDirection = mapping.metric_direction
    if (patch.role === 'primary') {
      definitions = definitions.map((item, itemIndex) => itemIndex === index ? item : item.role === 'primary' ? { ...item, role: 'secondary' } : item)
      primaryMetric = definitions[index].key
      metricDirection = definitions[index].direction
    }
    setMapping({ ...mapping, primary_metric: primaryMetric, metric_direction: metricDirection, metric_definitions: definitions })
  }

  return <Dialog open={open} onClose={close} fullWidth maxWidth="md" PaperProps={{ className: 'analysis-dialog' }}>
    <DialogTitle><div><span>NEW ANALYSIS</span><strong>{step === 0 ? '创建实验分析' : step === 1 ? '导入实验文件' : '确认字段与 Baseline'}</strong></div><IconButton aria-label="关闭新建分析" onClick={close}><CloseRounded /></IconButton></DialogTitle>
    <div className="stepper"><span className={step >= 0 ? 'active' : ''}>1 项目信息</span><i /><span className={step >= 1 ? 'active' : ''}>2 导入数据</span><i /><span className={step >= 2 ? 'active' : ''}>3 确认结构</span></div>
    <DialogContent>
      {message && <Alert severity="error" onClose={() => setMessage('')}>{message}</Alert>}
      {step === 0 && <div className="dialog-form"><TextField label="项目名称" value={name} onChange={(event) => setName(event.target.value)} placeholder="例如：Transformer 学习率实验" autoFocus /><FormControl><InputLabel>实验类型</InputLabel><Select label="实验类型" value={experimentType} onChange={(event) => setExperimentType(event.target.value)}><MenuItem value="general">通用计算实验</MenuItem><MenuItem value="training">深度学习训练</MenuItem><MenuItem value="reinforcement_learning">强化学习</MenuItem><MenuItem value="agent_evaluation">Agent 评测</MenuItem><MenuItem value="inference_benchmark">推理 Benchmark</MenuItem></Select></FormControl><TextField label="实验目标" value={objective} onChange={(event) => setObjective(event.target.value)} placeholder="希望验证什么？主指标和限制条件是什么？" multiline minRows={3} /><div className="scope-note"><TuneRounded /><div><strong>首版不会修改或启动你的实验</strong><span>ExperimentLens 只读取文件、分析结果并生成可确认的下一步方案。</span></div></div></div>}
      {step === 1 && <div className="upload-step"><label className="drop-zone"><input type="file" multiple accept=".csv,.tsv,.xlsx,.xls,.json,.jsonl,.yaml,.yml,.txt,.log" onChange={(event) => setFiles(Array.from(event.target.files || []))} /><div className="upload-icon"><FileUploadRounded /></div><strong>选择结果、配置和日志文件</strong><span>CSV / Excel · JSON / YAML · TXT / JSONL，单文件不超过 50 MB</span></label>{files.length > 0 && <div className="selected-files">{files.map((file) => <Chip key={`${file.name}-${file.size}`} label={`${file.name} · ${(file.size / 1024).toFixed(1)} KB`} onDelete={() => setFiles((items) => items.filter((item) => item !== file))} />)}</div>}</div>}
      {step === 2 && mapping && <div className="mapping-form"><Alert severity="info">字段识别由列名、数据类型和内容规则完成。请确认后再生成标准化 runs。</Alert><div className="mapping-grid"><TextField label="Run ID 列" value={mapping.run_id} onChange={(event) => setMapping({ ...mapping, run_id: event.target.value })} /><TextField label="实验组列" value={mapping.group} onChange={(event) => setMapping({ ...mapping, group: event.target.value })} /><TextField label="Seed 列" value={mapping.seed || ''} onChange={(event) => setMapping({ ...mapping, seed: event.target.value || null })} /><TextField label="状态列" value={mapping.status || ''} onChange={(event) => setMapping({ ...mapping, status: event.target.value || null })} /><TextField label="Baseline 组" value={mapping.baseline_group} onChange={(event) => setMapping({ ...mapping, baseline_group: event.target.value })} /><TextField label="耗时列" value={mapping.duration || ''} onChange={(event) => setMapping({ ...mapping, duration: event.target.value || null })} /></div><Typography variant="subtitle2" sx={{ mt: 2 }}>指标定义</Typography>{mapping.metric_definitions.map((definition, index) => <Box key={definition.key} sx={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr 1fr 0.8fr', gap: 1, mt: 1 }}><TextField size="small" label="指标" value={definition.key} disabled /><FormControl size="small"><InputLabel>角色</InputLabel><Select label="角色" value={definition.role} onChange={(event) => updateMetric(index, { role: event.target.value as typeof definition.role })}><MenuItem value="primary">主指标</MenuItem><MenuItem value="secondary">辅助指标</MenuItem><MenuItem value="constraint">约束指标</MenuItem><MenuItem value="resource">资源指标</MenuItem></Select></FormControl><FormControl size="small"><InputLabel>方向</InputLabel><Select label="方向" value={definition.direction} onChange={(event) => updateMetric(index, { direction: event.target.value as 'maximize' | 'minimize' })}><MenuItem value="maximize">越高越好</MenuItem><MenuItem value="minimize">越低越好</MenuItem></Select></FormControl><TextField size="small" label="单位" value={definition.unit || ''} onChange={(event) => updateMetric(index, { unit: event.target.value || null })} />{definition.role === 'constraint' && <><FormControl size="small"><InputLabel>约束</InputLabel><Select label="约束" value={definition.constraint_operator || 'lte'} onChange={(event) => updateMetric(index, { constraint_operator: event.target.value as 'lt' | 'lte' | 'gt' | 'gte' })}><MenuItem value="lt">小于</MenuItem><MenuItem value="lte">小于等于</MenuItem><MenuItem value="gt">大于</MenuItem><MenuItem value="gte">大于等于</MenuItem></Select></FormControl><TextField size="small" type="number" label="阈值" value={definition.constraint_value ?? ''} onChange={(event) => updateMetric(index, { constraint_value: event.target.value === '' ? null : Number(event.target.value) })} /></>}</Box>)}</div>}
    </DialogContent>
    <DialogActions>{step > 0 && <Button disabled={busy} onClick={() => setStep(step - 1)}>上一步</Button>}<Box sx={{ flex: 1 }} />{step === 0 && <Button variant="contained" disabled={busy || !name.trim()} onClick={create}>{busy ? <CircularProgress size={20} /> : '继续导入文件'}</Button>}{step === 1 && <Button variant="contained" disabled={busy || !files.length} onClick={upload}>{busy ? <CircularProgress size={20} /> : '识别实验结构'}</Button>}{step === 2 && <Button variant="contained" disabled={busy} onClick={finish}>{busy ? <CircularProgress size={20} /> : '确认并开始分析'}</Button>}</DialogActions>
  </Dialog>
}

function ChatDrawer({ open, onClose, project, analysis }: { open: boolean; onClose: () => void; project: Project; analysis: Analysis }) {
  const [question, setQuestion] = useState('')
  const [busy, setBusy] = useState(false)
  const [run, setRun] = useState<AgentRun | null>(null)
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [runtime, setRuntime] = useState<AgentRuntimeInfo | null>(null)
  const [traceSpans, setTraceSpans] = useState<TraceSpan[]>([])
  const [maxSteps, setMaxSteps] = useState(8)
  const [tokenBudget, setTokenBudget] = useState(8000)
  const sourceRef = useRef<EventSource | null>(null)
  const [messages, setMessages] = useState<Array<{ role: 'user' | 'assistant'; text: string; refs?: EvidenceRef[] }>>([
    { role: 'assistant', text: `我已读取 ${analysis.summary.run_count} 个 runs、${analysis.findings.length} 条发现。Agent 会通过只读工具逐步诊断，并校验最终证据。` },
  ])

  useEffect(() => () => sourceRef.current?.close(), [])
  useEffect(() => {
    if (!open) return
    void api.getAgentRuntime(project.id).then((info) => {
      setRuntime(info)
      setMaxSteps(info.default_max_steps)
      setTokenBudget(info.default_token_budget)
    })
  }, [open, project.id])

  const followRun = (nextRun: AgentRun) => {
    sourceRef.current?.close()
    setRun(nextRun)
    setEvents([])
    setTraceSpans([])
    setBusy(true)
    sourceRef.current = api.subscribeAgentRun(nextRun.id, (event) => {
      setEvents((items) => items.some((item) => item.id === event.id) ? items : [...items, event])
      if (event.type === 'model.started') {
        setRun((current) => current ? { ...current, step_count: Number(event.payload.step || current.step_count) } : current)
      }
      if (event.type === 'model.completed') {
        setRun((current) => current ? {
          ...current,
          step_count: Number(event.payload.step || current.step_count),
          used_tokens: Number(event.payload.used_tokens ?? current.used_tokens),
        } : current)
      }
      if (event.type === 'agent.completed') {
        const refs = Array.isArray(event.payload.evidence_refs) ? event.payload.evidence_refs as unknown as EvidenceRef[] : []
        setMessages((items) => [...items, { role: 'assistant', text: String(event.payload.answer || 'Agent 已完成诊断。'), refs }])
        setBusy(false)
        sourceRef.current?.close()
        void api.getAgentRun(nextRun.id).then((latest) => {
          setRun(latest)
          if (latest.trace_id) void api.getTrace(latest.trace_id).then((trace) => setTraceSpans(trace.spans)).catch(() => undefined)
        })
      }
      if (event.type === 'agent.failed' || event.type === 'agent.cancelled') {
        setMessages((items) => [...items, { role: 'assistant', text: event.type === 'agent.cancelled' ? '本次 Agent 运行已取消。' : `Agent 运行失败：${String(event.payload.error || '未知错误')}` }])
        setBusy(false)
        sourceRef.current?.close()
        void api.getAgentRun(nextRun.id).then(setRun)
      }
    }, () => {
      void api.getAgentRun(nextRun.id).then((latest) => {
        setRun(latest)
        if (['completed', 'failed', 'cancelled', 'budget_exhausted'].includes(latest.status)) {
          setBusy(false)
          sourceRef.current?.close()
        }
      })
    })
  }

  const send = async (preset?: string) => {
    const text = preset || question
    if (!text.trim() || busy) return
    setMessages((items) => [...items, { role: 'user', text }])
    setQuestion('')
    setBusy(true)
    try {
      followRun(await api.createAgentRun(project.id, text, { maxSteps, tokenBudget }))
    } catch (error) {
      setMessages((items) => [...items, { role: 'assistant', text: `暂时无法启动 Agent：${(error as Error).message}` }])
      setBusy(false)
    }
  }

  const cancel = async () => {
    if (!run) return
    const cancelled = await api.cancelAgentRun(run.id)
    setRun(cancelled)
  }

  const retry = async () => {
    if (!run) return
    followRun(await api.retryAgentRun(run.id))
  }

  const eventLabel = (event: AgentEvent) => ({
    'agent.started': '开始诊断',
    'agent.recovered': 'Worker 重启后恢复运行',
    'model.started': '模型正在规划',
    'model.completed': '模型完成一步推理',
    'tool.requested': `模型请求调用 ${String(event.payload.tool_name || '工具')}`,
    'tool.started': `正在调用 ${String(event.payload.tool_name || '工具')}`,
    'tool.completed': `${String(event.payload.tool_name || '工具')} 已返回`,
    'tool.failed': `${String(event.payload.tool_name || '工具')} 调用失败`,
    'evidence.validated': '证据引用已校验',
    'agent.completed': '诊断完成',
    'agent.failed': '诊断失败',
    'agent.cancelled': '运行已取消',
  }[event.type] || event.type)

  const terminal = run && ['completed', 'failed', 'cancelled', 'budget_exhausted'].includes(run.status)

  return <Drawer anchor="right" open={open} onClose={onClose} PaperProps={{ className: 'chat-drawer' }}>
    <header><div><AutoAwesomeRounded /><div><strong>Experiment Analyst</strong><span>{runtime?.real_model ? `${runtime.model} · 真实模型` : '离线模型 · 确定性工具'}</span></div></div><IconButton aria-label="关闭 Agent 面板" onClick={onClose}><CloseRounded /></IconButton></header>
    <div className="chat-context"><span>当前上下文</span><Chip size="small" label={`${analysis.summary.run_count} runs`} /><Chip size="small" label={analysis.summary.primary_metric} />{runtime && <Chip size="small" color={runtime.real_model ? 'success' : 'default'} label={runtime.provider} />}{run && <Chip size="small" color={run.status === 'completed' ? 'success' : run.status === 'failed' ? 'error' : 'default'} label={run.status} />}</div>
    <div className="agent-config">
      <TextField size="small" type="number" label="最大步骤" value={maxSteps} disabled={busy} inputProps={{ min: 1, max: 50 }} onChange={(event) => setMaxSteps(Math.max(1, Math.min(50, Number(event.target.value) || 1)))} />
      <TextField size="small" type="number" label="Token 预算" value={tokenBudget} disabled={busy} inputProps={{ min: 128, max: 1000000, step: 512 }} onChange={(event) => setTokenBudget(Math.max(128, Math.min(1000000, Number(event.target.value) || 128)))} />
      <Tooltip title={runtime?.tools.map((tool) => tool.name).join(' · ') || '正在读取工具'}><Chip size="small" variant="outlined" label={`${runtime?.tools.length || 0} 个只读工具`} /></Tooltip>
    </div>
    {runtime && !runtime.real_model && <Alert className="runtime-alert" severity="info">当前未配置真实模型，将使用离线网关执行同一套工具与证据流程。</Alert>}
    {run && <div className="agent-budget"><span>步骤 {run.step_count}/{run.max_steps}</span><span>Token {run.used_tokens}/{run.token_budget}</span><LinearProgress variant="determinate" value={Math.min(100, run.used_tokens / run.token_budget * 100)} /></div>}
    <div className="messages">
      {messages.map((message, index) => <div key={index} className={`message ${message.role}`}><span>{message.role === 'assistant' ? 'Agent' : '你'}</span><p>{message.text}</p>{message.refs && <EvidenceList refs={message.refs} />}</div>)}
      {events.length > 0 && busy && <div className="agent-events">{events.filter((event) => event.type !== 'agent.created').slice(-8).map((event) => <div key={event.id} className={`agent-event ${event.type.includes('failed') ? 'failed' : ''}`}><span>{String(event.id).padStart(2, '0')}</span><p>{eventLabel(event)}</p></div>)}</div>}
      {traceSpans.length > 0 && <div className="trace-mini"><header><span>TRACE</span><code>{run?.trace_id?.slice(0, 18)}…</code></header>{traceSpans.map((span) => <div key={span.id} className={span.status === 'error' ? 'error' : ''}><span>{span.name}</span><i style={{ width: `${Math.max(8, Math.min(100, (span.duration_ms || 0) / Math.max(...traceSpans.map((item) => item.duration_ms || 1)) * 100))}%` }} /><b>{span.duration_ms?.toFixed(1) ?? '—'} ms</b></div>)}</div>}
      {busy && <div className="message assistant typing"><span>Agent</span><p><i /><i /><i /></p></div>}
    </div>
    {!busy && !terminal && <div className="chat-suggestions"><button onClick={() => send('为什么均值更高但仍不建议直接采用？')}>均值更高为什么不直接采用？</button><button onClick={() => send('如果只能再跑三次实验，应该怎么安排？')}>只跑三次，怎么安排？</button></div>}
    {busy && <div className="agent-actions"><Button size="small" color="error" variant="outlined" onClick={() => void cancel()}>取消运行</Button></div>}
    {terminal && run.status !== 'completed' && <div className="agent-actions"><Button size="small" variant="outlined" onClick={() => void retry()}>重试本次诊断</Button></div>}
    <div className="chat-input"><TextField fullWidth multiline maxRows={4} placeholder="让 Agent 调用工具诊断…" value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); void send() } }} /><IconButton aria-label="发送问题" color="primary" disabled={!question.trim() || busy} onClick={() => send()}><ArrowForwardRounded /></IconButton></div>
  </Drawer>
}

function EmptyProject({ project, onImport }: { project: Project; onImport: () => void }) {
  return <div className="empty-project"><div className="empty-orbit"><BiotechRounded /></div><span>EMPTY WORKSPACE</span><h1>{project.name}</h1><p>导入实验结果、配置和日志后，ExperimentLens 会识别 runs 并让你确认字段。</p><Button variant="contained" startIcon={<FileUploadRounded />} onClick={onImport}>导入实验文件</Button></div>
}

function LoadingScreen() { return <div className="loading-screen"><div className="brand-mark"><SearchRounded /></div><CircularProgress size={28} /><span>正在打开实验工作区…</span></div> }
function FatalError({ message, onRetry }: { message: string; onRetry: () => void }) { return <div className="loading-screen"><ErrorOutlineRounded color="error" /><strong>工作区暂时无法打开</strong><span>{message}</span><Button variant="contained" onClick={onRetry}>重试</Button></div> }

export default App
