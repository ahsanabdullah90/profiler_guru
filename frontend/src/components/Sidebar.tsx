'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useAuthStore } from '../store/authStore';
import { useRagStore } from '../store/ragStore';
import { useContactsStore } from '../store/contactsStore';
import { useNavigationStore } from '../store/navigationStore';
import { useUIStore } from '../store/uiStore';
import { useStatusStore } from '../store/statusStore';
import {
  Home,
  Search,
  Upload,
  Settings as SettingsIcon,
  Keyboard,
  Info,
  Sun,
  Moon,
  LogOut,
  BookOpen,
  Users,
} from 'lucide-react';

/**
 * Persistent left-side icon rail (64px wide).
 * Contains all application navigation, status indicators, and utility actions.
 */
export default function Sidebar() {
  const setAuthenticated = useAuthStore((s) => s.setAuthenticated);
  const setGlobalSearchOpen = useRagStore((s) => s.setGlobalSearchOpen);
  const setSelectedContact = useContactsStore((s) => s.setSelectedContact);
  const { activeSection, setActiveSection } = useNavigationStore();
  const { theme, toggleTheme } = useUIStore();
  const cloudOnline = useStatusStore((s) => s.status.online_llm?.online ?? false);
  const localOnline = useStatusStore((s) => s.status.ollama?.online ?? false);

  const [tooltip, setTooltip] = useState<string | null>(null);
  const tooltipTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  const showTooltip = (label: string) => {
    if (tooltipTimeout.current) clearTimeout(tooltipTimeout.current);
    setTooltip(label);
  };

  const hideTooltip = () => {
    tooltipTimeout.current = setTimeout(() => setTooltip(null), 150);
  };

  useEffect(() => {
    return () => {
      if (tooltipTimeout.current) clearTimeout(tooltipTimeout.current);
    };
  }, []);

  const handleHome = () => {
    setActiveSection('home');
    setSelectedContact(null);
  };

  const handleSearch = () => {
    setGlobalSearchOpen(true);
  };

  const handleImport = () => {
    setActiveSection('import');
  };

  const handleSettings = () => {
    setActiveSection('settings');
  };

  const handleShortcuts = () => {
    useUIStore.getState().openShortcuts();
  };

  const handleWelcomeTour = () => {
    useUIStore.setState({ onboardingShown: false });
  };

  return (
    <nav
      className="w-16 h-full flex flex-col items-center py-3 bg-[var(--bg-surface-raised)] border-r border-[var(--border-subtle)] shrink-0 z-20"
      aria-label="Primary navigation"
    >
      {/* Brand */}
      <div
        className="w-8 h-8 rounded-lg flex items-center justify-center shadow-sm mb-4 shrink-0"
        style={{
          background:
            'linear-gradient(135deg, var(--brand-primary) 0%, var(--brand-primary-strong) 100%)',
        }}
        aria-hidden="true"
      >
        <span className="font-bold text-white text-[10px] tracking-wide">PG</span>
      </div>

      {/* Primary nav */}
      <div className="flex flex-col items-center gap-1 shrink-0">
        <NavButton
          icon={<Home className="w-4 h-4" />}
          label="Home"
          active={activeSection === 'home'}
          onClick={handleHome}
          onMouseEnter={() => showTooltip('Home')}
          onMouseLeave={hideTooltip}
        />
        <NavButton
          icon={<Users className="w-4 h-4" />}
          label="Clients"
          active={activeSection === 'clients'}
          onClick={() => setActiveSection('clients')}
          onMouseEnter={() => showTooltip('Clients')}
          onMouseLeave={hideTooltip}
        />
        <NavButton
          icon={<Search className="w-4 h-4" />}
          label="Search"
          onClick={handleSearch}
          onMouseEnter={() => showTooltip('Search (⌘K)')}
          onMouseLeave={hideTooltip}
        />
        <NavButton
          icon={<Upload className="w-4 h-4" />}
          label="Data Sources"
          active={activeSection === 'import'}
          onClick={handleImport}
          onMouseEnter={() => showTooltip('Data Sources')}
          onMouseLeave={hideTooltip}
        />
        <NavButton
          icon={<SettingsIcon className="w-4 h-4" />}
          label="Settings"
          active={activeSection === 'settings'}
          onClick={handleSettings}
          onMouseEnter={() => showTooltip('Settings')}
          onMouseLeave={hideTooltip}
        />
        <NavButton
          icon={<BookOpen className="w-4 h-4" />}
          label="Knowledge"
          active={activeSection === 'knowledge'}
          onClick={() => setActiveSection('knowledge')}
          onMouseEnter={() => showTooltip('Knowledge Base')}
          onMouseLeave={hideTooltip}
        />
      </div>

      {/* Spacer */}
      <div className="flex-1" aria-hidden="true" />

      {/* Status & utilities */}
      <div className="flex flex-col items-center gap-1 shrink-0">
        <NavButton
          icon={theme === 'dark' ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
          label="Theme"
          onClick={toggleTheme}
          onMouseEnter={() => showTooltip(`Theme: ${theme}`)}
          onMouseLeave={hideTooltip}
        />

        {/* Status indicators */}
        <div className="flex flex-col items-center gap-0.5 my-1">
          <StatusDot online={cloudOnline} label="Cloud" onMouseEnter={() => showTooltip(`Cloud: ${cloudOnline ? 'Online' : 'Offline'}`)} onMouseLeave={hideTooltip} />
          <StatusDot online={localOnline} label="Local" onMouseEnter={() => showTooltip(`Local: ${localOnline ? 'Online' : 'Offline'}`)} onMouseLeave={hideTooltip} />
        </div>

        <NavButton
          icon={<Keyboard className="w-4 h-4" />}
          label="Shortcuts"
          onClick={handleShortcuts}
          onMouseEnter={() => showTooltip('Keyboard Shortcuts (?)')}
          onMouseLeave={hideTooltip}
        />
        <NavButton
          icon={<Info className="w-4 h-4" />}
          label="Tour"
          onClick={handleWelcomeTour}
          onMouseEnter={() => showTooltip('Show Welcome Tour')}
          onMouseLeave={hideTooltip}
        />

        <div className="w-8 h-px bg-[var(--border-subtle)] my-1" aria-hidden="true" />

        <NavButton
          icon={<LogOut className="w-4 h-4" />}
          label="Logout"
          onClick={() => setAuthenticated(false, null)}
          onMouseEnter={() => showTooltip('Logout')}
          onMouseLeave={hideTooltip}
          danger
        />
      </div>

      {/* Tooltip */}
      {tooltip ? (
        <div
          role="tooltip"
          aria-hidden="true"
          className="fixed left-[72px] z-50 px-2 py-1 rounded-md text-[10px] font-semibold whitespace-nowrap shadow-lg pointer-events-none"
          style={{
            background: 'var(--bg-surface-raised)',
            border: '1px solid var(--border-subtle)',
            color: 'var(--text-primary)',
            top: '50%',
            transform: 'translateY(-50%)',
          }}
        >
          {tooltip}
        </div>
      ) : null}
    </nav>
  );
}

function NavButton({
  icon,
  label,
  active = false,
  danger = false,
  onClick,
  onMouseEnter,
  onMouseLeave,
}: {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
  danger?: boolean;
  onClick: () => void;
  onMouseEnter?: () => void;
  onMouseLeave?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      title={label}
      aria-label={label}
      className={`w-10 h-10 rounded-lg flex items-center justify-center transition-colors focus-visible:outline-2 focus-visible:outline-[var(--brand-primary)] focus-visible:outline-offset-2 ${
        danger
          ? 'text-[var(--text-secondary)] hover:text-[var(--error)] hover:bg-[rgba(255,90,95,0.08)]'
          : active
            ? 'text-[var(--brand-primary)] bg-[var(--brand-primary-soft)]'
            : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface)]'
      }`}
    >
      {icon}
    </button>
  );
}

function StatusDot({
  online,
  label,
  onMouseEnter,
  onMouseLeave,
}: {
  online: boolean | undefined;
  label: string;
  onMouseEnter?: () => void;
  onMouseLeave?: () => void;
}) {
  return (
    // eslint-disable-next-line jsx-a11y/no-static-element-interactions -- status dot with tooltip, not interactive
    <div
      className="flex items-center justify-center"
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      title={`${label}: ${online ? 'Online' : 'Offline'}`}
      aria-label={`${label} status: ${online ? 'Online' : 'Offline'}`}
    >
      <span
        className={`w-2 h-2 rounded-full ${
          online ? 'animate-led-pulse' : ''
        }`}
        style={{
          background: online ? 'var(--success)' : 'var(--text-muted)',
        }}
        aria-hidden="true"
      />
    </div>
  );
}
