'use client';

import React, { useState, useEffect } from 'react';
import { useSyncStore } from '../store/useSyncStore';
import Header from '../components/Header';
import StatusBar from '../components/StatusBar';
import Toast from '../components/Toast';
import Workspace from '../components/Workspace';
import AIHub from '../components/AIHub';
import GlobalSearch from '../components/GlobalSearch';
import { Lock, RefreshCw, Key } from 'lucide-react';

export default function Page() {
  const {
    isAuthenticated,
    setGlobalSearchOpen,
    isGlobalSearchOpen,
    verifyToken,
    login,
  } = useSyncStore();

  const [password, setPassword] = useState('');
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [authError, setAuthError] = useState('');
  const [isRestoringSession, setIsRestoringSession] = useState(true);

  // Verify stored JWT on boot via /api/v1/auth/verify
  useEffect(() => {
    const restore = async () => {
      await verifyToken();
      setIsRestoringSession(false);
    };
    restore();
  }, [verifyToken]);

  const handlePortalLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsAuthenticating(true);
    setAuthError('');

    try {
      const ok = await login(password);
      if (!ok) {
        setAuthError('Access denied. Incorrect password.');
      }
    } catch (err: any) {
      setAuthError(`Server connection failed: ${err.message}`);
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
              <label className="text-[9px] uppercase text-zinc-500 font-bold tracking-wider">Access Password</label>
              <input 
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter access password"
                className="px-3 py-2 text-xs bg-[rgba(255,255,255,0.015)] border border-[var(--border-glass)] rounded-lg text-white outline-none focus:border-[#007AFF] transition-colors text-center font-mono"
                required
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
    <div className="w-screen h-screen flex flex-col overflow-hidden bg-[#050506] relative font-sans select-none">
      {/* 1. Header Navigation (Height: 60px) */}
      <Header />

      {/* 2. Rigid Two-Column Workspace (Height: calc(100vh - 100px)) */}
      <div className="flex-1 w-full flex min-h-0 overflow-hidden relative z-10">
        
        {/* Column A (40% Width): Main Workspace Panel */}
        <div className="w-[40%] h-full border-r border-[var(--border-glass)] bg-[rgba(10,10,12,0.15)] min-h-0 overflow-hidden">
          <Workspace />
        </div>

        {/* Column B (60% Width): Unified AI Intelligence Hub */}
        <div className="w-[60%] h-full bg-[rgba(10,10,12,0.05)] min-h-0 overflow-hidden">
          <AIHub />
        </div>

      </div>

      {/* 3. Persistent Bottom Status Bar (Height: 40px) */}
      <StatusBar />

      {/* Toast notifications */}
      <Toast />

      {/* 4. Overlay Command Palette Modal (Ctrl+K) */}
      <GlobalSearch />

      {/* Visual Command Palette Helper float (bottom left, above status bar) */}
      <button 
        onClick={() => setGlobalSearchOpen(!isGlobalSearchOpen)}
        className="absolute bottom-14 left-6 px-3 py-1.5 rounded-lg border border-[var(--border-glass)] bg-[rgba(10,10,12,0.6)] backdrop-blur-md text-[10px] font-mono text-zinc-500 hover:text-white transition-all hover:border-zinc-700 z-20 cursor-pointer shadow-lg"
      >
        Press <kbd className="bg-zinc-950 px-1 py-0.5 rounded border border-zinc-800 mx-0.5 text-zinc-400">Ctrl+K</kbd> to search
      </button>
    </div>
  );
}
