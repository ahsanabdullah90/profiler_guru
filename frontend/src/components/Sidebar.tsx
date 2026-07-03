'use client';

import React from 'react';
import { useAuthStore } from '../store/authStore';
import { LogOut } from 'lucide-react';

/**
 * Persistent right-side rail (100px wide).
 * Per locked design decisions, the only item in the rail is Logout.
 * All other navigation lives in the header user menu.
 */
export default function Sidebar() {
  const setAuthenticated = useAuthStore((s) => s.setAuthenticated);

  return (
    <nav
      className="w-[100px] h-full flex flex-col items-center py-4 bg-[var(--bg-surface-raised)] border-r border-[var(--border-subtle)] shrink-0 z-20"
      aria-label="Primary actions"
    >
      <div className="flex-1" aria-hidden="true" />
      <button
        type="button"
        onClick={() => setAuthenticated(false, null)}
        title="Logout"
        aria-label="Logout"
        className="w-12 h-12 rounded-lg flex flex-col items-center justify-center gap-1 text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface)] transition-colors focus-visible:outline-2 focus-visible:outline-[var(--brand-primary)] focus-visible:outline-offset-2"
      >
        <LogOut className="w-4 h-4" />
        <span className="text-[9px] font-bold uppercase tracking-wider">Logout</span>
      </button>
    </nav>
  );
}
