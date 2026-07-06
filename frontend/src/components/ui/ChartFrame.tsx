'use client';

import React, { useState } from 'react';
import { ChevronDown, Download, Table as TableIcon } from 'lucide-react';

interface ChartFrameProps {
  title: string;
  subtitle?: React.ReactNode;
  icon?: React.ReactNode;
  children: React.ReactNode;
  /** Optional data rows for the data-table fallback. */
  dataTable?: { headers: string[]; rows: (string | number)[][] } | null;
  /** Optional CSV export hook — called with the same rows. */
  onExportCsv?: () => void;
  /** Optional class for the inner chart area. */
  chartClassName?: string;
}

export default function ChartFrame({
  title,
  subtitle,
  icon,
  children,
  dataTable,
  onExportCsv,
  chartClassName = 'h-44',
}: ChartFrameProps) {
  const [showTable, setShowTable] = useState(false);

  const csv = dataTable && onExportCsv
    ? onExportCsv
    : dataTable
    ? () => {
        const lines = [
          dataTable.headers.join(','),
          ...dataTable.rows.map((r) =>
            r.map((c) => (typeof c === 'string' && c.includes(',') ? `"${c}"` : c)).join(','),
          ),
        ];
        const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${title.replace(/\s+/g, '_').toLowerCase()}.csv`;
        a.click();
        URL.revokeObjectURL(url);
      }
    : null;

  return (
    <div className="p-4 bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-lg">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2 min-w-0">
          {icon ? <span className="shrink-0">{icon}</span> : null}
          <div className="min-w-0">
            <h3 className="text-xs font-bold text-[var(--text-primary)]">{title}</h3>
            {subtitle ? (
              <p className="text-[10px] text-[var(--text-muted)] mt-0.5">{subtitle}</p>
            ) : null}
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          {dataTable ? (
            <button
              type="button"
              onClick={() => setShowTable((v) => !v)}
              aria-label={showTable ? 'Show chart' : 'Show data table'}
              aria-expanded={showTable}
              className="h-7 px-2 inline-flex items-center gap-1 text-[10px] font-bold text-[var(--text-secondary)] hover:text-[var(--text-primary)] bg-transparent border border-[var(--border-subtle)] rounded-md hover:bg-[var(--bg-surface-raised)] transition-colors"
            >
              <TableIcon className="w-3 h-3" />
              {showTable ? 'Chart' : 'Data'}
              <ChevronDown className="w-3 h-3" />
            </button>
          ) : null}
          {csv ? (
            <button
              type="button"
              onClick={csv}
              aria-label="Export CSV"
              className="h-7 px-2 inline-flex items-center gap-1 text-[10px] font-bold text-[var(--text-secondary)] hover:text-[var(--text-primary)] bg-transparent border border-[var(--border-subtle)] rounded-md hover:bg-[var(--bg-surface-raised)] transition-colors"
            >
              <Download className="w-3 h-3" />
              CSV
            </button>
          ) : null}
        </div>
      </div>

      {showTable && dataTable ? (
        <div className="max-h-60 overflow-auto border border-[var(--border-subtle)] rounded-md">
          <table className="w-full text-[10px] font-mono">
            <thead className="bg-[var(--bg-surface-raised)] sticky top-0">
              <tr>
                {dataTable.headers.map((h) => (
                  <th
                    key={h}
                    className="text-left px-2 py-1.5 text-[var(--text-muted)] font-bold uppercase tracking-wider"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {dataTable.rows.map((row, i) => (
                <tr key={i} className="border-t border-[var(--border-subtle)]">
                  {row.map((cell, j) => (
                    <td key={j} className="px-2 py-1 text-[var(--text-primary)]">
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className={`${chartClassName} w-full`}>{children}</div>
      )}
    </div>
  );
}
