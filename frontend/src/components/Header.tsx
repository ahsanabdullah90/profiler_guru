'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useAuthStore } from '../store/authStore';
import { useRagStore } from '../store/ragStore';
import { useContactsStore } from '../store/contactsStore';
import { useUIStore } from '../store/uiStore';
import { useNavigationStore } from '../store/navigationStore';
import { useStatusStore } from '../store/statusStore';
import {
  Home,
  Search,
  LogOut,
  Upload,
  Settings as SettingsIcon,
  Keyboard,
  Info,
  Sun,
  Moon,
  Cloud,
  Server,
} from 'lucide-react';

/** Memoized status pills — only re-renders when the cloud/local online booleans change. */
const StatusPills = React.memo(function StatusPills({
  cloudOnline,
  localOnline,
}: {
  cloudOnline: boolean | undefined;
  localOnline: boolean | undefined;
}) {
  return (
    <div
      className="hidden lg:flex items-center gap-1.5"
      aria-label="System status"
    >
      <span
        className={`h-6 px-2 inline-flex items-center gap-1.5 text-[10px] font-bold rounded-md border ${
          cloudOnline
            ? 'border-[var(--border-subtle)] text-[var(--text-secondary)]'
            : 'border-[var(--border-subtle)] text-[var(--text-muted)] opacity-60'
        }`}
        title={`Cloud: ${cloudOnline ? 'Online' : 'Offline'}`}
      >
        <Cloud className="w-3 h-3" />
        Cloud
        <span
          className={`w-1.5 h-1.5 rounded-full ${
            cloudOnline ? 'bg-[var(--success)]' : 'bg-[var(--text-muted)]'
          }`}
          aria-hidden="true"
        />
      </span>
      <span
        className={`h-6 px-2 inline-flex items-center gap-1.5 text-[10px] font-bold rounded-md border ${
          localOnline
            ? 'border-[var(--border-subtle)] text-[var(--text-secondary)]'
            : 'border-[var(--border-subtle)] text-[var(--text-muted)] opacity-60'
        }`}
        title={`Local: ${localOnline ? 'Online' : 'Offline'}`}
      >
        <Server className="w-3 h-3" />
        Local
        <span
          className={`w-1.5 h-1.5 rounded-full ${
            localOnline ? 'bg-[var(--success)]' : 'bg-[var(--text-muted)]'
          }`}
          aria-hidden="true"
        />
      </span>
    </div>
  );
});

export default function Header() {
  const setAuthenticated = useAuthStore((s) => s.setAuthenticated);
  const setGlobalSearchOpen = useRagStore((s) => s.setGlobalSearchOpen);
  const selectedContact = useContactsStore((s) => s.selectedContact);
  const setSelectedContact = useContactsStore((s) => s.setSelectedContact);
  const { theme, toggleTheme } = useUIStore();
  const setActiveSection = useNavigationStore((s) => s.setActiveSection);
  const status = useStatusStore((s) => s.status);

  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    if (menuOpen) {
      document.addEventListener('mousedown', handler);
      return () => document.removeEventListener('mousedown', handler);
    }
  }, [menuOpen]);

  const handleHome = () => {
    setActiveSection('home');
    setSelectedContact(null);
  };

  const cloudOnline = status.online_llm?.online;
  const localOnline = status.ollama?.online;

  return (
    <header
      className="h-[56px] w-full px-4 flex items-center justify-between border-b border-[var(--border-subtle)] bg-[var(--bg-surface-raised)] shrink-0 relative z-30"
      role="banner"
    >
      {/* Left: brand + Home + breadcrumb */}
      <div className="flex items-center gap-3 min-w-0">
        <div className="flex items-center gap-2 shrink-0">
          <div
            className="w-7 h-7 rounded-md flex items-center justify-center shadow-sm"
            style={{
              background:
                'linear-gradient(135deg, var(--brand-primary) 0%, var(--brand-primary-strong) 100%)',
            }}
            aria-hidden="true"
          >
            <span className="font-bold text-white text-[11px] tracking-wide">PG</span>
          </div>
          <span className="text-sm font-bold text-[var(--text-primary)] tracking-tight hidden sm:inline">
            Profile Guru
          </span>
        </div>

        <button
          type="button"
          onClick={handleHome}
          className="h-8 px-2.5 inline-flex items-center gap-1.5 text-xs font-semibold text-[var(--text-secondary)] hover:text-[var(--text-primary)] bg-transparent border border-[var(--border-subtle)] rounded-md hover:bg-[var(--bg-surface)] transition-colors focus-visible:outline-2 focus-visible:outline-[var(--brand-primary)] focus-visible:outline-offset-2"
          aria-label="Go to home"
        >
          <Home className="w-3.5 h-3.5" />
          Home
        </button>

        {/* Breadcrumb */}
        <nav
          aria-label="Breadcrumb"
          className="hidden md:flex items-center text-xs text-[var(--text-muted)] min-w-0"
        >
          <ol className="flex items-center gap-1.5 min-w-0">
            <li className="font-mono text-[var(--text-secondary)] shrink-0">PG</li>
            {selectedContact ? (
              <>
                <li aria-hidden="true" className="text-[var(--text-muted)]">›</li>
                <li className="truncate">
                  <span className="text-[var(--text-muted)]">Contacts</span>
                </li>
                <li aria-hidden="true" className="text-[var(--text-muted)]">›</li>
                <li className="text-[var(--text-primary)] font-semibold truncate max-w-[260px]">
                  {selectedContact}
                </li>
              </>
            ) : null}
          </ol>
        </nav>
      </div>

      {/* Right: status pills, search, user menu */}
      <div className="flex items-center gap-2 shrink-0">
        <StatusPills cloudOnline={cloudOnline} localOnline={localOnline} />

        <button
          type="button"
          onClick={() => setGlobalSearchOpen(true)}
          className="h-8 px-2.5 inline-flex items-center gap-2 text-[11px] font-semibold text-[var(--text-muted)] hover:text-[var(--text-primary)] bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-md hover:bg-[var(--bg-surface-inset)] transition-colors focus-visible:outline-2 focus-visible:outline-[var(--brand-primary)] focus-visible:outline-offset-2"
          aria-label="Open global search (Ctrl+K)"
          aria-keyshortcuts="Control+K"
        >
          <Search className="w-3.5 h-3.5" />
          <kbd className="font-mono text-[10px] text-[var(--text-muted)] px-1 py-0.5 rounded border border-[var(--border-subtle)] bg-[var(--bg-surface-inset)]">
            ⌘K
          </kbd>
        </button>

        {/* User menu */}
        <div className="relative" ref={menuRef}>
          <button
            type="button"
            onClick={() => setMenuOpen((v) => !v)}
            aria-haspopup="menu"
            aria-expanded={menuOpen}
            aria-label="User menu"
            className="h-8 w-8 inline-flex items-center justify-center text-[var(--text-secondary)] hover:text-[var(--text-primary)] bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-md hover:bg-[var(--bg-surface-inset)] transition-colors focus-visible:outline-2 focus-visible:outline-[var(--brand-primary)] focus-visible:outline-offset-2"
          >
            <div
              className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold text-white"
              style={{ background: 'var(--brand-primary)' }}
              aria-hidden="true"
            >
              U
            </div>
          </button>

          {menuOpen ? (
            <div
              role="menu"
              className="absolute right-0 top-[calc(100%+6px)] w-56 bg-[var(--bg-surface-raised)] border border-[var(--border-subtle)] rounded-lg shadow-2xl py-1 z-50"
            >
              <MenuItem
                icon={<Upload className="w-3.5 h-3.5" />}
                label="Import"
                onClick={() => {
                  setActiveSection('import');
                  setMenuOpen(false);
                }}
              />
              <MenuItem
                icon={<SettingsIcon className="w-3.5 h-3.5" />}
                label="Settings"
                onClick={() => {
                  setActiveSection('settings');
                  setMenuOpen(false);
                }}
              />

              <div className="my-1 border-t border-[var(--border-subtle)]" />

              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  toggleTheme();
                }}
                className="w-full px-3 py-1.5 flex items-center justify-between text-xs text-[var(--text-primary)] hover:bg-[var(--bg-surface)] transition-colors"
              >
                <span className="flex items-center gap-2 font-semibold">
                  {theme === 'dark' ? (
                    <Moon className="w-3.5 h-3.5" />
                  ) : (
                    <Sun className="w-3.5 h-3.5" />
                  )}
                  Theme
                </span>
                <span className="text-[10px] text-[var(--text-muted)] uppercase tracking-wider">
                  {theme}
                </span>
              </button>

              <MenuItem
                icon={<Keyboard className="w-3.5 h-3.5" />}
                label="Keyboard Shortcuts"
                onClick={() => {
                  useUIStore.getState().openShortcuts();
                  setMenuOpen(false);
                }}
              />
              <MenuItem
                icon={<Info className="w-3.5 h-3.5" />}
                label="Show Welcome Tour"
                onClick={() => {
                  useUIStore.setState({ onboardingShown: false });
                  setMenuOpen(false);
                }}
              />

              <div className="my-1 border-t border-[var(--border-subtle)]" />

              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setAuthenticated(false, null);
                  setMenuOpen(false);
                }}
                className="w-full px-3 py-1.5 flex items-center gap-2 text-xs text-[var(--error)] hover:bg-[var(--bg-surface)] transition-colors font-semibold"
              >
                <LogOut className="w-3.5 h-3.5" />
                Logout
              </button>
            </div>
          ) : null}
        </div>
      </div>
    </header>
  );
}

function MenuItem({
  icon,
  label,
  onClick,
  disabled = false,
}: {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      role="menuitem"
      onClick={onClick}
      disabled={disabled}
      className="w-full px-3 py-1.5 flex items-center gap-2 text-xs text-[var(--text-primary)] hover:bg-[var(--bg-surface)] transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-semibold"
    >
      {icon}
      {label}
    </button>
  );
}
