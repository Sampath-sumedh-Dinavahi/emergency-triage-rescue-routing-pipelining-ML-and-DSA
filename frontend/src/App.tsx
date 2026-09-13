import { useState, useEffect, useCallback } from 'react';
import { ShieldCheck, RefreshCw, Satellite, ChevronRight, ChevronLeft, Loader2, Map as MapIcon, Layers } from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';
import { api } from './api';
import type { AppState, Disaster, DispatchResult, ModelInfo } from './types';
import MapControl from './components/MapControl';
import QueuePanel from './components/QueuePanel';
import TelemetryPanel from './components/TelemetryPanel';
import DisasterSelector from './components/DisasterSelector';
import DisasterHeader from './components/DisasterHeader';
import BottomRouteBar from './components/BottomRouteBar';

// ─── Notification types ────────────────────────────────────────
interface Notification {
  id: string;
  type: 'error' | 'success' | 'info';
  message: string;
}

function useNotifications() {
  const [notes, setNotes] = useState<Notification[]>([]);
  const push = useCallback((type: Notification['type'], message: string) => {
    const id = Math.random().toString(36).slice(2);
    setNotes(n => [...n, { id, type, message }]);
    setTimeout(() => setNotes(n => n.filter(x => x.id !== id)), 4000);
  }, []);
  const remove = useCallback((id: string) => setNotes(n => n.filter(x => x.id !== id)), []);
  return { notes, push, remove };
}

export default function App() {
  const [disasters, setDisasters] = useState<Disaster[]>([]);
  const [selectedDisaster, setSelectedDisaster] = useState<Disaster | null>(null);
  const [appState, setAppState] = useState<AppState | null>(null);
  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);
  const [latestDispatch, setLatestDispatch] = useState<DispatchResult | null>(null);

  // Loading states
  const [loadingUplink, setLoadingUplink] = useState(false);
  const [loadingDispatch, setLoadingDispatch] = useState(false);

  // Sidebar state
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [rightPanelOpen, setRightPanelOpen] = useState(false);

  // Notifications
  const { notes, push, remove } = useNotifications();

  // ─── Initial data load ──────────────────────────────────────
  useEffect(() => {
    const load = async () => {
      try {
        const [disasterData, modelData] = await Promise.allSettled([
          api.getDisasters(),
          api.getModelInfo(),
        ]);
        if (disasterData.status === 'fulfilled') setDisasters(disasterData.value);
        else push('error', 'Failed to fetch GDACS events. Check network.');
        if (modelData.status === 'fulfilled') setModelInfo(modelData.value);
      } catch (e) {
        push('error', 'Startup failed. Check Flask server.');
      }
    };
    load();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const refreshState = useCallback(async (dispatchRes?: DispatchResult) => {
    try {
      const state = await api.getState();
      setAppState(state);
      if (dispatchRes !== undefined) setLatestDispatch(dispatchRes);
    } catch (e: any) {
      push('error', 'State sync failed: ' + e.message);
    }
  }, [push]);

  // ─── Load disaster ───────────────────────────────────────────
  const handleLoadDisaster = useCallback(async () => {
    if (!selectedDisaster) return;
    setLoadingUplink(true);
    try {
      await api.loadDisaster(selectedDisaster.event_type, selectedDisaster.event_id);
      await refreshState();
      setLatestDispatch(null);
      setRightPanelOpen(false);
      push('success', `${selectedDisaster.event_type} event loaded — road network ready.`);
    } catch (e: any) {
      push('error', 'Integration Error: ' + e.message);
    } finally {
      setLoadingUplink(false);
    }
  }, [selectedDisaster, refreshState, push]);

  // ─── Dispatch ────────────────────────────────────────────────
  const handleDispatch = useCallback(async () => {
    setLoadingDispatch(true);
    try {
      const result = await api.dispatchNext();
      await refreshState(result);
      setRightPanelOpen(true);
    } catch (e: any) {
      if (e.message?.includes('No pending')) {
        push('info', 'Emergency queue is empty.');
      } else {
        push('error', 'Dispatch failed: ' + e.message);
      }
    } finally {
      setLoadingDispatch(false);
    }
  }, [refreshState, push]);

  // ─── Reset ───────────────────────────────────────────────────
  const handleReset = useCallback(async () => {
    if (!window.confirm('Reset all operational state?')) return;
    try {
      await api.reset();
      setAppState(null);
      setLatestDispatch(null);
      setSelectedDisaster(null);
      setRightPanelOpen(false);
      push('info', 'System reset. Ready for new disaster.');
    } catch {
      push('error', 'Reset failed. Refresh the page.');
    }
  }, [push]);

  const eventActive = !!appState?.event;
  const SIDEBAR_W = sidebarCollapsed ? 44 : 300;

  return (
    <div
      className="relative w-screen h-screen overflow-hidden"
      style={{ background: 'var(--bg-base)', fontFamily: 'Inter, sans-serif' }}
    >
      {/* ══════════════ MAP (full bleed background) ══════════════ */}
      <div className="absolute inset-0" style={{ left: SIDEBAR_W, transition: 'left 0.3s ease' }}>
        <MapControl
          appState={appState}
          latestDispatch={latestDispatch}
          onStateChange={() => refreshState()}
        />
      </div>

      {/* ══════════════ TOP HEADER ════════════════════════════════ */}
      <header
        className="absolute top-0 right-0 z-40 flex items-center justify-between gap-4 px-4 h-11"
        style={{
          left: SIDEBAR_W,
          transition: 'left 0.3s ease',
          background: 'rgba(8,13,20,0.85)',
          backdropFilter: 'blur(12px)',
          borderBottom: '1px solid var(--border-subtle)',
        }}
      >
        {/* Left: App identity */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4" style={{ color: 'var(--accent)' }} />
            <h1 className="text-[11px] font-black tracking-widest uppercase" style={{ color: 'var(--text-primary)' }}>
              RESCUE COMMAND
            </h1>
          </div>
          <div className="w-px h-4" style={{ background: 'var(--border-default)' }} />
          <div className="flex items-center gap-1.5">
            <span
              className="relative flex h-1.5 w-1.5"
            >
              <span className="op-ping absolute inline-flex h-full w-full rounded-full" style={{ background: 'var(--accent)', opacity: 0.5 }} />
              <span className="relative inline-flex rounded-full h-1.5 w-1.5" style={{ background: 'var(--accent)' }} />
            </span>
            <span className="text-[9px] font-bold tracking-widest uppercase" style={{ color: 'var(--accent)' }}>ONLINE</span>
          </div>
        </div>

        {/* Center: Active disaster header */}
        <DisasterHeader disaster={selectedDisaster} appEventActive={eventActive} />

        {/* Right: Controls */}
        <div className="flex items-center gap-2 ml-auto">
          {/* Map/Layer indicator */}
          <div className="flex items-center gap-1.5 px-2 py-1 rounded" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)' }}>
            <MapIcon className="w-3 h-3" style={{ color: 'var(--text-muted)' }} />
            <span className="text-[9px]" style={{ color: 'var(--text-muted)' }}>OpenFreeMap</span>
          </div>

          {/* Right panel toggle (show after dispatch) */}
          {eventActive && (
            <button
              onClick={() => setRightPanelOpen(x => !x)}
              className="flex items-center gap-1.5 px-2 py-1 rounded text-[9px] font-bold tracking-wider uppercase transition-all"
              style={{
                background: rightPanelOpen ? 'var(--accent-dim)' : 'var(--bg-elevated)',
                border: `1px solid ${rightPanelOpen ? 'var(--accent)' : 'var(--border-subtle)'}`,
                color: rightPanelOpen ? 'var(--accent)' : 'var(--text-muted)',
              }}
            >
              <Layers className="w-3 h-3" />
              Analysis
            </button>
          )}

          <button
            onClick={handleReset}
            className="flex items-center gap-1.5 px-2 py-1 rounded text-[9px] font-bold tracking-wider uppercase transition-all"
            style={{
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border-subtle)',
              color: 'var(--text-muted)',
            }}
          >
            <RefreshCw className="w-3 h-3" />
            RESET
          </button>
        </div>
      </header>

      {/* ══════════════ LEFT SIDEBAR ══════════════════════════════ */}
      <aside
        className="absolute top-0 left-0 bottom-0 z-30 flex flex-col"
        style={{
          width: SIDEBAR_W,
          background: 'var(--bg-surface)',
          borderRight: '1px solid var(--border-subtle)',
          transition: 'width 0.3s ease',
        }}
      >
        {/* Sidebar header */}
        <div
          className="flex items-center justify-between px-3 h-11 flex-shrink-0"
          style={{ borderBottom: '1px solid var(--border-subtle)' }}
        >
          {!sidebarCollapsed && (
            <span className="text-[9px] font-black tracking-widest uppercase" style={{ color: 'var(--text-muted)' }}>
              OPERATIONS
            </span>
          )}
          <button
            onClick={() => setSidebarCollapsed(x => !x)}
            className="w-6 h-6 rounded flex items-center justify-center transition-colors ml-auto"
            style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)' }}
          >
            {sidebarCollapsed ? (
              <ChevronRight className="w-3 h-3" style={{ color: 'var(--text-muted)' }} />
            ) : (
              <ChevronLeft className="w-3 h-3" style={{ color: 'var(--text-muted)' }} />
            )}
          </button>
        </div>

        {/* Sidebar body */}
        <AnimatePresence>
          {!sidebarCollapsed && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              className="flex flex-col flex-1 overflow-hidden"
            >
              {/* ── DISASTER SELECTION ──────────────────────────── */}
              {!eventActive && (
                <div
                  className="flex flex-col gap-3 p-3 flex-shrink-0"
                  style={{ borderBottom: '1px solid var(--border-subtle)' }}
                >
                  <div className="flex items-center gap-2">
                    <Satellite className="w-3.5 h-3.5" style={{ color: 'var(--text-muted)' }} />
                    <span className="text-[9px] font-black tracking-widest uppercase" style={{ color: 'var(--text-muted)' }}>
                      GDACS EVENTS
                    </span>
                  </div>
                  <DisasterSelector
                    disasters={disasters}
                    selected={selectedDisaster}
                    onSelect={setSelectedDisaster}
                    disabled={eventActive || loadingUplink}
                  />
                  <button
                    onClick={handleLoadDisaster}
                    disabled={!selectedDisaster || loadingUplink || eventActive}
                    className="w-full flex items-center justify-center gap-2 py-2 rounded-lg font-black text-[10px] tracking-widest uppercase transition-all active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed"
                    style={{
                      background: selectedDisaster && !loadingUplink && !eventActive ? 'var(--accent)' : 'var(--bg-elevated)',
                      color: selectedDisaster && !loadingUplink && !eventActive ? 'white' : 'var(--text-muted)',
                      border: `1px solid ${selectedDisaster ? 'var(--accent)' : 'var(--border-default)'}`,
                      boxShadow: selectedDisaster ? '0 0 16px rgba(16,185,129,0.2)' : 'none',
                    }}
                  >
                    {loadingUplink ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        CONNECTING...
                      </>
                    ) : (
                      <>
                        <Satellite className="w-3.5 h-3.5" />
                        INITIATE UPLINK
                      </>
                    )}
                  </button>
                </div>
              )}

              {/* ── ACTIVE DISASTER INFO ────────────────────────── */}
              {eventActive && selectedDisaster && (
                <div
                  className="p-3 flex-shrink-0"
                  style={{ borderBottom: '1px solid var(--border-subtle)' }}
                >
                  <div className="rounded-lg p-2.5" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
                    <div className="text-[9px] font-black tracking-widest uppercase mb-1.5" style={{ color: 'var(--text-muted)' }}>
                      ACTIVE DISASTER
                    </div>
                    <div className="text-[11px] font-bold" style={{ color: 'var(--text-primary)' }}>
                      {selectedDisaster.name || `${selectedDisaster.event_type} Event`}
                    </div>
                    <div className="text-[10px] mt-0.5" style={{ color: 'var(--text-secondary)' }}>
                      {selectedDisaster.country} · {selectedDisaster.event_type}
                    </div>
                    <div className="flex items-center justify-between mt-2">
                      <span
                        className="text-[8px] font-black px-1.5 py-0.5 rounded tracking-wider"
                        style={{
                          background: selectedDisaster.alert_level === 'Red' ? 'rgba(239,68,68,0.15)'
                            : selectedDisaster.alert_level === 'Orange' ? 'rgba(245,158,11,0.15)'
                            : 'rgba(16,185,129,0.12)',
                          color: selectedDisaster.alert_level === 'Red' ? '#ef4444'
                            : selectedDisaster.alert_level === 'Orange' ? '#f59e0b'
                            : '#10b981',
                          border: `1px solid ${selectedDisaster.alert_level === 'Red' ? 'rgba(239,68,68,0.3)'
                            : selectedDisaster.alert_level === 'Orange' ? 'rgba(245,158,11,0.3)'
                            : 'rgba(16,185,129,0.25)'}`,
                        }}
                      >
                        {selectedDisaster.alert_level.toUpperCase()} ALERT
                      </span>
                      <span className="font-mono text-[8px]" style={{ color: 'var(--text-muted)' }}>
                        #{selectedDisaster.event_id}
                      </span>
                    </div>
                  </div>

                  {/* Road count */}
                  {appState && (
                    <div className="flex items-center justify-between mt-2 px-1">
                      <span className="text-[9px]" style={{ color: 'var(--text-muted)' }}>
                        Road segments
                      </span>
                      <span className="font-mono text-[9px]" style={{ color: 'var(--text-secondary)' }}>
                        {appState.edges.length.toLocaleString()}
                      </span>
                    </div>
                  )}

                  {/* ML risk legend */}
                  <div className="mt-2 flex items-center gap-1">
                    <span className="text-[8px] font-bold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
                      Exposure:
                    </span>
                    {[['#22c55e', 'Low'], ['#f59e0b', 'Med'], ['#ef4444', 'High']].map(([c, l]) => (
                      <div key={l} className="flex items-center gap-0.5 ml-1">
                        <div className="w-3 h-1 rounded-full" style={{ background: c }} />
                        <span className="text-[8px]" style={{ color: 'var(--text-muted)' }}>{l}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* ── EMERGENCY QUEUE ─────────────────────────────── */}
              {eventActive && appState && (
                <div className="flex-1 overflow-y-auto p-3 custom-scrollbar">
                  <QueuePanel
                    emergencies={appState.emergencies}
                    onDispatch={handleDispatch}
                  />
                  {loadingDispatch && (
                    <div className="mt-3 flex items-center justify-center gap-2 py-2">
                      <Loader2 className="w-4 h-4 animate-spin" style={{ color: 'var(--accent)' }} />
                      <span className="text-[9px] font-bold tracking-widest uppercase" style={{ color: 'var(--accent)' }}>
                        ROUTING...
                      </span>
                    </div>
                  )}
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </aside>

      {/* ══════════════ RIGHT ANALYSIS PANEL ═════════════════════ */}
      <AnimatePresence>
        {rightPanelOpen && eventActive && (
          <motion.aside
            key="right-panel"
            initial={{ x: 280, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 280, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="absolute top-11 right-0 bottom-0 z-30 overflow-y-auto custom-scrollbar p-3"
            style={{
              width: 280,
              background: 'rgba(13,21,32,0.95)',
              backdropFilter: 'blur(12px)',
              borderLeft: '1px solid var(--border-subtle)',
            }}
          >
            <TelemetryPanel
              modelInfo={modelInfo}
              latestDispatch={latestDispatch}
              dispatchLog={appState?.dispatch_log ?? []}
            />
          </motion.aside>
        )}
      </AnimatePresence>

      {/* ══════════════ BOTTOM ROUTE BAR ═════════════════════════ */}
      <BottomRouteBar dispatch={latestDispatch} />

      {/* ══════════════ NOTIFICATIONS ════════════════════════════ */}
      <div className="absolute top-14 right-4 z-50 flex flex-col gap-2 pointer-events-none" style={{ maxWidth: 320 }}>
        <AnimatePresence>
          {notes.map(note => (
            <motion.div
              key={note.id}
              initial={{ opacity: 0, x: 20, scale: 0.95 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 20, scale: 0.95 }}
              transition={{ duration: 0.2 }}
              className="rounded-lg px-3 py-2.5 shadow-2xl pointer-events-auto cursor-pointer"
              style={{
                background: 'var(--bg-elevated)',
                border: `1px solid ${
                  note.type === 'error' ? 'rgba(239,68,68,0.4)'
                  : note.type === 'success' ? 'rgba(16,185,129,0.4)'
                  : 'var(--border-default)'
                }`,
              }}
              onClick={() => remove(note.id)}
            >
              <p className="text-[11px] font-medium" style={{ color: 'var(--text-primary)' }}>
                {note.message}
              </p>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
