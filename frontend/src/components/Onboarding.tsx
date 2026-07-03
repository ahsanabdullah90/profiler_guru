'use client';

/**
 * First-run onboarding overlay. Skippable, dismissed-once via localStorage.
 * Shown automatically the first time the user authenticates successfully.
 */

import React, { useEffect } from 'react';
import { useUIStore } from '../store/uiStore';
import { Sparkles, Database, Brain, X, ArrowRight, Keyboard } from 'lucide-react';

export default function Onboarding() {
  const onboardingShown = useUIStore((s) => s.onboardingShown);
  const dismissOnboarding = useUIStore((s) => s.dismissOnboarding);
  const openShortcuts = useUIStore((s) => s.openShortcuts);

  // Escape closes
  useEffect(() => {
    if (!onboardingShown) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') dismissOnboarding();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onboardingShown, dismissOnboarding]);

  if (onboardingShown) return null;

  return (
    // eslint-disable-next-line jsx-a11y/no-noninteractive-element-interactions -- modal dialog backdrop with explicit Escape handling
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center p-4 font-sans"
      style={{ background: 'rgba(11, 11, 14, 0.82)', backdropFilter: 'blur(8px)' }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="onboarding-title"
      tabIndex={-1}
      onClick={(e) => {
        if (e.target === e.currentTarget) dismissOnboarding();
      }}
      onKeyDown={(e) => {
        if ((e.key === 'Enter' || e.key === ' ') && e.target === e.currentTarget) {
          dismissOnboarding();
        }
      }}
    >
      <div
        className="w-full max-w-2xl rounded-2xl shadow-2xl relative"
        style={{
          background: 'var(--bg-surface-raised)',
          border: '1px solid var(--border-subtle)',
          boxShadow: '0 24px 64px rgba(0, 0, 0, 0.6), 0 0 32px var(--brand-primary-glow)',
        }}
      >
        {/* Close */}
        <button
          type="button"
          onClick={dismissOnboarding}
          aria-label="Dismiss onboarding"
          className="absolute right-3 top-3 p-1 rounded-md hover:bg-[var(--bg-surface)] transition-colors focus-visible:outline-2 focus-visible:outline-[var(--brand-primary)] focus-visible:outline-offset-2"
          style={{ color: 'var(--text-muted)' }}
        >
          <X className="w-4 h-4" />
        </button>

        {/* Hero */}
        <header className="p-6 pb-3 flex items-center gap-4">
          <div
            className="w-12 h-12 rounded-xl flex items-center justify-center shadow-lg shrink-0"
            style={{
              background: 'var(--brand-primary)',
              boxShadow: '0 0 24px var(--brand-primary-glow)',
            }}
            aria-hidden="true"
          >
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2
              id="onboarding-title"
              className="text-base font-bold text-[var(--text-primary)]"
            >
              Welcome to Profile Guru
            </h2>
            <p className="text-[11px] text-[var(--text-muted)] mt-0.5">
              A quick tour of the three-pane workspace.
            </p>
          </div>
        </header>

        {/* Three columns */}
        <div className="px-6 pb-4 grid grid-cols-1 sm:grid-cols-3 gap-3">
          <FeatureCard
            icon={<Database className="w-4 h-4" style={{ color: 'var(--data-1)' }} />}
            label="Contacts"
            description="Browse every imported DM conversation. Click a contact to see messages and analytics."
          />
          <FeatureCard
            icon={<Brain className="w-4 h-4" style={{ color: 'var(--data-2)' }} />}
            label="AI Hub"
            description="Generate personality profiles and ask questions about any contact's DMs."
          />
          <FeatureCard
            icon={<Sparkles className="w-4 h-4" style={{ color: 'var(--brand-primary)' }} />}
            label="Inspector"
            description="The right rail. Add tags, write clinical notes, and star important contacts."
          />
        </div>

        {/* Shortcuts teaser */}
        <div
          className="mx-6 mb-4 p-3 rounded-lg flex items-center gap-3"
          style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-subtle)',
          }}
        >
          <Keyboard
            className="w-4 h-4 shrink-0"
            style={{ color: 'var(--brand-primary)' }}
            aria-hidden="true"
          />
          <p className="text-[11px] text-[var(--text-secondary)] flex-1 leading-relaxed">
            Power-user? Press{' '}
            <kbd
              className="px-1.5 py-0.5 rounded border font-mono"
              style={{
                background: 'var(--bg-surface-inset)',
                borderColor: 'var(--border-subtle)',
                color: 'var(--text-primary)',
              }}
            >
              ?
            </kbd>{' '}
            anytime to see every keyboard shortcut.
          </p>
          <button
            type="button"
            onClick={() => {
              dismissOnboarding();
              openShortcuts();
            }}
            className="text-[11px] font-semibold underline shrink-0"
            style={{ color: 'var(--brand-primary)' }}
          >
            Show me
          </button>
        </div>

        {/* Footer actions */}
        <footer
          className="px-6 py-4 flex items-center justify-between rounded-b-2xl"
          style={{
            background: 'var(--bg-surface)',
            borderTop: '1px solid var(--border-subtle)',
          }}
        >
          <p className="text-[10px] text-[var(--text-muted)]">
            You can always re-open this from the user menu.
          </p>
          <button
            type="button"
            onClick={dismissOnboarding}
            className="h-8 px-4 inline-flex items-center gap-1.5 text-xs font-semibold rounded-md text-white transition-colors focus-visible:outline-2 focus-visible:outline-[var(--brand-primary)] focus-visible:outline-offset-2"
            style={{ background: 'var(--brand-primary)' }}
          >
            Get started
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </footer>
      </div>
    </div>
  );
}

function FeatureCard({
  icon,
  label,
  description,
}: {
  icon: React.ReactNode;
  label: string;
  description: string;
}) {
  return (
    <div
      className="p-3 rounded-lg"
      style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-subtle)',
      }}
    >
      <div className="flex items-center gap-2 mb-1.5">
        <span
          className="w-6 h-6 rounded-md flex items-center justify-center"
          style={{ background: 'var(--bg-surface-inset)' }}
          aria-hidden="true"
        >
          {icon}
        </span>
        <span className="text-xs font-bold text-[var(--text-primary)]">{label}</span>
      </div>
      <p className="text-[10px] text-[var(--text-muted)] leading-relaxed">{description}</p>
    </div>
  );
}
