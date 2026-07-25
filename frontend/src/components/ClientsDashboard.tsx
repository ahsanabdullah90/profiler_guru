'use client';

import React, { useEffect, useState, useCallback, useRef } from 'react';
import { useContactsStore } from '../store/contactsStore';
import { useStatusStore } from '../store/statusStore';
import { getApiBase, type Contact } from '../store/api';
import { Search, Users, ChevronLeft, ChevronRight, GitMerge, MoreHorizontal, UserPlus } from 'lucide-react';
import EmptyState from './ui/EmptyState';
import { ContactListSkeleton } from './ui/Skeleton';
import ClientProfileEditor from './ClientProfileEditor';
import PlatformBadge from './PlatformBadge';
import MergeModal from './MergeModal';
import MergeSuggestionBanner from './MergeSuggestionBanner';
import CreateClientModal from './CreateClientModal';

const GRADIENTS = [
  'linear-gradient(135deg, #FF5E62 0%, #FF9966 100%)',
  'linear-gradient(135deg, #EF4D7B 0%, #C82B57 100%)',
  'linear-gradient(135deg, #11998E 0%, #38EF7D 100%)',
  'linear-gradient(135deg, #7F00FF 0%, #E100FF 100%)',
  'linear-gradient(135deg, #00C6FF 0%, #0072FF 100%)',
  'linear-gradient(135deg, #F12711 0%, #F5AF19 100%)',
  'linear-gradient(135deg, #8E2DE2 0%, #4A00E0 100%)',
];

function getAvatarGradient(name: string) {
  const idx = name.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0) % GRADIENTS.length;
  return GRADIENTS[idx];
}

export default function ClientsDashboard() {
  const contacts = useContactsStore(s => s.contacts);
  const contactTotal = useContactsStore(s => s.contactTotal);
  const contactPage = useContactsStore(s => s.contactPage);
  const contactPages = useContactsStore(s => s.contactPages);
  const fetchContacts = useContactsStore(s => s.fetchContacts);
  const appOnline = useStatusStore(s => s.status.app_online);

  const [search, setSearch] = useState('');
  const [editingContact, setEditingContact] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<'recent' | 'volume' | 'alpha'>('alpha');
  const [platformFilter, setPlatformFilter] = useState<string>('');
  const [mergingContact, setMergingContact] = useState<Contact | null>(null);
  const [openMenu, setOpenMenu] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const SORT_MAP: Record<string, string> = { recent: 'last_date', volume: 'msg_count', alpha: 'name' };
  const SORT_LABELS: Record<string, string> = { recent: 'Recent Activity', volume: 'Msg Volume', alpha: 'Name' };

  const isLoading = contacts.length === 0 && appOnline && !search;

  useEffect(() => {
    if (appOnline) {
      fetchContacts({ page: 1, limit: 200, search, sort: SORT_MAP[sortBy] ?? 'name', platform: platformFilter || undefined });
    }
  }, [appOnline, fetchContacts, search, sortBy, platformFilter]);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpenMenu(null);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const handlePageChange = useCallback((page: number) => {
    fetchContacts({ page, limit: 200, search, sort: SORT_MAP[sortBy] ?? 'name' });
  }, [fetchContacts, search, sortBy, SORT_MAP]);

  const handleSearch = useCallback((value: string) => {
    setSearch(value);
    fetchContacts({ page: 1, limit: 200, search: value, sort: SORT_MAP[sortBy] ?? 'name' });
  }, [fetchContacts, sortBy, SORT_MAP]);

  const displayName = (c: typeof contacts[0]) => c.display_name || c.name;
  const contactHasProfile = (c: typeof contacts[0]) => c.display_name || c.email || c.mobile || c.whatsapp;

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="p-5 border-b border-[var(--border-subtle)] bg-[var(--bg-surface-raised)] shrink-0">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-outfit font-bold text-base text-[var(--text-primary)] flex items-center gap-2">
            <Users className="w-4 h-4 text-primary" /> Clients Directory
          </h2>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-3 py-1.5 bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-strong)] text-white text-xs font-semibold rounded-lg flex items-center gap-1.5 cursor-pointer transition-colors shadow-md shadow-purple-500/10"
            >
              <UserPlus className="w-3.5 h-3.5" />
              New Client
            </button>
            <span className="text-[10px] text-[var(--text-muted)] font-mono">
              {contactTotal} contact{contactTotal !== 1 ? 's' : ''}
            </span>
          </div>
        </div>

        {/* Platform filter chips */}
        <div className="flex items-center gap-1.5 mb-3">
          {[
            { key: '', label: 'All' },
            { key: 'instagram', label: 'Instagram', color: '#E1306C' },
            { key: 'whatsapp', label: 'WhatsApp', color: '#25D366' },
          ].map((chip) => (
            <button
              key={chip.key}
              onClick={() => setPlatformFilter(chip.key)}
              className={`px-2.5 py-1 rounded-lg text-[10px] font-bold transition-all ${
                platformFilter === chip.key
                  ? 'bg-[var(--brand-primary-soft)] border border-[var(--brand-primary)] text-primary'
                  : 'bg-[var(--bg-surface)] border border-[var(--border-glass)] text-[var(--text-muted)] hover:text-[var(--text-primary)]'
              }`}
            >
              {chip.label}
            </button>
          ))}
        </div>

        <div className="flex gap-2.5">
          <div className="flex-1 relative">
            <Search className="w-4 h-4 text-[var(--text-muted)] absolute left-3 top-2.5" />
            <input
              type="text"
              value={search}
              onChange={(e) => handleSearch(e.target.value)}
              placeholder="Search clients by name, handle, or email..."
              className="w-full pl-9 pr-4 py-2 bg-[var(--bg-surface)] border border-[var(--border-glass)] rounded-lg text-xs text-[var(--text-primary)] outline-none focus:border-primary transition-all"
            />
          </div>
          {/* eslint-disable-next-line jsx-a11y/no-onchange */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as 'recent' | 'volume' | 'alpha')}
            className="px-3 py-2 bg-[var(--bg-surface-inset)] border border-[var(--border-glass)] rounded-lg text-xs text-[var(--text-secondary)] outline-none focus:border-primary transition-colors cursor-pointer"
            aria-label="Sort clients"
          >
            <option value="recent">Sort: Recent Activity</option>
            <option value="volume">Sort: Msg Volume</option>
            <option value="alpha">Sort: Name</option>
          </select>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-5 scrollbar-thin scrollbar-thumb-[var(--border-subtle)]">
        {/* Merge suggestions banner */}
        <MergeSuggestionBanner onMerged={() => fetchContacts({ page: 1, limit: 200, search, sort: SORT_MAP[sortBy] ?? 'name', platform: platformFilter || undefined })} />

        {isLoading ? (
          <ContactListSkeleton rows={12} />
        ) : contacts.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
            {contacts.map((contact) => (
              <div key={contact.name} className="relative group/card">
                <button
                  onClick={() => setEditingContact(contact.name)}
                  className="w-full p-4 rounded-xl border border-[var(--border-glass)] bg-[var(--bg-surface)] hover:bg-[var(--bg-surface-raised)] hover:border-[var(--brand-primary)] transition-all duration-200 text-left cursor-pointer"
                >
                  <div className="flex items-center gap-3">
                    {/* Avatar */}
                    <div
                      className="w-10 h-10 rounded-full flex items-center justify-center text-xs font-bold text-white shrink-0 shadow-md overflow-hidden"
                      style={{ background: getAvatarGradient(contact.name) }}
                    >
                      {contact.photo_url ? (
                        <img
                          src={`${getApiBase().replace('/api/v1', '')}${contact.photo_url}`}
                          alt=""
                          role="presentation"
                          className="w-full h-full object-cover"
                          onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                        />
                      ) : (
                        displayName(contact).slice(0, 2).toUpperCase()
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <h4 className="text-xs font-semibold text-[var(--text-primary)] truncate group-hover/card:text-[var(--brand-primary)] transition-colors">
                          {displayName(contact)}
                        </h4>
                        <PlatformBadge platforms={contact.platforms || []} size="xs" />
                        {contact.source === 'manual' && (
                          <span className="px-1.5 py-0.5 rounded text-[8px] font-bold bg-purple-500/10 text-purple-400 border border-purple-500/20 shrink-0">
                            Manual
                          </span>
                        )}
                      </div>
                      {contact.instagram_handle && (
                        <p className="text-[10px] text-[var(--text-muted)] truncate">
                          @{contact.instagram_handle}
                        </p>
                      )}
                      <div className="flex items-center gap-2 mt-1 flex-wrap">
                        {contact.email && (
                          <span className="text-[9px] text-[var(--text-secondary)] truncate max-w-[120px]">
                            {contact.email}
                          </span>
                        )}
                        {contact.mobile && (
                          <span className="text-[9px] text-[var(--text-muted)]">{contact.mobile}</span>
                        )}
                      </div>
                    </div>
                  </div>
                  {!contactHasProfile(contact) && (
                    <div className="mt-2 text-[9px] text-amber-400/70 font-semibold">
                      + Add details
                    </div>
                  )}
                </button>

                {/* Three-dot menu */}
                <div className="absolute top-2 right-2 opacity-0 group-hover/card:opacity-100 transition-opacity z-10">
                  <button
                    onClick={(e) => { e.stopPropagation(); setOpenMenu(openMenu === contact.name ? null : contact.name); }}
                    className="w-7 h-7 rounded-lg flex items-center justify-center bg-[var(--bg-surface)] border border-[var(--border-glass)] hover:bg-[var(--bg-surface-raised)] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
                  >
                    <MoreHorizontal className="w-3.5 h-3.5" />
                  </button>
                  {openMenu === contact.name && (
                    <div
                      ref={menuRef}
                      className="absolute right-0 top-8 w-40 bg-[var(--bg-surface-raised)] border border-[var(--border-subtle)] rounded-lg shadow-xl z-20 py-1"
                    >
                      <button
                        onClick={(e) => { e.stopPropagation(); setMergingContact(contact); setOpenMenu(null); }}
                        className="w-full flex items-center gap-2 px-3 py-2 text-[11px] text-[var(--text-primary)] hover:bg-[var(--bg-surface)] transition-colors"
                      >
                        <GitMerge className="w-3.5 h-3.5" />
                        Merge with...
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState
            icon={<Users className="w-5 h-5" />}
            title={search ? 'No clients match your search' : 'No contacts imported yet'}
            description={
              search
                ? `Nothing matches "${search}". Try a different name or clear search.`
                : 'Import Instagram data first to populate the directory, then add client details.'
            }
          />
        )}
      </div>

      {/* Pagination */}
      {contactPages > 1 && (
        <div className="border-t border-[var(--border-glass)] bg-[var(--bg-surface-raised)] px-5 py-3 shrink-0 flex items-center justify-between text-[11px] font-semibold text-[var(--text-muted)]">
          <button
            onClick={() => handlePageChange(Math.max(contactPage - 1, 1))}
            disabled={contactPage <= 1}
            className="px-2.5 py-1 rounded bg-[var(--bg-surface)] border border-[var(--border-strong)] hover:bg-[var(--bg-surface-raised)] disabled:opacity-30 disabled:pointer-events-none text-[var(--text-primary)] transition-colors flex items-center gap-1"
          >
            <ChevronLeft className="w-3 h-3" /> Prev
          </button>
          <span>
            Page <strong className="text-[var(--text-primary)] font-mono">{contactPage}</strong> of {contactPages}
          </span>
          <button
            onClick={() => handlePageChange(Math.min(contactPage + 1, contactPages))}
            disabled={contactPage >= contactPages}
            className="px-2.5 py-1 rounded bg-[var(--bg-surface)] border border-[var(--border-strong)] hover:bg-[var(--bg-surface-raised)] disabled:opacity-30 disabled:pointer-events-none text-[var(--text-primary)] transition-colors flex items-center gap-1"
          >
            Next <ChevronRight className="w-3 h-3" />
          </button>
        </div>
      )}

      {/* Slide-in Editor Panel */}
      {editingContact && (
        <ClientProfileEditor
          contactName={editingContact}
          onClose={() => setEditingContact(null)}
          onSaved={() => {
            fetchContacts({ page: 1, limit: 200, search, sort: SORT_MAP[sortBy] ?? 'name', platform: platformFilter || undefined });
          }}
        />
      )}

      {/* Merge Modal */}
      {mergingContact && (
        <MergeModal
          primary={mergingContact}
          allContacts={contacts}
          onClose={() => setMergingContact(null)}
          onMerged={() => {
            setMergingContact(null);
            fetchContacts({ page: 1, limit: 200, search, sort: SORT_MAP[sortBy] ?? 'name', platform: platformFilter || undefined });
          }}
        />
      )}

      {/* Create Client Modal */}
      {showCreateModal && (
        <CreateClientModal
          onClose={() => setShowCreateModal(false)}
          onCreated={(chatName) => {
            setShowCreateModal(false);
            setEditingContact(chatName);
          }}
        />
      )}
    </div>
  );
}
