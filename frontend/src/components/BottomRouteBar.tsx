import { motion, AnimatePresence } from 'framer-motion';
import { Route, Shield, ChevronDown, ChevronUp, Info } from 'lucide-react';
import { useState } from 'react';
import type { DispatchResult } from '../types';

interface BottomRouteBarProps {
  dispatch: DispatchResult | null;
}

export default function BottomRouteBar({ dispatch }: BottomRouteBarProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <AnimatePresence>
      {dispatch?.status === 'dispatched' && (
        <motion.div
          key="route-bar"
          initial={{ y: 120, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 120, opacity: 0 }}
          transition={{ type: 'spring', stiffness: 280, damping: 30 }}
          className="absolute bottom-0 left-0 right-0 z-40 pointer-events-auto"
          style={{ paddingLeft: 300, paddingRight: 4 }}
        >
          <div
            className="rounded-t-xl overflow-hidden shadow-2xl"
            style={{
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border-default)',
              borderBottom: 'none',
            }}
          >
            {/* Compact summary bar */}
            <div className="flex items-center gap-0 px-5 h-12">
              {/* Dispatched label */}
              <div className="flex items-center gap-2 mr-6">
                <Shield className="w-4 h-4" style={{ color: 'var(--accent)' }} />
                <span className="text-[11px] font-black tracking-widest uppercase" style={{ color: 'var(--accent)' }}>
                  DISPATCHED
                </span>
              </div>

              <div className="w-px h-5 mr-6" style={{ background: 'var(--border-default)' }} />

              {/* Risk-aware route */}
              <div className="flex items-center gap-2 mr-6">
                <div className="w-8 h-1 rounded-full" style={{ background: 'var(--route-risk)' }} />
                <div>
                  <span className="text-[9px] font-bold tracking-wider uppercase" style={{ color: 'var(--text-muted)' }}>RISK-AWARE</span>
                  <span className="ml-2 text-[11px] font-bold font-mono" style={{ color: 'var(--accent)' }}>
                    {dispatch.risk_aware_route?.total_cost.toFixed(2)} cost
                  </span>
                </div>
              </div>

              <div className="w-px h-5 mr-6" style={{ background: 'var(--border-default)' }} />

              {/* Normal route */}
              <div className="flex items-center gap-2 mr-6">
                <div className="w-8 h-px rounded-full" style={{ background: 'var(--route-normal)', borderTop: '2px dashed var(--route-normal)', borderBottom: 'none', height: 2 }} />
                <div>
                  <span className="text-[9px] font-bold tracking-wider uppercase" style={{ color: 'var(--text-muted)' }}>NORMAL</span>
                  <span className="ml-2 text-[11px] font-mono" style={{ color: 'var(--text-secondary)' }}>
                    {dispatch.normal_route?.total_distance_km.toFixed(2)} km
                  </span>
                </div>
              </div>

              {dispatch.routes_differ && (
                <>
                  <div className="w-px h-5 mr-6" style={{ background: 'var(--border-default)' }} />
                  <div className="flex items-center gap-1.5">
                    <Route className="w-3.5 h-3.5" style={{ color: '#f59e0b' }} />
                    <span className="text-[10px] font-semibold" style={{ color: '#f59e0b' }}>
                      Route diverged — ML avoided high-exposure segments
                    </span>
                  </div>
                </>
              )}

              {!dispatch.routes_differ && (
                <>
                  <div className="w-px h-5 mr-6" style={{ background: 'var(--border-default)' }} />
                  <div className="flex items-center gap-1.5">
                    <Info className="w-3.5 h-3.5" style={{ color: 'var(--text-muted)' }} />
                    <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
                      Routes identical — shortest path is lowest exposure
                    </span>
                  </div>
                </>
              )}

              <div className="ml-auto">
                <button
                  onClick={() => setExpanded(x => !x)}
                  className="w-7 h-7 rounded flex items-center justify-center transition-colors"
                  style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}
                >
                  {expanded ? (
                    <ChevronDown className="w-3.5 h-3.5" style={{ color: 'var(--text-secondary)' }} />
                  ) : (
                    <ChevronUp className="w-3.5 h-3.5" style={{ color: 'var(--text-secondary)' }} />
                  )}
                </button>
              </div>
            </div>

            {/* Expanded detail */}
            <AnimatePresence>
              {expanded && (
                <motion.div
                  initial={{ height: 0 }}
                  animate={{ height: 'auto' }}
                  exit={{ height: 0 }}
                  transition={{ duration: 0.2 }}
                  className="overflow-hidden"
                >
                  <div className="px-5 pb-4 pt-2 grid grid-cols-4 gap-6 text-xs" style={{ borderTop: '1px solid var(--border-subtle)' }}>
                    <div>
                      <div className="text-[9px] font-bold tracking-widest uppercase mb-1" style={{ color: 'var(--text-muted)' }}>Target Node</div>
                      <div className="font-mono text-[11px] truncate" style={{ color: 'var(--text-primary)' }}>{dispatch.target_node}</div>
                    </div>
                    <div>
                      <div className="text-[9px] font-bold tracking-widest uppercase mb-1" style={{ color: 'var(--text-muted)' }}>Urgency Score</div>
                      <div className="font-bold font-mono text-[11px]" style={{ color: '#ef4444' }}>{dispatch.urgency_score.toFixed(2)}</div>
                    </div>
                    <div>
                      <div className="text-[9px] font-bold tracking-widest uppercase mb-1" style={{ color: 'var(--text-muted)' }}>Path Nodes</div>
                      <div className="font-mono text-[11px]" style={{ color: 'var(--text-secondary)' }}>
                        {dispatch.risk_aware_route?.path.length ?? 0} nodes
                      </div>
                    </div>
                    <div>
                      <div className="text-[9px] font-bold tracking-widest uppercase mb-1" style={{ color: 'var(--text-muted)' }}>Route Analysis</div>
                      <div className="text-[10px]" style={{ color: dispatch.routes_differ ? '#f59e0b' : 'var(--text-secondary)' }}>
                        {dispatch.routes_differ ? 'ML diverged' : 'Routes matched'}
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
