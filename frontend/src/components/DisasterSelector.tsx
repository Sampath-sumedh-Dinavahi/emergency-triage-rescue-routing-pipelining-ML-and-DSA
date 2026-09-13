import { useState, useMemo } from 'react';
import { Search, Droplets, Wind, Flame, Triangle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import type { Disaster } from '../types';

interface DisasterSelectorProps {
  disasters: Disaster[];
  selected: Disaster | null;
  onSelect: (d: Disaster) => void;
  disabled: boolean;
}

const TYPE_CONFIG: Record<string, { label: string; Icon: React.FC<any>; color: string }> = {
  EQ: { label: 'Earthquake', Icon: Triangle, color: '#f59e0b' },
  FL: { label: 'Flood', Icon: Droplets, color: '#3b82f6' },
  TC: { label: 'Cyclone', Icon: Wind, color: '#8b5cf6' },
  WF: { label: 'Wildfire', Icon: Flame, color: '#ef4444' },
};

const ALERT_CONFIG: Record<string, { label: string; bg: string; text: string; dot: string }> = {
  Red: { label: 'RED', bg: 'rgba(239,68,68,0.12)', text: '#ef4444', dot: '#ef4444' },
  Orange: { label: 'ORG', bg: 'rgba(245,158,11,0.12)', text: '#f59e0b', dot: '#f59e0b' },
  Green: { label: 'GRN', bg: 'rgba(16,185,129,0.10)', text: '#10b981', dot: '#10b981' },
};

function timeAgo(dateStr: string): string {
  if (!dateStr) return '';
  try {
    const diff = Date.now() - new Date(dateStr).getTime();
    const hours = Math.floor(diff / 3600000);
    if (hours < 1) return 'Just now';
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  } catch {
    return '';
  }
}

export default function DisasterSelector({ disasters, selected, onSelect, disabled }: DisasterSelectorProps) {
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('ALL');

  const types = useMemo(() => {
    const seen = new Set<string>();
    disasters.forEach(d => seen.add(d.event_type));
    return ['ALL', ...Array.from(seen)];
  }, [disasters]);

  const filtered = useMemo(() => {
    return disasters.filter(d => {
      const matchType = typeFilter === 'ALL' || d.event_type === typeFilter;
      const q = search.toLowerCase();
      const matchSearch = !q || d.name?.toLowerCase().includes(q) || d.country?.toLowerCase().includes(q) || d.event_type?.toLowerCase().includes(q);
      return matchType && matchSearch;
    });
  }, [disasters, search, typeFilter]);

  return (
    <div className="flex flex-col gap-2 min-h-0">
      {/* Search */}
      <div className="relative">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 pointer-events-none" style={{ color: 'var(--text-muted)' }} />
        <input
          type="text"
          placeholder="Search events..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          disabled={disabled}
          className="w-full h-8 pl-8 pr-3 rounded text-xs outline-none disabled:opacity-40"
          style={{
            background: 'var(--bg-base)',
            border: '1px solid var(--border-default)',
            color: 'var(--text-primary)',
            fontFamily: 'inherit'
          }}
        />
      </div>

      {/* Type filter pills */}
      <div className="flex gap-1 flex-wrap">
        {types.map(t => {
          const cfg = TYPE_CONFIG[t];
          const isActive = typeFilter === t;
          return (
            <button
              key={t}
              onClick={() => setTypeFilter(t)}
              disabled={disabled}
              className="px-2 py-0.5 rounded text-[10px] font-bold tracking-wider transition-all disabled:opacity-40"
              style={{
                background: isActive ? (cfg?.color ? cfg.color + '22' : 'var(--accent-dim)') : 'transparent',
                border: `1px solid ${isActive ? (cfg?.color || 'var(--accent)') : 'var(--border-subtle)'}`,
                color: isActive ? (cfg?.color || 'var(--accent)') : 'var(--text-muted)',
              }}
            >
              {t === 'ALL' ? 'ALL' : (TYPE_CONFIG[t]?.label.slice(0, 2).toUpperCase() || t)}
            </button>
          );
        })}
      </div>

      {/* Event list */}
      <div className="flex flex-col gap-1 overflow-y-auto custom-scrollbar flex-grow min-h-0 pr-1" style={{ maxHeight: 280 }}>
        {disasters.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-6 gap-2">
            <div className="w-5 h-5 rounded-full border-2 border-t-transparent animate-spin" style={{ borderColor: 'var(--accent)', borderTopColor: 'transparent' }} />
            <span className="text-[10px] font-bold tracking-widest uppercase" style={{ color: 'var(--text-muted)' }}>
              CONNECTING TO GDACS...
            </span>
          </div>
        ) : filtered.length === 0 ? (
          <div className="py-6 text-center text-[10px] font-bold tracking-widest uppercase" style={{ color: 'var(--text-muted)' }}>
            NO MATCHING EVENTS
          </div>
        ) : (
          <AnimatePresence>
            {filtered.map((d, i) => {
              const isSelected = selected?.event_id === d.event_id && selected?.event_type === d.event_type;
              const alert = ALERT_CONFIG[d.alert_level] || ALERT_CONFIG.Green;
              const typeInfo = TYPE_CONFIG[d.event_type];
              const Icon = typeInfo?.Icon;

              return (
                <motion.button
                  key={`${d.event_type}-${d.event_id}`}
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.02, duration: 0.15 }}
                  onClick={() => !disabled && onSelect(d)}
                  disabled={disabled}
                  className="w-full text-left rounded px-3 py-2.5 transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                  style={{
                    background: isSelected ? 'var(--accent-dim)' : 'var(--bg-elevated)',
                    border: `1px solid ${isSelected ? 'var(--accent)' : 'var(--border-subtle)'}`,
                    outline: 'none',
                  }}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0 flex-1">
                      {Icon && (
                        <div className="flex-shrink-0 w-6 h-6 rounded flex items-center justify-center" style={{ background: (typeInfo?.color || '#64748b') + '20' }}>
                          <Icon className="w-3.5 h-3.5" style={{ color: typeInfo?.color || '#64748b' }} />
                        </div>
                      )}
                      <div className="min-w-0 flex-1">
                        <div className="text-[11px] font-semibold truncate leading-tight" style={{ color: isSelected ? 'var(--accent)' : 'var(--text-primary)' }}>
                          {d.name || `${d.event_type} Event`}
                        </div>
                        <div className="text-[10px] mt-0.5 truncate" style={{ color: 'var(--text-secondary)' }}>
                          {d.country} · {timeAgo(d.date)}
                        </div>
                      </div>
                    </div>
                    <div
                      className="flex-shrink-0 px-1.5 py-0.5 rounded text-[9px] font-black tracking-wider"
                      style={{ background: alert.bg, color: alert.text, border: `1px solid ${alert.text}40` }}
                    >
                      {alert.label}
                    </div>
                  </div>
                </motion.button>
              );
            })}
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}
