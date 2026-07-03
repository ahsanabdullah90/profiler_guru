'use client';

import React from 'react';

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  width?: string | number;
  height?: string | number;
  rounded?: 'sm' | 'md' | 'lg' | 'full';
  /** Pulse animation; disabled for `prefers-reduced-motion`. */
  pulse?: boolean;
}

const ROUND_CLASSES = {
  sm: 'rounded-sm',
  md: 'rounded-md',
  lg: 'rounded-lg',
  full: 'rounded-full',
} as const;

export default function Skeleton({
  width,
  height = 12,
  rounded = 'md',
  pulse = true,
  className = '',
  style,
  ...rest
}: SkeletonProps) {
  return (
    <div
      role="status"
      aria-label="Loading"
      className={`bg-[var(--bg-surface-raised)] ${ROUND_CLASSES[rounded]} ${
        pulse ? 'animate-pulse' : ''
      } ${className}`}
      style={{
        width: typeof width === 'number' ? `${width}px` : width,
        height: typeof height === 'number' ? `${height}px` : height,
        ...style,
      }}
      {...rest}
    />
  );
}

/** List of skeleton rows for the contacts list. */
export function ContactListSkeleton({ rows = 8 }: { rows?: number }) {
  // Deterministic width patterns (no Math.random — that would make the
  // output unstable across re-renders and trigger React's purity rule).
  const widths: Array<[string, string]> = [
    ['60%', '40%'],
    ['75%', '50%'],
    ['55%', '35%'],
    ['80%', '55%'],
    ['65%', '45%'],
  ];
  return (
    <div role="status" aria-label="Loading contacts" className="space-y-1.5">
      {Array.from({ length: rows }).map((_, i) => {
        const [w1, w2] = widths[i % widths.length];
        return (
          <div key={i} className="flex items-center gap-3 p-3">
            <Skeleton width={36} height={36} rounded="lg" />
            <div className="flex-1 space-y-1.5">
              <Skeleton width={w1} height={10} />
              <Skeleton width={w2} height={8} />
            </div>
            <Skeleton width={28} height={10} />
          </div>
        );
      })}
    </div>
  );
}

/** Skeleton for the message thread. */
export function MessageThreadSkeleton({ rows = 6 }: { rows?: number }) {
  // Deterministic width cycle to avoid Math.random (impure during render).
  const widths = ['55%', '70%', '60%', '75%', '65%', '50%'];
  return (
    <div role="status" aria-label="Loading messages" className="space-y-3 p-4">
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className={`flex ${i % 2 === 0 ? 'justify-start' : 'justify-end'}`}
        >
          <Skeleton
            width={widths[i % widths.length]}
            height={48}
            rounded="lg"
          />
        </div>
      ))}
    </div>
  );
}
