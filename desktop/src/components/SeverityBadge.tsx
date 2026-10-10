import React from 'react';

export default function SeverityBadge({ severity }: { severity: string }) {
  const colors: Record<string, string> = {
    CRITICAL: 'bg-red-500/20 text-red-400 border-red-500/50',
    HIGH: 'bg-orange-500/20 text-orange-400 border-orange-500/50',
    MEDIUM: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50',
    LOW: 'bg-blue-500/20 text-blue-400 border-blue-500/50',
  };
  return (
    <span className={`px-2 py-0.5 text-xs font-semibold rounded border ${colors[severity] || 'bg-slate-700 text-slate-300'}`}>
      {severity}
    </span>
  );
}
