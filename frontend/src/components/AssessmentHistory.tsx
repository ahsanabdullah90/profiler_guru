'use client';

import React, { useEffect, useState } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip as ReTooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { apiFetch, type AssessmentHistoryEntry } from '../store/api';
import { Loader2, History } from 'lucide-react';

const DIMENSION_COLORS = [
  '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899',
];

interface Props {
  contactName: string;
  frameworkId: string;
  dimensionLabels: Record<string, string>;
}

export default function AssessmentHistory({ contactName, frameworkId, dimensionLabels }: Props) {
  const [history, setHistory] = useState<AssessmentHistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    apiFetch<{ history: AssessmentHistoryEntry[] }>(
      `/rag/contacts/${encodeURIComponent(contactName)}/profile/history`
    )
      .then((data) => {
        if (mounted) setHistory(data.history || []);
      })
      .catch(() => {
        if (mounted) setHistory([]);
      })
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [contactName]);

  // Only show entries that have scores
  const scored = history.filter((h) => h.scores && Object.keys(h.scores).length > 0);

  // Build chart data: one point per assessment date, with a key per dimension
  const chartData = scored.map((h) => {
    const point: Record<string, string | number> = {
      date: typeof h.generated_at === 'string' ? h.generated_at.slice(0, 10) : '',
    };
    if (h.scores) {
      for (const [dim, val] of Object.entries(h.scores)) {
        point[dim] = val;
      }
    }
    return point;
  });

  // Determine which dimensions appear across all data points
  const allDims = new Set<string>();
  for (const point of chartData) {
    for (const key of Object.keys(point)) {
      if (key !== 'date') allDims.add(key);
    }
  }
  const dims = allDims.size > 0 ? [...allDims] : Object.keys(dimensionLabels);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <History className="w-3.5 h-3.5" style={{ color: 'var(--text-muted)' }} />
        <span className="text-[10px] font-bold uppercase" style={{ color: 'var(--text-muted)' }}>Assessment History</span>
        <span className="text-[9px]" style={{ color: 'var(--text-muted)' }}>({history.length} total)</span>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-6">
          <Loader2 className="w-4 h-4 animate-spin" style={{ color: 'var(--brand-primary)' }} />
        </div>
      ) : chartData.length >= 2 ? (
        /* Score trajectory chart when there are 2+ scored assessments */
        <div className="p-3 rounded-lg" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
          <div style={{ height: 180 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
                <XAxis dataKey="date" tick={{ fontSize: 8, fill: 'var(--text-muted)' }} />
                <YAxis domain={[0, 10]} tick={{ fontSize: 8, fill: 'var(--text-muted)' }} />
                <ReTooltip
                  contentStyle={{
                    background: 'var(--bg-surface-raised)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '6px',
                    fontSize: '10px',
                    color: 'var(--text-primary)',
                  }}
                />
                <Legend wrapperStyle={{ fontSize: '8px', color: 'var(--text-muted)' }} />
                {dims.slice(0, 6).map((dim, i) => (
                  <Line
                    key={dim}
                    type="monotone"
                    dataKey={dim}
                    name={dimensionLabels[dim] || dim}
                    stroke={DIMENSION_COLORS[i % DIMENSION_COLORS.length]}
                    strokeWidth={1.5}
                    dot={{ r: 2 }}
                    connectNulls
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      ) : chartData.length === 1 ? (
        <div className="p-3 rounded-lg text-[10px] italic text-center" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', color: 'var(--text-muted)' }}>
          One assessment completed. Generate another to see score trajectories.
        </div>
      ) : (
        <div className="p-3 rounded-lg text-[10px] italic text-center" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', color: 'var(--text-muted)' }}>
          No assessment history yet.
        </div>
      )}

      {/* Simple list of past assessments */}
      {history.length > 0 ? (
        <div className="max-h-40 overflow-y-auto space-y-1" style={{ scrollbarWidth: 'thin' }}>
          {history.map((h) => (
            <div
              key={h.history_id}
              className="flex items-center justify-between px-2 py-1.5 rounded text-[9px]"
              style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}
            >
              <div className="flex items-center gap-2">
                <span className="font-bold" style={{ color: 'var(--text-secondary)' }}>
                  {h.framework_id.replace(/_/g, ' ')}
                </span>
                <span className="font-mono" style={{ color: 'var(--text-muted)' }}>
                  {h.generated_at.slice(0, 10)}
                </span>
                {h.framework_version && (
                  <span className="text-[7px] font-mono px-1 py-0.5 rounded border select-none opacity-80" style={{ background: 'var(--bg-surface-inset)', borderColor: 'var(--border-subtle)', color: 'var(--text-muted)' }}>
                    v:{h.framework_version}
                  </span>
                )}
              </div>
              <span className="text-[8px]" style={{ color: 'var(--text-muted)' }}>
                {h.model_name || h.pipeline_mode}
              </span>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
