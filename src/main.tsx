import React from 'react'
import ReactDOM from 'react-dom/client'
import { Provider } from 'react-redux'
import { CssBaseline, ThemeProvider, createTheme } from '@mui/material'
import { store } from './store'
import App from './App'
import './styles.css'

const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: '#59e3c2' },
    secondary: { main: '#f8c866' },
    background: { default: '#09111f', paper: '#111c2c' },
    error: { main: '#ff7c8d' },
    warning: { main: '#f8c866' },
  },
  typography: {
    fontFamily: 'Inter, "SF Pro Display", "PingFang SC", "Microsoft YaHei", sans-serif',
    h1: { fontSize: '2rem', fontWeight: 700, letterSpacing: '-0.035em' },
    h2: { fontSize: '1.25rem', fontWeight: 650, letterSpacing: '-0.02em' },
    button: { textTransform: 'none', fontWeight: 650 },
  },
  shape: { borderRadius: 10 },
  components: {
    MuiButton: { styleOverrides: { root: { minHeight: 40, boxShadow: 'none' } } },
    MuiPaper: { styleOverrides: { root: { backgroundImage: 'none' } } },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Provider store={store}>
      <ThemeProvider theme={theme}><CssBaseline /><App /></ThemeProvider>
    </Provider>
  </React.StrictMode>,
)
