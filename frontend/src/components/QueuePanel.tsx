import { Send, AlertCircle, Users, Heart } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import type { Emergency } from '../types';

interface QueuePanelProps {
  emergencies: Emergency[];
  onDispatch: () => void;
}

const SEVERITY_LABEL = (s: number) => {
  if (s >= 4) return { label: 'CRITICAL', color: '#ef4444' };
  if (s >= 3) return { label: 'HIGH', color: '#f59e0b' };
  if (s >= 2) return { label: 'MODERATE', color: '#3b82f6' };
  return { label: 'LOW', color: '#64748b' };
};

export default function QueuePanel({ emergencies, onDispatch }: QueuePanelProps) {
  const top = emergencies[0];
  const rest = emergencies.slice(1);

  return (
    <div className="flex flex-col gap-3 min-h-0">
      {/* Section label */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <AlertCircle className="w-3.5 h-3.5" style={{ color: 'var(--text-muted)' }} />
          <span className="text-[10px] font-black tracking-widest uppercase" style={{ color: 'var(--text-secondary)' }}>
            Emergency Queue
          </span>
        </div>
        <span
          className="px-2 py-0.5 rounded text-[10px] font-bold font-mono"
          style={{
            background: emergencies.length > 0 ? 'rgba(239,68,68,0.12)' : 'var(--bg-elevated)',
            color: emergencies.length > 0 ? '#ef4444' : 'var(--text-muted)',
            border: `1px solid ${emergencies.length > 0 ? 'rgba(239,68,68,0.3)' : 'var(--border-subtle)'}`,
          }}
        >
          {emergencies.length}
        </span>
      </div>

      {emergencies.length === 0 ? (
        <div
          className="rounded-lg px-4 py-6 text-center"
          style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)' }}
        >
          <div className="text-[10px] font-bold tracking-widest uppercase" style={{ color: 'var(--text-muted)' }}>
            ALL UNITS ACCOUNTED FOR
          </div>
          <div className="text-[9px] mt-1" style={{ color: 'var(--text-muted)' }}>No pending emergencies</div>
        </div>
      ) : (
        <>
          {/* TOP PRIORITY CARD */}
          <AnimatePresence mode="wait">
            {top && (
              <motion.div
                key={top.request_id}
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 8 }}
                transition={{ duration: 0.2 }}
                className="rounded-lg overflow-hidden pulse-critical"
                style={{
                  background: 'rgba(239,68,68,0.07)',
                  border: '1px solid rgba(239,68,68,0.5)',
                }}
              >
                {/* Priority badge */}
                <div className="px-3 py-1.5 flex items-center justify-between" style={{ borderBottom: '1px solid rgba(239,68,68,0.2)', background: 'rgba(239,68,68,0.1)' }}>
                  <span className="text-[9px] font-black tracking-widest uppercase" style={{ color: '#ef4444' }}>
                    ▲ HIGHEST PRIORITY
                  </span>
                  <span className="font-bold font-mono text-[11px]" style={{ color: '#ef4444' }}>
                    {top.urgency_score.toFixed(1)}
                  </span>
                </div>

                {/* Metrics grid */}
                <div className="px-3 py-2.5 grid grid-cols-3 gap-2">
                  <div className="flex flex-col gap-0.5">
                    <div className="flex items-center gap-1">
                      <AlertCircle className="w-2.5 h-2.5" style={{ color: (() => { const s = SEVERITY_LABEL(top.severity); return s.color; })() }} />
                      <span className="text-[9px] font-bold tracking-wider uppercase" style={{ color: 'var(--text-muted)' }}>Sev</span>
                    </div>
                    <span className="text-[10px] font-bold" style={{ color: SEVERITY_LABEL(top.severity).color }}>
                      {SEVERITY_LABEL(top.severity).label}
                    </span>
                  </div>

                  <div className="flex flex-col gap-0.5">
                    <div className="flex items-center gap-1">
                      <Heart className="w-2.5 h-2.5" style={{ color: 'var(--text-muted)' }} />
                      <span className="text-[9px] font-bold tracking-wider uppercase" style={{ color: 'var(--text-muted)' }}>Med</span>
                    </div>
                    <span className="text-[10px] font-bold" style={{ color: 'var(--text-primary)' }}>
                      {top.medical_urgency}/5
                    </span>
                  </div>

                  <div className="flex flex-col gap-0.5">
                    <div className="flex items-center gap-1">
                      <Users className="w-2.5 h-2.5" style={{ color: 'var(--text-muted)' }} />
                      <span className="text-[9px] font-bold tracking-wider uppercase" style={{ color: 'var(--text-muted)' }}>Affected</span>
                    </div>
                    <span className="text-[10px] font-bold" style={{ color: 'var(--text-primary)' }}>
                      {top.affected_people}
                    </span>
                  </div>
                </div>

                <div className="px-3 pb-2">
                  <div className="text-[9px] font-mono truncate" style={{ color: 'var(--text-muted)' }}>
                    NODE {top.location_node}
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* DISPATCH BUTTON */}
          <button
            onClick={onDispatch}
            className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg font-black text-xs tracking-widest uppercase transition-all active:scale-95"
            style={{
              background: 'var(--accent)',
              color: 'white',
              boxShadow: '0 0 20px rgba(16,185,129,0.25)',
              border: '1px solid rgba(16,185,129,0.5)',
            }}
          >
            <Send className="w-3.5 h-3.5" />
            DISPATCH NEXT EMERGENCY
          </button>

          {/* REST OF QUEUE */}
          {rest.length > 0 && (
            <div className="flex flex-col gap-0 overflow-y-auto custom-scrollbar rounded-lg" style={{ border: '1px solid var(--border-subtle)', background: 'var(--bg-elevated)' }}>
              <div className="px-3 py-1.5" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                <span className="text-[9px] font-bold tracking-widest uppercase" style={{ color: 'var(--text-muted)' }}>
                  REMAINING QUEUE
                </span>
              </div>
              <div className="overflow-y-auto custom-scrollbar" style={{ maxHeight: 200 }}>
                <AnimatePresence>
                  {rest.map((em, idx) => (
                    <motion.div
                      key={em.request_id}
                      initial={{ opacity: 0, x: -6 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.15, delay: idx * 0.03 }}
                      className="flex items-center px-3 py-2 gap-3"
                      style={{ borderBottom: '1px solid var(--border-subtle)' }}
                    >
                      <span
                        className="w-5 h-5 rounded-full flex items-center justify-center text-[9px] font-black flex-shrink-0"
                        style={{ background: 'var(--bg-surface)', color: 'var(--text-secondary)', border: '1px solid var(--border-default)' }}
                      >
                        {idx + 2}
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <span className="font-bold font-mono text-[10px]" style={{ color: 'var(--text-secondary)' }}>
                            {em.urgency_score.toFixed(1)}
                          </span>
                          <span className="text-[9px]" style={{ color: 'var(--text-muted)' }}>
                            {em.affected_people} affected
                          </span>
                        </div>
                        <div className="font-mono text-[9px] truncate mt-0.5" style={{ color: 'var(--text-muted)' }}>
                          {em.location_node}
                        </div>
                      </div>
                      <div
                        className="text-[8px] font-black px-1 py-0.5 rounded"
                        style={{
                          background: SEVERITY_LABEL(em.severity).color + '20',
                          color: SEVERITY_LABEL(em.severity).color,
                        }}
                      >
                        {em.severity}
                      </div>
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
