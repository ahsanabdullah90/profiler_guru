'use client';

import React, { useState, useEffect } from 'react';
import { useSyncStore, getApiBase } from '../store/useSyncStore';
import { Shield, Key, RefreshCw, Smartphone, AlertTriangle, Cpu, Globe } from 'lucide-react';

export default function Header() {
  const { 
    status,
    triggerInstagramSync, 
    toggleDaemonSync, 
    fetchContacts 
  } = useSyncStore();

  const [isOpen, setIsOpen] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [twoFactorCode, setTwoFactorCode] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [igStatus, setIgStatus] = useState<any>({ logged_in: false, username: '', challenge_url: null });

  // Fetch Instagram login status from backend
  const fetchIgStatus = async () => {
    try {
      const res = await fetch(`${getApiBase()}/api/instagram/status`);
      if (res.ok) {
        const data = await res.json();
        setIgStatus(data);
        if (data.username) {
          setUsername(data.username);
        }
      }
    } catch (e) {
      console.error('Failed to fetch IG status:', e);
    }
  };

  // Fetch IG status only once the backend is confirmed online (status.app_online
  // is set to true by the StatusBar WebSocket). This prevents spammy "Failed to
  // fetch" console errors and avoids polling a server that isn't ready yet.
  useEffect(() => {
    if (!status.app_online) return;
    fetchIgStatus();
    const timer = setInterval(fetchIgStatus, 5000);
    return () => clearInterval(timer);
  }, [status.app_online]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMessage('');
    setSuccessMessage('');
    
    try {
      const res = await fetch(`${getApiBase()}/api/instagram/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      
      const data = await res.json();
      if (res.ok) {
        if (data.status === 'success') {
          setSuccessMessage('Successfully connected to Instagram! ✅');
          setPassword('');
          fetchIgStatus();
          fetchContacts();
        } else if (data.status === '2fa_required') {
          setSuccessMessage('2FA code required. Please enter it below.');
        } else if (data.status === 'challenge') {
          setErrorMessage('Instagram requires checkpoint verification. Click the link below.');
          fetchIgStatus();
        }
      } else {
        setErrorMessage(data.detail || 'Authentication failed. Please check credentials.');
      }
    } catch (e: any) {
      setErrorMessage(`Server connection error: ${e.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handle2FA = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMessage('');
    setSuccessMessage('');
    
    try {
      const res = await fetch(`${getApiBase()}/api/instagram/2fa`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, code: twoFactorCode })
      });
      
      const data = await res.json();
      if (res.ok) {
        setSuccessMessage('Successfully authenticated with 2FA! ✅');
        setTwoFactorCode('');
        setPassword('');
        fetchIgStatus();
        fetchContacts();
      } else {
        setErrorMessage(data.detail || '2FA verification failed.');
      }
    } catch (e: any) {
      setErrorMessage(`2FA submission error: ${e.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSyncOnce = async () => {
    const success = await triggerInstagramSync();
    if (success) {
      alert('Manual Instagram Sync initiated successfully! Progress is displayed in the status bar.');
    } else {
      alert('Failed to initiate sync. Please ensure Instagram is connected.');
    }
  };

  const handleToggleDaemon = async () => {
    await toggleDaemonSync();
    fetchIgStatus();
  };

  return (
    <header className="h-[60px] w-full px-6 flex items-center justify-between border-b border-[var(--border-glass)] bg-[rgba(10,10,12,0.4)] backdrop-blur-md relative z-30">
      {/* Brand & Logo */}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-[#007AFF] to-[#32D74B] flex items-center justify-center shadow-lg shadow-[rgba(0,122,255,0.2)]">
          <span className="font-bold text-white text-sm font-outfit">PG</span>
        </div>
        <h1 className="font-outfit font-bold text-lg tracking-tight bg-gradient-to-r from-white via-[#E5E2E3] to-rgba(255,255,255,0.7) bg-clip-text text-transparent">
          Profile Guru
        </h1>
        <span className="text-[10px] uppercase tracking-widest font-mono text-zinc-600 bg-zinc-900 px-2 py-0.5 rounded border border-zinc-800">
          v2.0 Elite
        </span>
      </div>

      {/* Connection & Account Panel */}
      <div className="relative">
        <button 
          onClick={() => setIsOpen(!isOpen)}
          className={`flex items-center gap-2.5 px-4 py-1.5 rounded-lg border text-xs font-semibold transition-all duration-200 ${
            igStatus.logged_in 
              ? 'bg-[rgba(50,215,75,0.06)] border-[rgba(50,215,75,0.25)] text-[#32D74B] hover:bg-[rgba(50,215,75,0.1)]' 
              : 'bg-[rgba(255,55,95,0.06)] border-[rgba(255,55,95,0.25)] text-[#FF375F] hover:bg-[rgba(255,55,95,0.1)]'
          }`}
        >
          <span className={`w-2 h-2 rounded-full ${igStatus.logged_in ? 'bg-[#32D74B] animate-led-pulse' : 'bg-[#FF375F]'}`} />
          {igStatus.logged_in ? `Connected: @${igStatus.username}` : 'Instagram Disconnected'}
        </button>

        {/* Credentials / 2FA / Challenges Frosted Dropdown Card */}
        {isOpen && (
          <div className="absolute right-0 mt-3 w-80 p-5 glass-panel-heavy z-40 animate-fade-in">
            <h3 className="font-outfit font-bold text-sm text-white mb-3 flex items-center gap-2">
              <Shield className="w-4 h-4 text-[#007AFF]" /> Instagram Integration
            </h3>

            {errorMessage && (
              <div className="p-3 mb-3 bg-[rgba(255,55,95,0.08)] border border-[rgba(255,55,95,0.2)] rounded-lg text-[11px] text-[#FF375F] flex gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>{errorMessage}</span>
              </div>
            )}

            {successMessage && (
              <div className="p-3 mb-3 bg-[rgba(50,215,75,0.08)] border border-[rgba(50,215,75,0.2)] rounded-lg text-[11px] text-[#32D74B] flex gap-2">
                <span>{successMessage}</span>
              </div>
            )}

            {igStatus.challenge_url && (
              <div className="p-3 mb-4 bg-[rgba(255,149,0,0.08)] border border-[rgba(255,149,0,0.2)] rounded-lg text-[11px]">
                <p className="text-[#FF9500] font-bold mb-1.5 flex items-center gap-1">
                  <AlertTriangle className="w-3.5 h-3.5" /> Suspicious Login Detected
                </p>
                <p className="text-zinc-400 mb-2">Instagram flagged the attempt. Open the link to verify, click "It was me", then retry.</p>
                <a 
                  href={igStatus.challenge_url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="block text-center py-1.5 bg-[#FF9500] text-black font-bold rounded hover:bg-[#E08200] transition-colors mb-2"
                >
                  Verify on Instagram
                </a>
              </div>
            )}

            {/* Logged Out Form */}
            {!igStatus.logged_in ? (
              <form onSubmit={igStatus.two_factor_required ? handle2FA : handleLogin} className="flex flex-col gap-3">
                <div className="flex flex-col gap-1">
                  <label className="text-[10px] uppercase text-zinc-500 font-bold">Instagram Username</label>
                  <input 
                    type="text" 
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="Enter Instagram username"
                    className="px-3 py-2 text-xs bg-[rgba(255,255,255,0.02)] border border-[var(--border-glass)] rounded-lg text-white outline-none focus:border-[#007AFF] transition-colors"
                    required
                  />
                </div>

                <div className="flex flex-col gap-1">
                  <label className="text-[10px] uppercase text-zinc-500 font-bold">Password</label>
                  <input 
                    type="password" 
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter Instagram password"
                    className="px-3 py-2 text-xs bg-[rgba(255,255,255,0.02)] border border-[var(--border-glass)] rounded-lg text-white outline-none focus:border-[#007AFF] transition-colors"
                    required
                  />
                </div>

                {igStatus.two_factor_required && (
                  <div className="flex flex-col gap-1 border-t border-[var(--border-glass)] pt-2 mt-1">
                    <label className="text-[10px] uppercase text-[#FF9500] font-bold flex items-center gap-1">
                      <Smartphone className="w-3.5 h-3.5" /> 6-Digit 2FA Code
                    </label>
                    <input 
                      type="text" 
                      value={twoFactorCode}
                      onChange={(e) => setTwoFactorCode(e.target.value)}
                      placeholder="e.g., 123456"
                      className="px-3 py-2 text-xs bg-[rgba(255,255,255,0.02)] border border-[#FF9500] rounded-lg text-white outline-none focus:ring-1 focus:ring-[#FF9500] transition-all"
                      required
                    />
                  </div>
                )}

                <button 
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full py-2 bg-[#007AFF] hover:bg-[#0066D6] disabled:bg-zinc-800 text-white text-xs font-bold rounded-lg transition-colors flex items-center justify-center gap-2 mt-1"
                >
                  {isSubmitting ? (
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Key className="w-3.5 h-3.5" />
                  )}
                  {igStatus.two_factor_required ? 'Verify 2FA Code' : 'Connect Account'}
                </button>
              </form>
            ) : (
              /* Connected Actions Panel */
              <div className="flex flex-col gap-3">
                <div className="p-3 bg-[rgba(255,255,255,0.01)] border border-[var(--border-glass)] rounded-lg text-xs text-zinc-400">
                  <p>Connected Username: <strong className="text-white">@{igStatus.username}</strong></p>
                  <p className="mt-1">Active Syncs: <strong className="text-white">{status.instagram_sync.status === 'syncing' ? '1' : '0'}</strong></p>
                </div>

                <button 
                  onClick={handleSyncOnce}
                  className="w-full py-2 bg-[#007AFF] hover:bg-[#0066D6] text-white text-xs font-bold rounded-lg transition-colors flex items-center justify-center gap-2"
                >
                  <RefreshCw className="w-3.5 h-3.5" /> Force Sync Recent Threads
                </button>

                <button 
                  onClick={handleToggleDaemon}
                  className={`w-full py-2 text-xs font-bold rounded-lg border transition-colors flex items-center justify-center gap-2 ${
                    igStatus.daemon_sync_active
                      ? 'bg-[rgba(255,55,95,0.06)] border-[rgba(255,55,95,0.2)] hover:bg-[rgba(255,55,95,0.1)] text-[#FF375F]'
                      : 'bg-[rgba(50,215,75,0.06)] border-[rgba(50,215,75,0.2)] hover:bg-[rgba(50,215,75,0.1)] text-[#32D74B]'
                  }`}
                >
                  {igStatus.daemon_sync_active ? 'Stop Daemon Sync' : 'Start Daemon Sync'}
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </header>
  );
}
