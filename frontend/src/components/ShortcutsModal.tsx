'use client';

/**
 * Keyboard shortcuts cheat sheet. Opened by pressing `?` (Shift+/)
 * anywhere in the app, or from the onboarding overlay.
 */

import React, { useEffect } from 'react';
import { useUIStore } from '../store/uiStore';
import { X, Keyboard } from 'lucide-react';

interface Shortcut {
  keys: string[];
  description: string;
  group: string;
}

const SHORTCUTS: Shortcut[] = [
  // Global
  { group: 'Global', keys: ['⌘', 'K'], description: 'Open global search' },
  { group: 'Global', keys: ['Ctrl', 'I'], description: 'Toggle Inspector pane' },
  { group: 'Global', keys: ['?'], description: 'Show this cheat sheet' },
  { group: 'Global', keys: ['Esc'], description: 'Close modal / dismiss hint' },
  { group: 'Global', keys: ['Home'], description: 'Go to home view (clears selected contact)' },

  // Command palette
  { group: 'Command palette', keys: ['↵'], description: 'Open the highlighted result' },
  { group: 'Command palette', keys: ['Esc'], description: 'Close the palette' },
];

function isMac(): boolean {
  if (typeof navigator === 'undefined') return false;
  return /Mac|iPhone|iPad/.test(navigator.platform);
}

export default function ShortcutsModal() {
  const open = useUIStore((s) => s.shortcutsOpen);
  const close = useUIStore((s) => s.closeShortcuts);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      // Press ? (Shift+/) to open. Don't fire while typing in an input.
      const target = e.target as HTMLElement | null;
      const isTyping = target?.tagName === 'INPUT' || target?.tagName === 'TEXTAREA' || target?.isContentEditable;
      if (!open && e.key === '?' && !isTyping && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        useUIStore.getState().openShortcuts();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  if (!open) return null;

  const mac = isMac();
  const groups = Array.from(new Set(SHORTCUTS.map((s) => s.group)));

  return (
    // eslint-disable-next-line jsx-a11y/no-noninteractive-element-interactions -- modal dialog backdrop with Escape support
    <div
      className="fixed inset-0 z-[70] flex items-center justify-center p-4 font-sans"
      style={{ background: 'rgba(11, 11, 14, 0.78)', backdropFilter: 'blur(6px)' }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="shortcuts-title"
      tabIndex={-1}
      onClick={(e) => {
        if (e.target === e.currentTarget) close();
      }}
      onKeyDown={(e) => {
        if ((e.key === 'Enter' || e.key === ' ') && e.target === e.currentTarget) {
          close();
        }
      }}
    >
      <div
        className="w-full max-w-md rounded-2xl shadow-2xl relative"
        style={{
          background: 'var(--bg-surface-raised)',
          border: '1px solid var(--border-subtle)',
          boxShadow: '0 24px 64px rgba(0, 0, 0, 0.6)',
        }}
      >
        <header
          className="p-4 flex items-center gap-2.5 rounded-t-2xl"
          style={{ borderBottom: '1px solid var(--border-subtle)' }}
        >
          <Keyboard
            className="w-4 h-4"
            style={{ color: 'var(--brand-primary)' }}
            aria-hidden="true"
          />
          <h2
            id="shortcuts-title"
            className="text-sm font-bold text-[var(--text-primary)]"
          >
            Keyboard shortcuts
          </h2>
          <button
            type="button"
            onClick={close}
            aria-label="Close shortcuts"
            className="ml-auto p-1 rounded-md hover:bg-[var(--bg-surface)] transition-colors focus-visible:outline-2 focus-visible:outline-[var(--brand-primary)] focus-visible:outline-offset-2"
            style={{ color: 'var(--text-muted)' }}
          >
            <X className="w-4 h-4" />
          </button>
        </header>

        <div className="p-4 space-y-4 max-h-[60vh] overflow-y-auto">
          {groups.map((group) => (
            <section key={group}>
              <h3 className="text-[10px] uppercase tracking-wider text-[var(--text-muted)] font-bold mb-2">
                {group}
              </h3>
              <ul className="space-y-1.5">
                {SHORTCUTS.filter((s) => s.group === group).map((s, i) => (
                  <li
                    key={i}
                    className="flex items-center justify-between gap-2 py-1 text-xs"
                  >
                    <span className="text-[var(--text-secondary)]">{s.description}</span>
                    <span className="flex items-center gap-1 shrink-0">
                      {s.keys.map((k, j) => (
                        <React.Fragment key={j}>
                          <Kbd>{k}</Kbd>
                          {j < s.keys.length - 1 && (
                            <span style={{ color: 'var(--text-muted)' }}>+</span>
                          )}
                        </React.Fragment>
                      ))}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>

        <footer
          className="px-4 py-2.5 text-[10px] text-center rounded-b-2xl"
          style={{
            background: 'var(--bg-surface)',
            color: 'var(--text-muted)',
            borderTop: '1px solid var(--border-subtle)',
          }}
        >
          {mac ? 'macOS' : 'Windows / Linux'} · Press{' '}
          <Kbd inline>Esc</Kbd> to close
        </footer>
      </div>
    </div>
  );
}

function Kbd({ children, inline = false }: { children: React.ReactNode; inline?: boolean }) {
  return (
    <kbd
      className={
        inline
          ? 'px-1 py-0.5 rounded border font-mono text-[10px] inline-block'
          : 'px-1.5 py-0.5 rounded border font-mono text-[10px] inline-block min-w-[20px] text-center'
      }
      style={{
        background: 'var(--bg-surface-inset)',
        borderColor: 'var(--border-subtle)',
        color: 'var(--text-primary)',
      }}
    >
      {children}
    </kbd>
  );
}
