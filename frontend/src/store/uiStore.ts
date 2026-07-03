'use client';

import { create } from 'zustand';

export type Theme = 'dark' | 'light';

interface UIState {
  theme: Theme;
  inspectorOpen: boolean;
  inspectorWidth: number;
  inspectorHintShown: boolean;
  onboardingShown: boolean;
  shortcutsOpen: boolean;

  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
  setInspectorOpen: (open: boolean) => void;
  toggleInspector: () => void;
  setInspectorWidth: (width: number) => void;
  dismissInspectorHint: () => void;
  dismissOnboarding: () => void;
  openShortcuts: () => void;
  closeShortcuts: () => void;
}

const STORAGE_KEYS = {
  theme: 'pg.theme',
  inspectorOpen: 'pg.inspector.open',
  inspectorWidth: 'pg.inspector.width',
  inspectorHint: 'pg.inspector.hintShown',
  onboardingShown: 'pg.onboarding.shown',
};

function safeGet<T>(key: string, fallback: T): T {
  if (typeof window === 'undefined') return fallback;
  try {
    const v = window.localStorage.getItem(key);
    if (v === null) return fallback;
    return JSON.parse(v) as T;
  } catch {
    return fallback;
  }
}

function safeSet(key: string, value: unknown): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // ignore quota / privacy errors
  }
}

function applyTheme(theme: Theme): void {
  if (typeof document === 'undefined') return;
  document.documentElement.setAttribute('data-theme', theme);
}

export const useUIStore = create<UIState>((set, get) => ({
  theme: 'dark',
  inspectorOpen: true,
  inspectorWidth: 320,
  inspectorHintShown: false,
  onboardingShown: false,
  shortcutsOpen: false,

  setTheme: (theme) => {
    safeSet(STORAGE_KEYS.theme, theme);
    applyTheme(theme);
    set({ theme });
  },

  toggleTheme: () => {
    const next: Theme = get().theme === 'dark' ? 'light' : 'dark';
    get().setTheme(next);
  },

  setInspectorOpen: (open) => {
    safeSet(STORAGE_KEYS.inspectorOpen, open);
    set({ inspectorOpen: open });
  },

  toggleInspector: () => {
    get().setInspectorOpen(!get().inspectorOpen);
  },

  setInspectorWidth: (width) => {
    const clamped = Math.max(280, Math.min(480, width));
    safeSet(STORAGE_KEYS.inspectorWidth, clamped);
    set({ inspectorWidth: clamped });
  },

  dismissInspectorHint: () => {
    safeSet(STORAGE_KEYS.inspectorHint, true);
    set({ inspectorHintShown: true });
  },

  dismissOnboarding: () => {
    safeSet(STORAGE_KEYS.onboardingShown, true);
    set({ onboardingShown: true });
  },

  openShortcuts: () => set({ shortcutsOpen: true }),
  closeShortcuts: () => set({ shortcutsOpen: false }),
}));

/**
 * Hydrate the UI store from localStorage. Call once on app mount.
 * Safe to call on the client only.
 */
export function hydrateUIStore(): void {
  if (typeof window === 'undefined') return;
  const theme = safeGet<Theme>(STORAGE_KEYS.theme, 'dark');
  applyTheme(theme);
  useUIStore.setState({
    theme,
    inspectorOpen: safeGet<boolean>(STORAGE_KEYS.inspectorOpen, true),
    inspectorWidth: safeGet<number>(STORAGE_KEYS.inspectorWidth, 320),
    inspectorHintShown: safeGet<boolean>(STORAGE_KEYS.inspectorHint, false),
    onboardingShown: safeGet<boolean>(STORAGE_KEYS.onboardingShown, false),
  });
}
