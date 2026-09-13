import { StrictMode, Component } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import './index.css'

class ErrorBoundary extends Component<{ children: React.ReactNode }, { error: Error | null }> {
  state = { error: null };
  static getDerivedStateFromError(error: Error) { return { error }; }
  render() {
    if (this.state.error) {
      return (
        <div style={{ background: '#080d14', color: '#e2e8f0', minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', fontFamily: 'Inter, sans-serif', padding: 32 }}>
          <div style={{ color: '#ef4444', fontWeight: 900, fontSize: 12, letterSpacing: '0.15em', marginBottom: 12 }}>APPLICATION ERROR</div>
          <pre style={{ color: '#64748b', fontSize: 11, background: '#0d1520', padding: 16, borderRadius: 6, maxWidth: 600, overflowX: 'auto', border: '1px solid #1a2535' }}>
            {String((this.state.error as Error).message)}
          </pre>
          <button
            onClick={() => window.location.reload()}
            style={{ marginTop: 20, padding: '8px 20px', background: '#10b981', color: 'white', border: 'none', borderRadius: 6, fontWeight: 700, fontSize: 11, cursor: 'pointer', letterSpacing: '0.1em' }}
          >
            RELOAD APPLICATION
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
)
