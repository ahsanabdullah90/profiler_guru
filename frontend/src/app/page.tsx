'use client';

import React, { useState, useEffect } from 'react';
import { useAuthStore } from '../store/authStore';
import { AuthError } from '../store/api';
import ProgressPanel from '../components/ProgressPanel';
import Toast from '../components/Toast';
import Workspace from '../components/Workspace';
import AIHub from '../components/AIHub';
import GlobalSearch from '../components/GlobalSearch';
import Sidebar from '../components/Sidebar';
import Inspector from '../components/Inspector';
import SettingsPanel from '../components/SettingsPanel';
import ImportPanel from '../components/ImportPanel';
import Onboarding from '../components/Onboarding';
import ShortcutsModal from '../components/ShortcutsModal';
import { useNavigationStore } from '../store/navigationStore';
import { hydrateUIStore, useUIStore } from '../store/uiStore';
import { Lock, RefreshCw, Key, ServerCrash } from 'lucide-react';

export default function Page() {
  const isAuthenticated = useAuthStore(s => s.isAuthenticated);
  const verifyToken = useAuthStore(s => s.verifyToken);
  const login = useAuthStore(s => s.login);
  const isBackendOffline = useAuthStore(s => s.isBackendOffline);
  const checkBackendHealth = useAuthStore(s => s.checkBackendHealth);
  const activeSection = useNavigationStore(s => s.activeSection);
  const toggleInspector = useUIStore(s => s.toggleInspector);

  const [password, setPassword] = useState('');
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [authError, setAuthError] = useState('');
  const [isRestoringSession, setIsRestoringSession] = useState(true);
  const [modalsReady, setModalsReady] = useState(false);

  // Verify stored JWT on boot via /api/v1/auth/verify
  useEffect(() => {
    const restore = async () => {
      hydrateUIStore();
      await checkBackendHealth();
      await verifyToken();
      setIsRestoringSession(false);
    };
    restore();
  }, [verifyToken, checkBackendHealth]);

  // Defer modal mount until after auth completes
  useEffect(() => {
    if (isAuthenticated) {
      requestAnimationFrame(() => setModalsReady(true));
    }
  }, [isAuthenticated]);

  // Global keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Ctrl+I / Cmd+I toggles Inspector
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'i' && !e.shiftKey) {
        e.preventDefault();
        toggleInspector();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [toggleInspector]);

  const handlePortalLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsAuthenticating(true);
    setAuthError('');

    try {
      await login(password);
    } catch (err) {
      if (err instanceof AuthError || (err instanceof Error && err.name === 'AuthError')) {
        setAuthError('Access denied. Incorrect password.');
      } else {
        setAuthError('Server connection failed. Please ensure the backend is running.');
      }
    } finally {
      setIsAuthenticating(false);
    }
  };

  if (isRestoringSession) {
    return (
      <div className="h-screen w-screen flex flex-col justify-center items-center bg-[#050506]">
        <RefreshCw className="w-8 h-8 text-[#007AFF] animate-spin glow-primary" />
        <span className="text-xs text-zinc-500 mt-3">Restoring Profile Guru Portal...</span>
      </div>
    );
  }

  /* ==================== GLOBAL HEALTH GATE ==================== */
  if (isBackendOffline) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-[#050506] p-4 font-sans relative overflow-hidden">
        {/* Ambient background glows */}
        <div className="ambient-glow -top-40 -left-40" />
        <div className="ambient-glow -bottom-40 -right-40" />

        <div className="w-full max-w-md glass-panel-heavy p-8 flex flex-col gap-6 relative z-10 border border-[var(--border-glass-bright)] shadow-2xl shadow-[rgba(255,55,95,0.15)]">
          <div className="text-center space-y-2">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-[#FF375F] to-[#FF9500] flex items-center justify-center mx-auto shadow-lg shadow-[rgba(255,55,95,0.2)]">
              <ServerCrash className="w-6 h-6 text-white" />
            </div>
            <h2 className="font-outfit font-bold text-lg text-white mt-3">Backend Server Offline</h2>
            <p className="text-[10px] text-zinc-400 max-w-[280px] mx-auto leading-relaxed">
              Unable to establish a connection with the Profile Guru local server.
            </p>
          </div>

          <div className="p-4 bg-[rgba(255,55,95,0.04)] border border-[rgba(255,55,95,0.15)] rounded-lg space-y-2 text-[10px] text-zinc-400">
            <strong className="text-zinc-200 block font-bold mb-1 uppercase tracking-wider text-[9px]">Troubleshooting Guide:</strong>
            <ul className="list-disc list-inside space-y-1.5 pl-1 leading-relaxed">
              <li>Verify that the backend server is running locally on port <code className="text-zinc-200 bg-zinc-950 px-1 py-0.5 rounded border border-zinc-800 font-mono">8000</code>.</li>
              <li>Double-click the <code className="text-[#FF9500] bg-zinc-950 px-1.5 py-0.5 rounded border border-zinc-800 font-mono">run.bat</code> script in the project root directory.</li>
              <li>Check your command prompt terminal logs for any startup errors or port conflicts.</li>
            </ul>
          </div>

          <button 
            onClick={() => checkBackendHealth()}
            className="w-full py-2.5 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 hover:border-zinc-700 text-white text-xs font-bold rounded-lg transition-colors flex items-center justify-center gap-2 cursor-pointer shadow-md"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  /* ==================== AUTHENTICATION GATE PORTAL ==================== */
  if (!isAuthenticated) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-[#050506] p-4 font-sans relative overflow-hidden">
        {/* Ambient background glows */}
        <div className="ambient-glow -top-40 -left-40" />
        <div className="ambient-glow -bottom-40 -right-40" />

        <div className="w-full max-w-sm glass-panel-heavy p-8 flex flex-col gap-6 relative z-10 border border-[var(--border-glass-bright)] shadow-2xl shadow-[rgba(0,122,255,0.1)]">
          <div className="text-center space-y-2">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-[#007AFF] to-[#32D74B] flex items-center justify-center mx-auto shadow-lg">
              <Lock className="w-5 h-5 text-white" />
            </div>
            <h2 className="font-outfit font-bold text-lg text-white mt-3">Profile Guru Portal</h2>
            <p className="text-[10px] text-zinc-500 max-w-[240px] mx-auto leading-relaxed">
              Decoupled High-Performance DM Intelligence Platform. Enter access password.
            </p>
          </div>

          {authError && (
            <div className="p-3 bg-[rgba(255,55,95,0.08)] border border-[rgba(255,55,95,0.2)] rounded-lg text-[10px] text-[#FF375F] text-center">
              {authError}
            </div>
          )}

          <form onSubmit={handlePortalLogin} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label htmlFor="portal-password" className="text-[9px] uppercase text-zinc-500 font-bold tracking-wider">Access Password</label>
              <input
                id="portal-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter access password"
                className="px-3 py-2 text-xs bg-[rgba(255,255,255,0.015)] border border-[var(--border-glass)] rounded-lg text-white outline-none focus:border-[#007AFF] transition-colors text-center font-mono"
                required
                // eslint-disable-next-line jsx-a11y/no-autofocus -- single-input login form, autoFocus aids usability
                autoFocus
              />
            </div>

            <button 
              type="submit"
              disabled={isAuthenticating}
              className="w-full py-2 bg-[#007AFF] hover:bg-[#0066D6] disabled:bg-zinc-800 text-white text-xs font-bold rounded-lg transition-colors flex items-center justify-center gap-2 cursor-pointer"
            >
              {isAuthenticating ? (
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Key className="w-3.5 h-3.5" />
              )}
              Unlock Portal
            </button>
          </form>
        </div>

        <Toast />
      </div>
    );
  }

  /* ==================== AUTHENTICATED WORKSPACE (16:9 VIEWPORT) ==================== */
  return (
    <div className="w-full h-full flex flex-col overflow-hidden bg-[var(--bg-canvas)] relative font-sans select-none">
      {/* Content Area with Sidebar + Inspector */}
      <div className="flex-1 flex min-h-0 overflow-hidden relative z-10">
        {/* Sidebar Navigation */}
        <Sidebar />

        {/* Main Content */}
        {activeSection === 'home' ? (
          <div className="flex-1 flex flex-col md:flex-row min-h-0 overflow-hidden">
            {/* Column A (40% Width on desktop, full on mobile): Main Workspace Panel */}
            <div className="w-full md:w-[40%] h-full md:h-full border-r border-[var(--border-subtle)] bg-[var(--bg-surface)] min-h-0 overflow-hidden">
              <Workspace />
            </div>

            {/* Column B (60% Width on desktop, full on mobile): Unified AI Intelligence Hub */}
            <div className="w-full md:w-[60%] h-full md:h-full bg-[var(--bg-surface-inset)] min-h-0 overflow-hidden">
              <AIHub />
            </div>
          </div>
        ) : activeSection === 'settings' ? (
          <div className="flex-1 min-h-0 overflow-hidden bg-[var(--bg-surface-inset)]">
            <SettingsPanel />
          </div>
        ) : (
          <div className="flex-1 min-h-0 overflow-hidden bg-[var(--bg-surface-inset)]">
            <ImportPanel />
          </div>
        )}

        {/* Inspector Pane (right rail) */}
        {activeSection === 'home' ? <Inspector /> : null}
      </div>

      {/* 3. Persistent Bottom Progress Panel (Height: 40px compact, 300px expanded) */}
      <ProgressPanel />

      {/* Toast notifications */}
      <Toast />

      {/* 4. Overlay Command Palette Modal (Ctrl+K) */}
      {modalsReady ? (
        <>
          <GlobalSearch />
          <Onboarding />
          <ShortcutsModal />
        </>
      ) : null}
    </div>
  );
}
