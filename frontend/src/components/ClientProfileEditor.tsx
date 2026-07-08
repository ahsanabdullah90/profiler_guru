'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useContactsStore, type ClientProfile } from '../store/contactsStore';
import { useStatusStore } from '../store/statusStore';
import { getApiBase } from '../store/api';
import { X, Save, Camera, Trash2, Loader2, User } from 'lucide-react';

interface Props {
  contactName: string;
  onClose: () => void;
  onSaved?: () => void;
}

export default function ClientProfileEditor({ contactName, onClose, onSaved }: Props) {
  const fetchClientProfile = useContactsStore(s => s.fetchClientProfile);
  const updateClientProfile = useContactsStore(s => s.updateClientProfile);
  const uploadClientPhoto = useContactsStore(s => s.uploadClientPhoto);
  const deleteClientPhoto = useContactsStore(s => s.deleteClientPhoto);
  const pushError = useStatusStore(s => s.pushError);

  const [profile, setProfile] = useState<ClientProfile>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [photoUploading, setPhotoUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  const photoBaseUrl = getApiBase().replace('/api/v1', '');
  const displayName = profile.display_name || contactName;
  const initials = displayName.slice(0, 2).toUpperCase();

  useEffect(() => {
    const load = async () => {
      try {
        const data = await fetchClientProfile(contactName);
        setProfile(data || {});
      } catch (err) {
        const e = err as Error;
        pushError(`Failed to load profile: ${e.message}`, 'error');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [contactName, fetchClientProfile, pushError]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateClientProfile(contactName, {
        display_name: profile.display_name || null,
        email: profile.email || null,
        mobile: profile.mobile || null,
        whatsapp: profile.whatsapp || null,
        instagram_handle: profile.instagram_handle || null,
      });
      pushError('Client profile saved', 'info');
      onSaved?.();
    } catch (err) {
      const e = err as Error;
      pushError(`Failed to save: ${e.message}`, 'error');
    } finally {
      setSaving(false);
    }
  };

  const handlePhotoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setPhotoUploading(true);
    try {
      const photoUrl = await uploadClientPhoto(contactName, file);
      if (photoUrl) {
        setProfile(prev => ({ ...prev, photo_url: photoUrl }));
      }
    } catch (err) {
      const error = err as Error;
      pushError(`Photo upload failed: ${error.message}`, 'error');
    } finally {
      setPhotoUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDeletePhoto = async () => {
    try {
      await deleteClientPhoto(contactName);
      setProfile(prev => ({ ...prev, photo_url: null }));
    } catch (err) {
      const e = err as Error;
      pushError(`Failed to delete photo: ${e.message}`, 'error');
    }
  };

  const updateField = (field: keyof ClientProfile, value: string) => {
    setProfile(prev => ({ ...prev, [field]: value || null }));
  };

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 bg-black/40 z-30"
        onClick={onClose}
      />

      {/* Slide-in Panel */}
      <div
        ref={panelRef}
        className="fixed right-0 top-0 h-full w-full max-w-md bg-[var(--bg-surface-raised)] border-l border-[var(--border-subtle)] shadow-2xl z-40 flex flex-col overflow-hidden animate-in slide-in-from-right duration-300"
      >
        {/* Header */}
        <div className="px-5 py-4 border-b border-[var(--border-subtle)] flex items-center justify-between shrink-0">
          <h3 className="text-sm font-bold text-[var(--text-primary)]">Edit Client</h3>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface)] transition-colors"
            aria-label="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        {loading ? (
          <div className="flex-1 flex items-center justify-center">
            <Loader2 className="w-5 h-5 text-[var(--brand-primary)] animate-spin" />
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto p-5 space-y-6 scrollbar-thin scrollbar-thumb-[var(--border-subtle)]">
            {/* Photo Section */}
            <div className="flex flex-col items-center gap-3">
              <div
                className="w-24 h-24 rounded-full flex items-center justify-center text-2xl font-bold text-white shadow-lg overflow-hidden relative"
                style={{ background: 'linear-gradient(135deg, var(--brand-primary) 0%, var(--brand-primary-strong) 100%)' }}
              >
                {profile.photo_url ? (
                  <img
                    src={`${photoBaseUrl}${profile.photo_url}`}
                    alt={`${displayName}'s photo`}
                    role="presentation"
                    className="w-full h-full object-cover"
                    onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                  />
                ) : (
                  initials
                )}
                {photoUploading && (
                  <div className="absolute inset-0 bg-black/50 flex items-center justify-center rounded-full">
                    <Loader2 className="w-6 h-6 text-white animate-spin" />
                  </div>
                )}
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={photoUploading}
                  className="px-3 py-1.5 rounded-lg border border-[var(--border-glass)] bg-[var(--bg-surface)] hover:bg-[var(--bg-surface-inset)] text-[10px] font-semibold text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors flex items-center gap-1.5 disabled:opacity-50"
                >
                  <Camera className="w-3 h-3" />
                  Upload Photo
                </button>
                {profile.photo_url && (
                  <button
                    onClick={handleDeletePhoto}
                    className="px-3 py-1.5 rounded-lg border border-[var(--error)]/30 bg-[var(--error)]/10 hover:bg-[var(--error)]/20 text-[10px] font-semibold text-[var(--error)] transition-colors flex items-center gap-1.5"
                  >
                    <Trash2 className="w-3 h-3" />
                    Remove
                  </button>
                )}
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                className="hidden"
                onChange={handlePhotoUpload}
              />
            </div>

            {/* Form Fields */}
            <div className="space-y-4">
              <Field label="Display Name" value={profile.display_name || ''} onChange={(v) => updateField('display_name', v)} placeholder="e.g. Sarah Connor" />
              <Field label="Instagram Handle" value={profile.instagram_handle || ''} onChange={(v) => updateField('instagram_handle', v)} placeholder="e.g. @sarah_connor" prefix="@" />
              <Field label="Email" value={profile.email || ''} onChange={(v) => updateField('email', v)} placeholder="e.g. sarah@example.com" type="email" />
              <Field label="Mobile" value={profile.mobile || ''} onChange={(v) => updateField('mobile', v)} placeholder="e.g. +1 555-0123" type="tel" />
              <Field label="WhatsApp" value={profile.whatsapp || ''} onChange={(v) => updateField('whatsapp', v)} placeholder="e.g. +1 555-0123" type="tel" />
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="px-5 py-4 border-t border-[var(--border-subtle)] shrink-0 flex gap-2">
          <button
            onClick={onClose}
            className="flex-1 py-2 rounded-lg border border-[var(--border-glass)] text-[11px] font-bold text-[var(--text-secondary)] hover:bg-[var(--bg-surface)] transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving || loading}
            className="flex-1 py-2 rounded-lg bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-strong)] disabled:opacity-50 text-white text-[11px] font-bold transition-colors flex items-center justify-center gap-1.5"
          >
            {saving ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Save className="w-3.5 h-3.5" />
            )}
            Save
          </button>
        </div>
      </div>
    </>
  );
}

function Field({
  label,
  value,
  onChange,
  placeholder,
  prefix,
  type = 'text',
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  prefix?: string;
  type?: string;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-[10px] uppercase tracking-wider font-bold text-[var(--text-muted)]">
        {label}
      </label>
      <div className="flex items-center gap-1">
        {prefix && (
          <span className="text-xs text-[var(--text-muted)] font-mono">{prefix}</span>
        )}
        <input
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="w-full px-3 py-2 bg-[var(--bg-surface)] border border-[var(--border-glass)] rounded-lg text-xs text-[var(--text-primary)] outline-none focus:border-[var(--brand-primary)] transition-colors placeholder:text-[var(--text-muted)]/50"
        />
      </div>
    </div>
  );
}
