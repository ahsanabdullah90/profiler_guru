'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { apiFetch } from '../store/api';
import { useStatusStore } from '../store/statusStore';
import { ShieldCheck, ShieldAlert, Loader2 } from 'lucide-react';

const CONSENT_TYPES = ['chat_analysis', 'audio_recording', 'clinical_assessment'];
const CONSENT_LABELS: Record<string, string> = {
  chat_analysis: 'Deep Chat & Semantic Search',
  audio_recording: 'Session Audio Recording',
  clinical_assessment: 'Clinical Report Generation',
};

interface ConsentInfo {
  active: boolean;
  version: string;
  attested_at?: string;
}

interface Props {
  contactName: string;
}

export default function ConsentManager({ contactName }: Props) {
  const [consents, setConsents] = useState<Record<string, ConsentInfo>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<string | null>(null);
  const pushError = useStatusStore((s) => s.pushError);

  const fetchConsents = useCallback(async () => {
    setLoading(true);
    try {
      const consentData = await apiFetch<{ active: Record<string, unknown>[]; history: Record<string, unknown>[] }>(
        `/consent/${encodeURIComponent(contactName)}`
      );
      const consentMap: Record<string, ConsentInfo> = {};
      consentData.active.forEach((c) => {
        const ct = c.consent_type as string;
        consentMap[ct] = {
          active: true,
          version: c.consent_version as string,
          attested_at: c.attested_at as string,
        };
      });
      setConsents(consentMap);
    } catch (err) {
      console.error('Failed to load consents:', err);
      pushError('Failed to load patient consent records.', 'error');
    } finally {
      setLoading(false);
    }
  }, [contactName, pushError]);

  useEffect(() => {
    fetchConsents();
  }, [fetchConsents]);

  const handleConsentToggle = async (consentType: string) => {
    const current = consents[consentType];
    setSaving(consentType);
    try {
      if (current?.active) {
        // Revoke
        await apiFetch(`/consent/${encodeURIComponent(contactName)}/revoke`, {
          method: 'POST',
          body: JSON.stringify({ consent_type: consentType }),
        });
        setConsents((prev) => {
          const next = { ...prev };
          delete next[consentType];
          return next;
        });
        pushError(`${CONSENT_LABELS[consentType]}: Consent revoked successfully`, 'info');
      } else {
        // Attest
        const version = `v1.0-${new Date().toISOString().slice(0, 7)}`;
        await apiFetch(`/consent/${encodeURIComponent(contactName)}/attest`, {
          method: 'POST',
          body: JSON.stringify({
            consent_type: consentType,
            consent_version: version,
          }),
        });
        setConsents((prev) => ({
          ...prev,
          [consentType]: { active: true, version, attested_at: new Date().toISOString() },
        }));
        pushError(`${CONSENT_LABELS[consentType]}: Consent attested (${version})`, 'info');
      }
    } catch (err) {
      const e = err as Error;
      pushError(`Consent update failed: ${e.message}`, 'error');
    } finally {
      setSaving(null);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex justify-center items-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-[#007AFF]" />
        <span className="text-xs text-[var(--text-muted)] ml-2">Loading consent records...</span>
      </div>
    );
  }

  return (
    <div className="p-5 flex flex-col gap-4">
      <div className="space-y-1">
        <h3 className="text-sm font-bold text-[var(--text-primary)] flex items-center gap-1.5">
          <ShieldCheck className="w-4 h-4 text-[#007AFF]" /> HIPAA Consent & Attestation Manager
        </h3>
        <p className="text-[11px] text-[var(--text-muted)] leading-relaxed">
          Federal HIPAA regulations require practitioner attestation of patient written consent prior to activating clinical tools, semantic search, or session recording uploads.
        </p>
      </div>

      <div className="space-y-3 mt-2">
        {CONSENT_TYPES.map((ct) => {
          const consent = consents[ct];
          const isSaving = saving === ct;
          return (
            <div
              key={ct}
              className="flex items-center justify-between p-3.5 rounded-xl transition-all"
              style={{
                background: consent?.active ? 'rgba(16, 185, 129, 0.04)' : 'var(--bg-surface)',
                border: `1px solid ${consent?.active ? 'rgba(16, 185, 129, 0.15)' : 'var(--border-subtle)'}`,
              }}
            >
              <div className="flex flex-col gap-1 pr-4">
                <span className="font-bold text-xs text-[var(--text-primary)]">
                  {CONSENT_LABELS[ct]}
                </span>
                {consent?.active ? (
                  <span className="text-[10px] text-[var(--success)] flex items-center gap-1">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    Attested {consent.version} — {consent.attested_at ? new Date(consent.attested_at).toLocaleDateString() : ''}
                  </span>
                ) : (
                  <span className="text-[10px] text-[var(--text-muted)] flex items-center gap-1 italic">
                    <ShieldAlert className="w-3.5 h-3.5 text-[var(--text-muted)]" />
                    Not attested (Clinical gate active)
                  </span>
                )}
              </div>
              <button
                type="button"
                disabled={isSaving}
                onClick={() => handleConsentToggle(ct)}
                className={`px-4 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer disabled:opacity-50 ${
                  consent?.active
                    ? 'border border-[var(--error)]/30 bg-[var(--error)]/10 text-[var(--error)] hover:bg-[var(--error)]/20'
                    : 'bg-[#007AFF] text-white hover:bg-[#0066D6]'
                }`}
              >
                {isSaving && <Loader2 className="w-3 h-3 animate-spin" />}
                {consent?.active ? 'Revoke' : 'Attest'}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
