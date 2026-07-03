/**
 * @file SettingsPanel.tsx
 * @description User settings panel component. Fetches current settings via GET `/settings`
 * and updates them via POST `/settings`. Configures cloud provider integrations, 
 * local Ollama model names, and deep scan/pdf rendering preferences.
 * 
 * State:
 * - settings (SettingsData): Active configuration state
 * - loading (boolean): Loader state during initialization
 * - saving (boolean): Loader state during form submit
 * - message (string): User feedback on save success/error
 */

'use client';


import React, { useState, useEffect } from 'react';
import { apiFetch } from '../store/api';
import { Settings, Save, RefreshCw } from 'lucide-react';

interface SettingsData {
  cloud_provider: string;
  cloud_api_key: string;
  llm_provider: string;
  ollama_model: string;
  deep_scan: boolean;
  pdf_include_charts: boolean;
}

export default function SettingsPanel() {
  const [settings, setSettings] = useState<SettingsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    apiFetch('/settings').then((data: any) => {
      setSettings(data.settings);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    if (!settings) return;
    setSaving(true);
    try {
      await apiFetch('/settings', { method: 'POST', body: JSON.stringify({ settings }) });
      setMessage('Settings saved successfully');
      setTimeout(() => setMessage(''), 3000);
    } catch {
      setMessage('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <RefreshCw className="w-5 h-5 text-zinc-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <div className="p-6 border-b border-zinc-800 bg-zinc-900 shrink-0 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Settings className="w-4 h-4 text-primary" />
          <h2 className="font-outfit font-bold text-sm text-white">Settings</h2>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary/15 border border-primary/30 text-xs font-bold text-white hover:bg-primary/25 transition-all cursor-pointer"
        >
          {saving ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
          Save
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {message && (
          <div className={`p-3 rounded-lg text-xs ${message.includes('success') ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400' : 'bg-red-500/10 border border-red-500/20 text-red-400'}`}>
            {message}
          </div>
        )}

        {settings && (
          <>
            <div className="space-y-3">
              <label className="text-[10px] uppercase text-zinc-500 font-bold">Cloud Provider</label>
              <input
                value={settings.cloud_provider}
                onChange={(e) => setSettings({ ...settings, cloud_provider: e.target.value })}
                className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-lg text-xs text-white outline-none focus:border-primary transition-colors"
              />
            </div>

            <div className="space-y-3">
              <label className="text-[10px] uppercase text-zinc-500 font-bold">Cloud API Key</label>
              <input
                type="password"
                value={settings.cloud_api_key}
                onChange={(e) => setSettings({ ...settings, cloud_api_key: e.target.value })}
                className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-lg text-xs text-white outline-none focus:border-primary transition-colors"
              />
            </div>

            <div className="space-y-3">
              <label className="text-[10px] uppercase text-zinc-500 font-bold">Ollama Model</label>
              <input
                value={settings.ollama_model}
                onChange={(e) => setSettings({ ...settings, ollama_model: e.target.value })}
                className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-lg text-xs text-white outline-none focus:border-primary transition-colors"
              />
            </div>

            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={settings.deep_scan}
                onChange={(e) => setSettings({ ...settings, deep_scan: e.target.checked })}
                className="accent-primary"
              />
              <span className="text-xs text-zinc-300">Enable deep scan by default</span>
            </div>

            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={settings.pdf_include_charts}
                onChange={(e) => setSettings({ ...settings, pdf_include_charts: e.target.checked })}
                className="accent-primary"
              />
              <span className="text-xs text-zinc-300">Include charts in PDF reports</span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
