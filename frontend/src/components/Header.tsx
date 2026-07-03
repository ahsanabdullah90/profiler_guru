'use client';

import React from 'react';
import { useAuthStore } from '../store/authStore';
import { LogOut } from 'lucide-react';

export default function Header() {
  const setAuthenticated = useAuthStore(s => s.setAuthenticated);

  return (
    <header className="h-[60px] w-full px-6 flex items-center justify-between border-b border-[var(--border-glass)] bg-[rgba(10,10,12,0.4)] backdrop-blur-md relative z-30">
      {/* Brand & Logo */}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-primary to-success flex items-center justify-center shadow-lg shadow-primary/20">
          <span className="font-bold text-white text-sm font-outfit">PG</span>
        </div>
        <h1 className="font-outfit font-bold text-lg tracking-tight bg-gradient-to-r from-white via-[#E5E2E3] to-rgba(255,255,255,0.7) bg-clip-text text-transparent">
          Profile Guru
        </h1>
        <span className="text-[10px] uppercase tracking-widest font-mono text-zinc-600 bg-zinc-900 px-2 py-0.5 rounded border border-zinc-800 hidden sm:inline">
          v2.0 Elite
        </span>
      </div>

      {/* Logout */}
      <button
        onClick={() => setAuthenticated(false, null)}
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-[var(--border-glass)] bg-[rgba(255,255,255,0.01)] text-[10px] font-bold text-zinc-400 hover:text-white hover:bg-[rgba(255,255,255,0.04)] hover:border-zinc-700 transition-all cursor-pointer"
      >
        <LogOut className="w-3.5 h-3.5" /> Logout
      </button>
    </header>
  );
}
