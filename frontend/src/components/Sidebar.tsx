/**
 * @file Sidebar.tsx
 * @description Persistent left-hand vertical navigation sidebar (60px wide).
 * Renders icons for Home, Import, and Settings sections, and triggers section switching 
 * via `useNavigationStore`. Includes a logout button at the bottom using `useAuthStore`.
 * 
 * Dependencies:
 * - Zustand stores: `useNavigationStore` (navigation state), `useAuthStore` (auth state)
 * - Icons: Lucide-react (Home, Upload, Settings, LogOut)
 */

'use client';


import React from 'react';
import { useNavigationStore } from '../store/navigationStore';
import { useAuthStore } from '../store/authStore';
import { Home, Upload, Settings, LogOut } from 'lucide-react';

const NAV_ITEMS = [
  { id: 'home' as const, icon: Home, label: 'Home' },
  { id: 'import' as const, icon: Upload, label: 'Import Data' },
  { id: 'settings' as const, icon: Settings, label: 'Settings' },
];

export default function Sidebar() {
  const activeSection = useNavigationStore(s => s.activeSection);
  const setActiveSection = useNavigationStore(s => s.setActiveSection);
  const setAuthenticated = useAuthStore(s => s.setAuthenticated);

  return (
    <nav className="w-[60px] h-full flex flex-col items-center py-4 bg-zinc-900 border-r border-zinc-800 shrink-0 z-20">
      {/* Nav Items */}
      <div className="flex flex-col gap-1 flex-1">
        {NAV_ITEMS.map(({ id, icon: Icon, label }) => {
          const isActive = activeSection === id;
          return (
            <button
              key={id}
              onClick={() => setActiveSection(id)}
              title={label}
              className={`relative w-10 h-10 rounded-lg flex items-center justify-center transition-all cursor-pointer ${
                isActive
                  ? 'bg-primary/15 text-primary'
                  : 'text-zinc-200 hover:text-white hover:bg-zinc-700/60'
              }`}
            >
              {isActive && (
                <div className="absolute left-0 top-1.5 bottom-1.5 w-[3px] rounded-full bg-primary" />
              )}
              <Icon className="w-5 h-5" />
            </button>
          );
        })}
      </div>

      {/* Logout at bottom */}
      <button
        onClick={() => setAuthenticated(false, null)}
        title="Logout"
        className="w-10 h-10 rounded-lg flex items-center justify-center text-zinc-400 hover:text-white hover:bg-zinc-700/60 transition-all cursor-pointer"
      >
        <LogOut className="w-5 h-5" />
      </button>
    </nav>
  );
}
