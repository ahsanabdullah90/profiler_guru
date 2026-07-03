'use client';

import React from 'react';

interface DataCardProps {
  label: string;
  value: React.ReactNode;
  trend?: { direction: 'up' | 'down' | 'flat'; label: string } | null;
  footer?: React.ReactNode;
  icon?: React.ReactNode;
  className?: string;
}

export default function DataCard({
  label,
  value,
  trend,
  footer,
  icon,
  className = '',
}: DataCardProps) {
  return (
    <div
      className={`p-3 bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-lg flex flex-col justify-center min-h-[88px] ${className}`}
    >
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[9px] uppercase tracking-wider text-[var(--text-muted)] font-bold">
          {label}
        </span>
        {icon ? <span className="text-[var(--text-muted)]">{icon}</span> : null}
      </div>
      <strong className="text-base font-bold text-[var(--text-primary)] font-mono leading-tight">
        {value}
      </strong>
      {trend ? (
        <span
          className={`text-[10px] mt-1 font-semibold ${
            trend.direction === 'up'
              ? 'text-[var(--success)]'
              : trend.direction === 'down'
              ? 'text-[var(--error)]'
              : 'text-[var(--text-muted)]'
          }`}
        >
          {trend.direction === 'up' ? '▲' : trend.direction === 'down' ? '▼' : '■'}{' '}
          {trend.label}
        </span>
      ) : null}
      {footer ? (
        <div className="text-[10px] text-[var(--text-muted)] mt-1.5">{footer}</div>
      ) : null}
    </div>
  );
}
