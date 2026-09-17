import { configureStore, createAsyncThunk, createSlice, type PayloadAction } from '@reduxjs/toolkit'
import { api } from './api'
import type { Analysis, Project, RunRow } from './types'

interface AppState {
  projects: Project[]
  currentProject: Project | null
  analysis: Analysis | null
  runs: RunRow[]
  status: 'idle' | 'loading' | 'ready' | 'error'
  error: string | null
}

const initialState: AppState = { projects: [], currentProject: null, analysis: null, runs: [], status: 'idle', error: null }

export const bootstrap = createAsyncThunk('app/bootstrap', async () => {
  let projects = await api.listProjects()
  if (!projects.length) projects = [await api.createDemo()]
  const currentProject = projects[0]
  const [analysis, runs] = await Promise.all([api.getAnalysis(currentProject.id), api.getRuns(currentProject.id)])
  return { projects, currentProject, analysis, runs }
})

export const selectProject = createAsyncThunk('app/selectProject', async (project: Project) => {
  const [fresh, analysis, runs] = await Promise.all([api.getProject(project.id), api.getAnalysis(project.id), api.getRuns(project.id)])
  return { project: fresh, analysis, runs }
})

export const refreshProject = createAsyncThunk('app/refreshProject', async (id: string) => {
  const [project, analysis, runs, projects] = await Promise.all([api.getProject(id), api.getAnalysis(id), api.getRuns(id), api.listProjects()])
  return { project, analysis, runs, projects }
})

const appSlice = createSlice({
  name: 'app',
  initialState,
  reducers: {
    clearError(state) { state.error = null },
    addProject(state, action: PayloadAction<Project>) {
      state.projects.unshift(action.payload)
      state.currentProject = action.payload
      state.analysis = null
      state.runs = []
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(bootstrap.pending, (state) => { state.status = 'loading'; state.error = null })
      .addCase(bootstrap.fulfilled, (state, action) => { Object.assign(state, action.payload, { status: 'ready' }) })
      .addCase(bootstrap.rejected, (state, action) => { state.status = 'error'; state.error = action.error.message || '加载失败' })
      .addCase(selectProject.pending, (state) => { state.status = 'loading'; state.error = null })
      .addCase(selectProject.fulfilled, (state, action) => { state.currentProject = action.payload.project; state.analysis = action.payload.analysis; state.runs = action.payload.runs; state.status = 'ready' })
      .addCase(selectProject.rejected, (state, action) => { state.status = 'error'; state.error = action.error.message || '加载失败' })
      .addCase(refreshProject.fulfilled, (state, action) => { state.currentProject = action.payload.project; state.analysis = action.payload.analysis; state.runs = action.payload.runs; state.projects = action.payload.projects; state.status = 'ready' })
  },
})

export const { addProject, clearError } = appSlice.actions
export const store = configureStore({ reducer: { app: appSlice.reducer } })
export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch
