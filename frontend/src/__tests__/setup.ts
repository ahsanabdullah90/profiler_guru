/**
 * Global test setup for Vitest + jsdom.
 *
 * - Provides a minimal localStorage mock so store tests that touch
 *   localStorage do not throw in the jsdom environment.
 * - Clears module registry and store state between tests via vi.resetModules().
 */
import { vi } from 'vitest';

// Minimal localStorage shim (jsdom has one but it's not persistent across modules)
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => { store[key] = value; },
    removeItem: (key: string) => { delete store[key]; },
    clear: () => { store = {}; },
    get length() { return Object.keys(store).length; },
    key: (i: number) => Object.keys(store)[i] ?? null,
  };
})();

Object.defineProperty(globalThis, 'localStorage', { value: localStorageMock });

// Suppress console.error noise from expected thrown errors in tests
vi.spyOn(console, 'error').mockImplementation(() => {});
