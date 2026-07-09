'use client';

import React, { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import { apiFetch } from '../store/api';
import { Crown, Lock } from 'lucide-react';

interface FeatureFlags {
  clinical_instruments: boolean;
  trait_frameworks: boolean;
  unlimited_patients: boolean;
  report_library: boolean;
  framework_expansion_packs: boolean;
  cloud_sync: boolean;
  whatsapp_import: boolean;
  audio_upload: boolean;
}

interface FeatureContextValue {
  tier: string;
  features: FeatureFlags;
  loading: boolean;
  isEnabled: (feature: string) => boolean;
}

const defaultFlags: FeatureFlags = {
  clinical_instruments: true,
  trait_frameworks: true,
  unlimited_patients: true,
  report_library: false,
  framework_expansion_packs: false,
  cloud_sync: false,
  whatsapp_import: true,
  audio_upload: true,
};

const FeatureContext = createContext<FeatureContextValue>({
  tier: 'Free',
  features: defaultFlags,
  loading: true,
  isEnabled: () => true,
});

export function FeatureProvider({ children }: { children: ReactNode }) {
  const [tier, setTier] = useState('Free');
  const [features, setFeatures] = useState<FeatureFlags>(defaultFlags);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    apiFetch<{ tier: string; features: FeatureFlags }>('/settings/features')
      .then((data) => {
        if (mounted) {
          setTier(data.tier);
          setFeatures(data.features);
        }
      })
      .catch(() => {})
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, []);

  const isEnabled = (feature: string): boolean => {
    return (features as unknown as Record<string, boolean>)[feature] !== false;
  };

  return (
    <FeatureContext.Provider value={{ tier, features, loading, isEnabled }}>
      {children}
    </FeatureContext.Provider>
  );
}

export function useFeatureGate() {
  return useContext(FeatureContext);
}

interface FeatureGateProps {
  feature: string;
  children: ReactNode;
  fallback?: ReactNode;
}

export default function FeatureGate({ feature, children, fallback }: FeatureGateProps) {
  const { tier, isEnabled } = useFeatureGate();

  if (isEnabled(feature)) {
    return <>{children}</>;
  }

  if (fallback) {
    return <>{fallback}</>;
  }

  return (
    <div className="relative group">
      <div className="opacity-40 pointer-events-none select-none">
        {children}
      </div>
      <div className="absolute inset-0 flex items-center justify-center">
        <div
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] font-bold"
          style={{ background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.3)', color: '#F59E0B' }}
        >
          <Crown className="w-3 h-3" />
          Pro Feature — Upgrade to unlock
        </div>
      </div>
    </div>
  );
}

export function TierBadge({ tier: overrideTier }: { tier?: string }) {
  const ctx = useContext(FeatureContext);
  const currentTier = overrideTier || ctx.tier;
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[9px] font-bold"
      style={{
        background: currentTier === 'Pro' ? 'rgba(245, 158, 11, 0.1)' : 'rgba(16, 185, 129, 0.1)',
        color: currentTier === 'Pro' ? '#F59E0B' : '#10B981',
      }}
    >
      {currentTier === 'Pro' ? <Crown className="w-2.5 h-2.5" /> : <Lock className="w-2.5 h-2.5" />}
      {currentTier}
    </span>
  );
}
