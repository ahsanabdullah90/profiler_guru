'use client';

import React, { useState } from 'react';
import { useContactsStore } from '../store/contactsStore';
import { useStatusStore } from '../store/statusStore';
import { X, UserPlus, Loader2 } from 'lucide-react';

interface Props {
  onClose: () => void;
  onCreated: (chatName: string) => void;
}

export default function CreateClientModal({ onClose, onCreated }: Props) {
  const createClient = useContactsStore((s) => s.createClient);
  const pushError = useStatusStore((s) => s.pushError);

  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [mobile, setMobile] = useState('');
  const [whatsapp, setWhatsapp] = useState('');
  const [instagramHandle, setInstagramHandle] = useState('');
  const [dob, setDob] = useState('');
  const [nationalId, setNationalId] = useState('');

  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!displayName.trim()) {
      pushError('Display name is required', 'error');
      return;
    }

    setSubmitting(true);
    try {
      const chatName = await createClient({
        display_name: displayName.trim(),
        email: email.trim() || null,
        mobile: mobile.trim() || null,
        whatsapp: whatsapp.trim() || null,
        instagram_handle: instagramHandle.trim() || null,
        dob: dob.trim() || null,
        national_id: nationalId.trim() || null,
      });
      pushError('Manual client registered successfully', 'info');
      onCreated(chatName);
    } catch (err) {
      const error = err as Error;
      pushError(`Failed to create client: ${error.message}`, 'error');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <div className="fixed inset-0 bg-black/40 z-50 animate-fade-in" onClick={onClose} />
      <div className="fixed inset-0 flex items-center justify-center z-50 pointer-events-none p-4">
        <div
          className="pointer-events-auto bg-[var(--bg-surface-raised)] border border-[var(--border-subtle)] rounded-xl shadow-2xl w-full max-w-lg max-h-[90vh] flex flex-col overflow-hidden animate-slide-up"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--border-subtle)] shrink-0">
            <h3 className="text-sm font-bold text-[var(--text-primary)] flex items-center gap-2">
              <UserPlus className="w-4 h-4 text-primary" />
              Register New Client
            </h3>
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-lg flex items-center justify-center text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface)] transition-colors cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Form Content */}
          <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-5 space-y-4 scrollbar-thin">
            <div className="space-y-3">
              <div>
                <label className="block text-[10px] uppercase tracking-wider font-bold text-[var(--text-muted)] mb-1">
                  Display Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="e.g. Jane Doe"
                  className="w-full px-3 py-2 bg-[var(--bg-surface)] border border-[var(--border-glass)] rounded-lg text-xs text-[var(--text-primary)] outline-none focus:border-primary transition-all placeholder:text-[var(--text-muted)]/40"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-[10px] uppercase tracking-wider font-bold text-[var(--text-muted)] mb-1">
                    Email
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="e.g. jane@example.com"
                    className="w-full px-3 py-2 bg-[var(--bg-surface)] border border-[var(--border-glass)] rounded-lg text-xs text-[var(--text-primary)] outline-none focus:border-primary transition-all placeholder:text-[var(--text-muted)]/40"
                  />
                </div>
                <div>
                  <label className="block text-[10px] uppercase tracking-wider font-bold text-[var(--text-muted)] mb-1">
                    Phone / Mobile
                  </label>
                  <input
                    type="text"
                    value={mobile}
                    onChange={(e) => setMobile(e.target.value)}
                    placeholder="e.g. +1 555-0199"
                    className="w-full px-3 py-2 bg-[var(--bg-surface)] border border-[var(--border-glass)] rounded-lg text-xs text-[var(--text-primary)] outline-none focus:border-primary transition-all placeholder:text-[var(--text-muted)]/40"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-[10px] uppercase tracking-wider font-bold text-[var(--text-muted)] mb-1">
                    WhatsApp Number
                  </label>
                  <input
                    type="text"
                    value={whatsapp}
                    onChange={(e) => setWhatsapp(e.target.value)}
                    placeholder="e.g. +15550199"
                    className="w-full px-3 py-2 bg-[var(--bg-surface)] border border-[var(--border-glass)] rounded-lg text-xs text-[var(--text-primary)] outline-none focus:border-primary transition-all placeholder:text-[var(--text-muted)]/40"
                  />
                </div>
                <div>
                  <label className="block text-[10px] uppercase tracking-wider font-bold text-[var(--text-muted)] mb-1">
                    Instagram Handle
                  </label>
                  <input
                    type="text"
                    value={instagramHandle}
                    onChange={(e) => setInstagramHandle(e.target.value)}
                    placeholder="e.g. jane_doe"
                    className="w-full px-3 py-2 bg-[var(--bg-surface)] border border-[var(--border-glass)] rounded-lg text-xs text-[var(--text-primary)] outline-none focus:border-primary transition-all placeholder:text-[var(--text-muted)]/40"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-[10px] uppercase tracking-wider font-bold text-[var(--text-muted)] mb-1">
                    Date of Birth
                  </label>
                  <input
                    type="text"
                    value={dob}
                    onChange={(e) => setDob(e.target.value)}
                    placeholder="YYYY-MM-DD"
                    className="w-full px-3 py-2 bg-[var(--bg-surface)] border border-[var(--border-glass)] rounded-lg text-xs text-[var(--text-primary)] outline-none focus:border-primary transition-all placeholder:text-[var(--text-muted)]/40"
                  />
                </div>
                <div>
                  <label className="block text-[10px] uppercase tracking-wider font-bold text-[var(--text-muted)] mb-1">
                    National ID / CNIC / SSN
                  </label>
                  <input
                    type="text"
                    value={nationalId}
                    onChange={(e) => setNationalId(e.target.value)}
                    placeholder="ID details"
                    className="w-full px-3 py-2 bg-[var(--bg-surface)] border border-[var(--border-glass)] rounded-lg text-xs text-[var(--text-primary)] outline-none focus:border-primary transition-all placeholder:text-[var(--text-muted)]/40"
                  />
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center justify-end gap-2.5 pt-4 border-t border-[var(--border-subtle)] shrink-0">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 border border-[var(--border-glass)] hover:bg-[var(--bg-surface)] text-[var(--text-secondary)] text-xs font-semibold rounded-lg transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="px-4 py-2 bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-strong)] disabled:opacity-40 text-white text-xs font-semibold rounded-lg flex items-center gap-1.5 transition-colors cursor-pointer shadow-md shadow-purple-500/10"
              >
                {submitting ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <UserPlus className="w-3.5 h-3.5" />
                )}
                Register Client
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  );
}
