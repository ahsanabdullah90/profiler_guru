'use client';

import React from 'react';
import { MessageCircle, Globe } from 'lucide-react';

interface Props {
  platforms: string[];
  size?: 'sm' | 'xs';
}

const platformConfig: Record<string, { label: string; icon: React.ReactNode; color: string; bg: string }> = {
  instagram: {
    label: 'IG',
    icon: <Globe className="w-2.5 h-2.5" />,
    color: '#E1306C',
    bg: 'rgba(225, 48, 108, 0.12)',
  },
  whatsapp: {
    label: 'WA',
    icon: <MessageCircle className="w-2.5 h-2.5" />,
    color: '#25D366',
    bg: 'rgba(37, 211, 102, 0.12)',
  },
};

export default function PlatformBadge({ platforms, size = 'sm' }: Props) {
  if (!platforms || platforms.length === 0) return null;

  const isSm = size === 'sm';
  const cls = isSm
    ? 'inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-bold'
    : 'inline-flex items-center gap-0.5 px-1 py-0.5 rounded text-[8px] font-bold';

  return (
    <span className="inline-flex items-center gap-1">
      {platforms.map((p) => {
        const cfg = platformConfig[p];
        if (!cfg) return null;
        return (
          <span
            key={p}
            className={cls}
            style={{ background: cfg.bg, color: cfg.color }}
          >
            {cfg.icon}
            {isSm && cfg.label}
          </span>
        );
      })}
    </span>
  );
}
