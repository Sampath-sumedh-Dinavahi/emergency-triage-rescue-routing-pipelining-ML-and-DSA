import { Triangle, Droplets, Wind, Flame, AlertOctagon } from 'lucide-react';
import type { Disaster } from '../types';

interface DisasterHeaderProps {
  disaster: Disaster | null;
  appEventActive: boolean;
}

const TYPE_CONFIG: Record<string, { label: string; Icon: React.FC<any>; color: string }> = {
  EQ: { label: 'EARTHQUAKE', Icon: Triangle, color: '#f59e0b' },
  FL: { label: 'FLOOD', Icon: Droplets, color: '#3b82f6' },
  TC: { label: 'CYCLONE', Icon: Wind, color: '#8b5cf6' },
  WF: { label: 'WILDFIRE', Icon: Flame, color: '#ef4444' },
};

const ALERT_COLORS: Record<string, { text: string; bg: string }> = {
  Red: { text: '#ef4444', bg: 'rgba(239,68,68,0.14)' },
  Orange: { text: '#f59e0b', bg: 'rgba(245,158,11,0.14)' },
  Green: { text: '#10b981', bg: 'rgba(16,185,129,0.10)' },
};

export default function DisasterHeader({ disaster, appEventActive }: DisasterHeaderProps) {
  if (!disaster || !appEventActive) return null;

  const typeInfo = TYPE_CONFIG[disaster.event_type] || { label: disaster.event_type, Icon: AlertOctagon, color: '#64748b' };
  const alertColors = ALERT_COLORS[disaster.alert_level] || ALERT_COLORS.Green;
  const Icon = typeInfo.Icon;

  return (
    <div className="flex items-center gap-2 px-3 py-1 rounded" style={{ background: alertColors.bg, border: `1px solid ${alertColors.text}30` }}>
      {/* Alert badge */}
      <div className="flex items-center gap-1">
        <span className="text-[9px] font-black tracking-widest" style={{ color: alertColors.text }}>
          ● {disaster.alert_level.toUpperCase()}
        </span>
      </div>

      <div className="w-px h-3" style={{ background: 'var(--border-default)' }} />

      {/* Type icon + label */}
      <div className="flex items-center gap-1.5">
        <Icon className="w-3.5 h-3.5" style={{ color: typeInfo.color }} />
        <span className="text-[10px] font-bold tracking-wide" style={{ color: 'var(--text-primary)' }}>
          {typeInfo.label}
        </span>
      </div>

      <div className="w-px h-3" style={{ background: 'var(--border-default)' }} />

      {/* Country + name */}
      <span className="text-[10px] font-medium max-w-[200px] truncate" style={{ color: 'var(--text-secondary)' }}>
        {disaster.country}
        {disaster.name && disaster.name !== 'Unknown Event' ? ` · ${disaster.name}` : ''}
      </span>

      <div className="w-px h-3" style={{ background: 'var(--border-default)' }} />

      {/* Event ID */}
      <span className="text-[9px] font-mono" style={{ color: 'var(--text-muted)' }}>
        #{disaster.event_id}
      </span>
    </div>
  );
}
