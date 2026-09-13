import { CheckCircle2, XCircle, Info, Cpu, ChevronDown, ChevronUp, Clock } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useState } from 'react';
import type { DispatchResult, ModelInfo } from '../types';

interface TelemetryPanelProps {
  modelInfo: ModelInfo | null;
  latestDispatch: DispatchResult | null;
  dispatchLog: DispatchResult[];
}

export default function TelemetryPanel({ modelInfo, latestDispatch, dispatchLog }: TelemetryPanelProps) {
  const [logExpanded, setLogExpanded] = useState(false);

  return (
    <div className="flex flex-col gap-3">
      {/* ── Active Dispatch Result ─────────────────────────────── */}
      <AnimatePresence mode="wait">
        {latestDispatch && (
          <motion.div
            key={latestDispatch.request_id}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            transition={{ duration: 0.25 }}
            className="rounded-lg overflow-hidden"
            style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}
          >
            {/* Header */}
            <div
              className="px-3 py-2 flex items-center gap-2"
              style={{
                borderBottom: '1px solid var(--border-subtle)',
                background: latestDispatch.status === 'dispatched' ? 'rgba(16,185,129,0.08)' : 'rgba(239,68,68,0.08)',
              }}
            >
              {latestDispatch.status === 'dispatched' ? (
                <CheckCircle2 className="w-3.5 h-3.5" style={{ color: 'var(--accent)' }} />
              ) : (
                <XCircle className="w-3.5 h-3.5" style={{ color: '#ef4444' }} />
              )}
              <span
                className="text-[10px] font-black tracking-widest uppercase"
                style={{ color: latestDispatch.status === 'dispatched' ? 'var(--accent)' : '#ef4444' }}
              >
                {latestDispatch.status === 'dispatched' ? 'DISPATCH SUCCESSFUL' : 'TARGET UNREACHABLE'}
              </span>
            </div>

            {/* Content */}
            <div className="px-3 py-3">
              {latestDispatch.status === 'dispatched' && latestDispatch.risk_aware_route ? (
                <>
                  {/* Route comparison visual */}
                  <div className="flex flex-col gap-2 mb-3">
                    {/* Risk-aware */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="w-6 h-1 rounded-full" style={{ background: 'var(--route-risk)' }} />
                        <span className="text-[9px] font-bold tracking-wider uppercase" style={{ color: 'var(--text-muted)' }}>
                          Risk-Aware Route
                        </span>
                      </div>
                      <span className="font-bold font-mono text-[11px]" style={{ color: 'var(--accent)' }}>
                        {latestDispatch.risk_aware_route.total_cost.toFixed(2)}
                        <span className="text-[8px] ml-1" style={{ color: 'var(--text-muted)' }}>cost</span>
                      </span>
                    </div>

                    {/* Normal */}
                    {latestDispatch.normal_route && (
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div
                            className="w-6 h-px"
                            style={{ borderTop: '2px dashed var(--route-normal)' }}
                          />
                          <span className="text-[9px] font-bold tracking-wider uppercase" style={{ color: 'var(--text-muted)' }}>
                            Normal Route
                          </span>
                        </div>
                        <span className="font-mono text-[11px]" style={{ color: 'var(--text-secondary)' }}>
                          {latestDispatch.normal_route.total_distance_km.toFixed(2)}
                          <span className="text-[8px] ml-1" style={{ color: 'var(--text-muted)' }}>km</span>
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Divergence notice */}
                  {latestDispatch.routes_differ ? (
                    <div
                      className="rounded px-2.5 py-2 text-[10px]"
                      style={{ background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.25)', color: '#f59e0b' }}
                    >
                      <div className="font-bold mb-0.5">Route Diverged</div>
                      <div style={{ color: 'rgba(245,158,11,0.8)' }}>
                        ML-guided routing avoided predicted high-exposure road segments.
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center gap-1.5 text-[10px]" style={{ color: 'var(--text-muted)' }}>
                      <Info className="w-3 h-3" />
                      Shortest path has lowest exposure — routes matched.
                    </div>
                  )}
                </>
              ) : (
                <div className="text-[10px]" style={{ color: 'var(--text-secondary)' }}>
                  {latestDispatch.message || 'Target is unreachable from the rescue base. All paths blocked.'}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── ML Model Status ─────────────────────────────────────── */}
      <div
        className="rounded-lg overflow-hidden"
        style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}
      >
        <div className="px-3 py-2 flex items-center gap-2" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
          <Cpu className="w-3.5 h-3.5" style={{ color: 'var(--text-muted)' }} />
          <span className="text-[9px] font-black tracking-widest uppercase" style={{ color: 'var(--text-muted)' }}>
            Road Impact Predictor
          </span>
          {modelInfo && (
            <span
              className="ml-auto px-1.5 py-0.5 rounded text-[8px] font-bold"
              style={{ background: 'rgba(16,185,129,0.1)', color: 'var(--accent)', border: '1px solid rgba(16,185,129,0.25)' }}
            >
              ONLINE
            </span>
          )}
        </div>

        <div className="px-3 py-2.5 text-[10px]">
          {modelInfo ? (
            <div className="grid grid-cols-2 gap-y-2 gap-x-4">
              <span style={{ color: 'var(--text-muted)' }}>Engine</span>
              <span className="text-right font-medium truncate" style={{ color: 'var(--text-primary)' }}>
                {modelInfo.selected_model}
              </span>

              <span style={{ color: 'var(--text-muted)' }}>RMSE (engine)</span>
              <span className="text-right font-mono font-bold" style={{ color: 'var(--accent)' }}>
                {modelInfo.metrics[modelInfo.selected_model]?.mean_rmse?.toFixed(4) ?? 'N/A'}
              </span>

              <span style={{ color: 'var(--text-muted)' }}>RMSE (baseline)</span>
              <span className="text-right font-mono" style={{ color: 'var(--text-secondary)' }}>
                {(modelInfo.metrics['Dummy (Mean Baseline)'] ?? modelInfo.metrics['DummyRegressor'])?.mean_rmse?.toFixed(4) ?? 'N/A'}
              </span>

              <span style={{ color: 'var(--text-muted)' }}>Training samples</span>
              <span className="text-right font-mono" style={{ color: 'var(--text-secondary)' }}>
                {modelInfo.training_metadata?.dataset_statistics?.row_count?.toLocaleString() ?? 'N/A'}
              </span>
            </div>
          ) : (
            <div className="flex items-center gap-2" style={{ color: '#ef4444' }}>
              <XCircle className="w-3.5 h-3.5" />
              <span className="font-bold text-[9px] tracking-wider uppercase">Model Offline</span>
            </div>
          )}
          <div className="mt-2 text-[9px] leading-relaxed" style={{ color: 'var(--text-muted)' }}>
            Predicted road exposure is not confirmed damage.
          </div>
        </div>
      </div>

      {/* ── Operations Log ─────────────────────────────────────── */}
      <div
        className="rounded-lg overflow-hidden"
        style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}
      >
        <button
          onClick={() => setLogExpanded(x => !x)}
          className="w-full px-3 py-2 flex items-center justify-between transition-colors"
          style={{ borderBottom: logExpanded ? '1px solid var(--border-subtle)' : 'none' }}
        >
          <div className="flex items-center gap-2">
            <Clock className="w-3.5 h-3.5" style={{ color: 'var(--text-muted)' }} />
            <span className="text-[9px] font-black tracking-widest uppercase" style={{ color: 'var(--text-muted)' }}>
              Dispatch Log
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span
              className="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold"
              style={{ background: 'var(--bg-surface)', color: 'var(--text-secondary)', border: '1px solid var(--border-subtle)' }}
            >
              {dispatchLog.length}
            </span>
            {logExpanded ? (
              <ChevronUp className="w-3 h-3" style={{ color: 'var(--text-muted)' }} />
            ) : (
              <ChevronDown className="w-3 h-3" style={{ color: 'var(--text-muted)' }} />
            )}
          </div>
        </button>

        <AnimatePresence>
          {logExpanded && (
            <motion.div
              initial={{ height: 0 }}
              animate={{ height: 'auto' }}
              exit={{ height: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              <div className="overflow-y-auto custom-scrollbar" style={{ maxHeight: 200 }}>
                {dispatchLog.length === 0 ? (
                  <div className="px-3 py-4 text-center text-[9px] font-bold tracking-widest uppercase" style={{ color: 'var(--text-muted)' }}>
                    NO RECORDS
                  </div>
                ) : (
                  [...dispatchLog].reverse().map((log, idx) => (
                    <div
                      key={`${log.request_id}-${idx}`}
                      className="flex items-center px-3 py-2 gap-3"
                      style={{ borderBottom: '1px solid var(--border-subtle)' }}
                    >
                      {log.status === 'unreachable' ? (
                        <XCircle className="w-3 h-3 flex-shrink-0" style={{ color: '#ef4444' }} />
                      ) : (
                        <CheckCircle2 className="w-3 h-3 flex-shrink-0" style={{ color: 'var(--accent)' }} />
                      )}
                      <span className="font-mono text-[9px] flex-1 truncate" style={{ color: 'var(--text-secondary)' }}>
                        {log.target_node}
                      </span>
                      {log.status === 'dispatched' && log.risk_aware_route && (
                        <span className="font-mono text-[9px] font-bold" style={{ color: 'var(--accent)' }}>
                          {log.risk_aware_route.total_cost.toFixed(1)}
                        </span>
                      )}
                      {log.status === 'unreachable' && (
                        <span className="text-[9px] font-bold" style={{ color: '#ef4444' }}>FAIL</span>
                      )}
                    </div>
                  ))
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
