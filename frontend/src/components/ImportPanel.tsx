/**
 * @file ImportPanel.tsx
 * @description Interface for triggering the import of Instagram or Facebook zip/unzipped data exports.
 * Prompts the user for a filesystem path containing the `messages/inbox/` directory 
 * and sends a POST request to `/contacts/import` using `apiFetch`.
 * 
 * State:
 * - folderPath (string): Path to target data folder
 * - importing (boolean): Loading indicator for active API requests
 * - message (string): Feedback message for success or failure
 */

'use client';


import React, { useState } from 'react';
import { apiFetch } from '../store/api';
import { Upload, FolderOpen, RefreshCw } from 'lucide-react';

export default function ImportPanel() {
  const [folderPath, setFolderPath] = useState('');
  const [importing, setImporting] = useState(false);
  const [message, setMessage] = useState('');

  const handleImport = async () => {
    if (!folderPath.trim()) return;
    setImporting(true);
    setMessage('');
    try {
      await apiFetch('/contacts/import', {
        method: 'POST',
        body: JSON.stringify({ path: folderPath.trim() }),
      });
      setMessage('Import started. Check the Progress Panel for status.');
    } catch {
      setMessage('Failed to start import. Check that the path is correct.');
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <div className="p-6 border-b border-zinc-800 bg-zinc-900 shrink-0">
        <div className="flex items-center gap-2">
          <Upload className="w-4 h-4 text-primary" />
          <h2 className="font-outfit font-bold text-sm text-white">Import Instagram Data</h2>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        <p className="text-xs text-zinc-400 leading-relaxed">
          Import your Instagram data export. Unzip the downloaded archive and point to the folder containing your <code className="bg-zinc-950 px-1.5 py-0.5 rounded border border-zinc-800 text-zinc-300 font-mono">messages/inbox/</code> directory.
        </p>

        {message && (
          <div className={`p-3 rounded-lg text-xs ${message.includes('started') ? 'bg-blue-500/10 border border-blue-500/20 text-blue-400' : 'bg-red-500/10 border border-red-500/20 text-red-400'}`}>
            {message}
          </div>
        )}

        <div className="space-y-3">
          <label className="text-[10px] uppercase text-zinc-500 font-bold">Export Folder Path</label>
          <div className="flex gap-2">
            <input
              value={folderPath}
              onChange={(e) => setFolderPath(e.target.value)}
              placeholder="C:\Users\You\Downloads\instagram-export"
              className="flex-1 px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-lg text-xs text-white outline-none focus:border-primary transition-colors font-mono"
            />
            <button
              onClick={handleImport}
              disabled={importing || !folderPath.trim()}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary/15 border border-primary/30 text-xs font-bold text-white hover:bg-primary/25 disabled:opacity-40 transition-all cursor-pointer"
            >
              {importing ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <FolderOpen className="w-3.5 h-3.5" />}
              Import
            </button>
          </div>
        </div>

        <div className="p-4 bg-zinc-900/50 border border-zinc-800 rounded-lg text-[10px] text-zinc-500 space-y-2">
          <p className="font-bold text-zinc-400 uppercase tracking-wider">Supported Formats</p>
          <ul className="space-y-1 list-disc list-inside">
            <li>Instagram data export ZIP (unzipped)</li>
            <li>Facebook data export ZIP (unzipped)</li>
            <li>Must contain <span className="text-zinc-300 font-mono">messages/inbox/</span> directory</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
