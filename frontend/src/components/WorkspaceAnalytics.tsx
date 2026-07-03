'use client';

/**
 * Workspace analytics panel — lazy-loaded when the user switches to the
 * Analytics tab. Keeps recharts (~150KB gz) off the initial load.
 */

import React, { useState } from 'react';
import { type Analytics } from '../store/api';
import { getApiBase } from '../store/api';
import {
  BarChart3, Calendar, Activity, Volume2, Download,
} from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from 'recharts';
import DataCard from './ui/DataCard';
import ChartFrame from './ui/ChartFrame';

export default function WorkspaceAnalytics({
  analytics,
  selectedContact,
}: {
  analytics: Analytics;
  selectedContact: string | null;
}) {
  const [exportFormat, setExportFormat] = useState<'csv' | 'json'>('csv');

  const handleExport = () => {
    if (!selectedContact) return;
    const url = `${getApiBase()}/contacts/${selectedContact}/export?format=${exportFormat}`;
    window.open(url, '_blank');
  };

  return (
    <div
      className="flex-1 overflow-y-auto p-5 space-y-5 font-sans"
      style={{ scrollbarWidth: 'thin' }}
    >
      {/* Connection Metrics Cards Grid */}
      <div className="grid grid-cols-3 gap-3">
        <DataCard
          label="Connection Status"
          value={
            <span
              className="text-base font-bold"
              style={{ color: analytics.depth_color }}
            >
              {analytics.depth_label}
            </span>
          }
        />
        <DataCard
          label="Weekly Daily Avg"
          value={analytics.avg_msg_weekly.toFixed(2)}
          icon={<BarChart3 className="w-3 h-3" />}
        />
        <DataCard
          label="Monthly Daily Avg"
          value={analytics.avg_msg_monthly.toFixed(2)}
          icon={<Calendar className="w-3 h-3" />}
        />
      </div>

      {/* 14-Day activity Recharts Line Chart */}
      {analytics.timeline.length > 0 ? (
        <ChartFrame
          title="14-Day Messaging Activity"
          subtitle="Daily message count for this contact"
          icon={
            <Activity
              className="w-3.5 h-3.5"
              style={{ color: 'var(--brand-primary)' }}
            />
          }
          dataTable={{
            headers: ['Date', 'Messages'],
            rows: analytics.timeline.map((t) => [t.date, t.messages]),
          }}
          chartClassName="h-44"
        >
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={analytics.timeline}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2A2A33" />
              <XAxis dataKey="date" stroke="#8A8A95" tick={{ fontSize: 10 }} />
              <YAxis stroke="#8A8A95" tick={{ fontSize: 10 }} />
              <Tooltip
                contentStyle={{
                  background: '#1C1C22',
                  borderColor: '#2A2A33',
                  borderRadius: '8px',
                  color: '#F5F5F7',
                  fontSize: '11px',
                }}
                labelStyle={{ color: '#B8B8C0' }}
              />
              <Line
                type="monotone"
                dataKey="messages"
                stroke="var(--brand-primary)"
                strokeWidth={2}
                dot={{ r: 3, fill: 'var(--brand-primary)', strokeWidth: 0 }}
                activeDot={{ r: 5 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </ChartFrame>
      ) : (
        <div
          className="p-6 rounded-lg text-center text-xs italic"
          style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-subtle)',
            color: 'var(--text-muted)',
          }}
        >
          No daily metrics activity recorded yet.
        </div>
      )}

      {/* Audio voice metrics */}
      <div
        className="p-4 rounded-lg"
        style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-subtle)',
        }}
      >
        <h3 className="text-xs font-bold text-[var(--text-primary)] mb-3 flex items-center gap-2">
          <Volume2 className="w-4 h-4" style={{ color: 'var(--warning)' }} />{' '}
          Voice Messaging Ratio
        </h3>
        <div className="flex items-center justify-between gap-10">
          <div className="flex flex-col">
            <span
              className="text-[10px]"
              style={{ color: 'var(--text-muted)' }}
            >
              Voice Clips Ingested:
            </span>
            <strong className="text-base font-bold text-[var(--text-primary)] mt-0.5 font-mono">
              {analytics.audio_count} clips
            </strong>
          </div>
          <div className="flex flex-col text-right">
            <span
              className="text-[10px]"
              style={{ color: 'var(--text-muted)' }}
            >
              Percentage of DMs:
            </span>
            <strong
              className="text-base font-bold mt-0.5 font-mono"
              style={{ color: 'var(--warning)' }}
            >
              {analytics.audio_ratio}%
            </strong>
          </div>
        </div>
        <div
          className="w-full h-1.5 rounded-full mt-3 overflow-hidden"
          style={{ background: 'var(--bg-surface-inset)' }}
        >
          <div
            className="h-full rounded-full"
            style={{
              background: 'var(--warning)',
              width: `${Math.min(100, analytics.audio_ratio)}%`,
            }}
          />
        </div>
      </div>

      {/* Export Panel */}
      <div
        className="p-4 rounded-lg flex flex-col gap-3"
        style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-subtle)',
        }}
      >
        <div>
          <h3 className="text-xs font-bold text-[var(--text-primary)] flex items-center gap-2">
            <Download
              className="w-4 h-4"
              style={{ color: 'var(--success)' }}
            />{' '}
            Export Metrics Data
          </h3>
          <p
            className="text-[10px] mt-1"
            style={{ color: 'var(--text-muted)' }}
          >
            Download the SQLite connection metrics in standard CSV or JSON
            format.
          </p>
        </div>
        <div className="flex items-center justify-between mt-1">
          <div
            className="flex p-0.5 rounded-lg"
            style={{
              background: 'var(--bg-surface-inset)',
              border: '1px solid var(--border-subtle)',
            }}
          >
            <button
              type="button"
              onClick={() => setExportFormat('csv')}
              className="px-3 py-1 rounded text-[10px] font-bold transition-colors"
              style={{
                background:
                  exportFormat === 'csv'
                    ? 'var(--brand-primary)'
                    : 'transparent',
                color:
                  exportFormat === 'csv'
                    ? 'white'
                    : 'var(--text-muted)',
              }}
            >
              CSV
            </button>
            <button
              type="button"
              onClick={() => setExportFormat('json')}
              className="px-3 py-1 rounded text-[10px] font-bold transition-colors"
              style={{
                background:
                  exportFormat === 'json'
                    ? 'var(--brand-primary)'
                    : 'transparent',
                color:
                  exportFormat === 'json'
                    ? 'white'
                    : 'var(--text-muted)',
              }}
            >
              JSON
            </button>
          </div>
          <button
            type="button"
            onClick={handleExport}
            className="px-4 py-1.5 text-black font-bold text-[10px] rounded-lg transition-colors flex items-center gap-1.5 cursor-pointer"
            style={{ background: 'var(--success)' }}
          >
            <Download className="w-3.5 h-3.5" /> Download Export
          </button>
        </div>
      </div>
    </div>
  );
}
