/**
 * @file navigationStore.ts
 * @description Zustand store for tracking the global active section of the Profile Guru application.
 * Used to manage navigation state between Home, Data Import, Settings, and Knowledge views.
 * 
 * State:
 * - activeSection: 'home' | 'import' | 'settings' | 'knowledge' (default is 'home')
 * Actions:
 * - setActiveSection(section): Updates the active view.
 */

import { create } from 'zustand';


type ActiveSection = 'home' | 'clients' | 'import' | 'settings' | 'knowledge';

interface NavigationState {
  activeSection: ActiveSection;
  setActiveSection: (section: ActiveSection) => void;
}

export const useNavigationStore = create<NavigationState>((set) => ({
  activeSection: 'home',
  setActiveSection: (activeSection) => set({ activeSection }),
}));
