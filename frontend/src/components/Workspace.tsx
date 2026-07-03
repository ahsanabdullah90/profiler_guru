'use client';

import React, { useState, useEffect, useRef, useMemo } from 'react';
import dynamic from 'next/dynamic';
import { useContactsStore } from '../store/contactsStore';
import { useStatusStore } from '../store/statusStore';
import { useDebouncedCallback } from '../lib/useDebounce';
import { useNavigationStore } from '../store/navigationStore';
import {
  Search, ArrowLeft, MessageSquare, BarChart3, Calendar, Database,
} from 'lucide-react';
import EmptyState from './ui/EmptyState';
import { ContactListSkeleton, MessageThreadSkeleton } from './ui/Skeleton';

const LazyWorkspaceAnalytics = dynamic(
  () => import('./WorkspaceAnalytics'),
  { ssr: false },
);

const GRADIENTS = [
  'linear-gradient(135deg, #FF5E62 0%, #FF9966 100%)',
  'linear-gradient(135deg, #EF4D7B 0%, #C82B57 100%)',
  'linear-gradient(135deg, #11998E 0%, #38EF7D 100%)',
  'linear-gradient(135deg, #7F00FF 0%, #E100FF 100%)',
  'linear-gradient(135deg, #00C6FF 0%, #0072FF 100%)',
  'linear-gradient(135deg, #F12711 0%, #F5AF19 100%)',
  'linear-gradient(135deg, #8E2DE2 0%, #4A00E0 100%)',
];

const SELECTED_GRADIENT = 'linear-gradient(135deg, #7963FF 0%, #5E5CE6 100%)';

function getAvatarGradient(name: string, isSelected: boolean) {
  if (isSelected) return SELECTED_GRADIENT;
  const idx = name.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0) % GRADIENTS.length;
  return GRADIENTS[idx];
}

const ContactCard = React.memo(function ContactCard({ 
  contact, isSelected, onSelect 
}: { 
  contact: { name: string; msg_count: number; last_date: string; avg_msg: number; depth_label: string; depth_color: string };
  isSelected: boolean;
  onSelect: (name: string) => void;
}) {
  const initials = contact.name.slice(0, 2).toUpperCase();
  return (
    <button
      onClick={() => onSelect(contact.name)}
      className={`p-3 rounded-xl transition-all duration-200 border text-left w-full ${
        isSelected
          ? 'glass-card-active'
          : 'glass-card'
      }`}
    >
      <div className="flex items-center gap-3">
        <div 
          className="w-9 h-9 rounded-lg flex items-center justify-center text-[11px] font-bold text-white shrink-0 shadow-md"
          style={{ background: getAvatarGradient(contact.name, isSelected) }}
        >
          {initials}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-semibold text-white truncate">{contact.name}</h4>
            <span className="text-[9px] font-mono text-zinc-500 shrink-0 ml-2">{contact.msg_count}</span>
          </div>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-[10px] truncate text-zinc-400">{contact.last_date}</span>
            <span 
              className="text-[9px] font-bold px-1.5 py-0.5 rounded-full shrink-0"
              style={{ color: contact.depth_color, backgroundColor: `${contact.depth_color}15` }}
            >
              {contact.depth_label.split(' ')[0]}
            </span>
          </div>
        </div>
      </div>
    </button>
  );
});

const MessageBubble = React.memo(function MessageBubble({ 
  msg, audioBase 
}: { 
  msg: { id: string; sender: string; time: string; text: string; audio_url: string | null; is_self: boolean };
  audioBase: string;
}) {
  return (
    <div className={`flex ${msg.is_self ? 'justify-end' : 'justify-start'} mb-3`}>
      <div className={`max-w-[80%] p-3 rounded-2xl ${
        msg.is_self 
          ? 'bg-[rgba(121,99,255,0.12)] border border-[rgba(121,99,255,0.15)] rounded-br-sm' 
          : 'bg-[rgba(255,255,255,0.03)] border border-[var(--border-glass)] rounded-bl-sm'
      }`}>
        {!msg.is_self && (
          <p className="text-[10px] font-bold text-accent-cyan mb-1">{msg.sender}</p>
        )}
        <p className="text-[11px] text-zinc-200 leading-relaxed whitespace-pre-wrap">{msg.text}</p>
        {msg.audio_url ? (
          <audio
            controls
            preload="none"
            aria-label={`Voice message from ${msg.sender}`}
            className="mt-2 w-full h-8"
          >
            <source src={`${audioBase}/${msg.audio_url}`} />
            {/* Empty track satisfies jsx-a11y/media-has-caption; voice memos
                do not have captions, the transcript appears in the chat. */}
            <track kind="captions" />
          </audio>
        ) : null}
        <p className="text-[9px] text-zinc-600 mt-1 text-right font-mono">{msg.time}</p>
      </div>
    </div>
  );
});

export default function Workspace() {
  const contacts = useContactsStore(s => s.contacts);
  const selectedContact = useContactsStore(s => s.selectedContact);
  const selectedMonth = useContactsStore(s => s.selectedMonth);
  const availableMonths = useContactsStore(s => s.availableMonths);
  const messages = useContactsStore(s => s.messages);
  const analytics = useContactsStore(s => s.analytics);
  const activeTab = useContactsStore(s => s.activeTab);
  const status = useStatusStore(s => s.status);
  const contactTotal = useContactsStore(s => s.contactTotal);
  const contactPage = useContactsStore(s => s.contactPage);
  const contactPages = useContactsStore(s => s.contactPages);
  const setSelectedContact = useContactsStore(s => s.setSelectedContact);
  const setSelectedMonth = useContactsStore(s => s.setSelectedMonth);
  const setActiveTab = useContactsStore(s => s.setActiveTab);
  const fetchContacts = useContactsStore(s => s.fetchContacts);
  const setActiveSection = useNavigationStore(s => s.setActiveSection);

  const [sortBy, setSortBy] = useState<'recent' | 'volume' | 'alpha'>('recent');
  const [chatSearch, setChatSearch] = useState('');
  const [contactSearch, setContactSearch] = useState('');

  const chatEndRef = useRef<HTMLDivElement>(null);

  const appOnline = status.app_online;
  const isLoadingContacts = contacts.length === 0 && appOnline && !contactSearch;
  useEffect(() => {
    if (appOnline) {
      fetchContacts({ page: 1, limit: 50, search: contactSearch });
    }
  }, [appOnline, fetchContacts, contactSearch]);

  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  const handleContactSearch = useDebouncedCallback((value: string) => {
    setContactSearch(value);
    fetchContacts({ page: 1, limit: 50, search: value });
  }, 300);

  const filteredMessages = useMemo(() => 
    messages.filter(m => !chatSearch || m.text.toLowerCase().includes(chatSearch.toLowerCase())),
    [messages, chatSearch]
  );

  const audioBase = useMemo(() =>
    typeof window === 'undefined' ? '' : `http://${window.location.hostname}:8000/static/audio`,
  []);

  return (
    <div className="w-full h-full flex flex-col overflow-hidden">
      
      {/* ==================== STATE A: CONTACTS HUB ==================== */}
      {!selectedContact ? (
        <div className="flex-1 flex flex-col p-5 overflow-hidden">
          
          {/* Contacts Search & Sort Bar */}
          <div className="flex flex-col gap-3 mb-4 shrink-0">
            <h2 className="font-outfit font-bold text-base text-white flex items-center gap-2">
              <Database className="w-4 h-4 text-primary" /> DMs Contacts Hub
            </h2>
            
            <div className="flex gap-2.5">
              {/* Fuzzy Search Box */}
              <div className="flex-1 relative">
                <Search className="w-4 h-4 text-zinc-500 absolute left-3 top-2.5" />
                <input 
                  type="text"
                  value={contactSearch}
                  onChange={(e) => handleContactSearch(e.target.value)}
                  placeholder="Search contacts..."
                  className="w-full pl-9 pr-4 py-2 bg-[rgba(255,255,255,0.01)] border border-[var(--border-glass)] rounded-lg text-xs text-white outline-none focus:border-primary transition-all"
                />
              </div>
              
              {/* Sort Dropdown */}
              {/* eslint-disable-next-line jsx-a11y/no-onchange -- <select> requires onChange */}
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as 'recent' | 'volume' | 'alpha')}
                className="px-3 py-2 bg-[rgba(10,10,12,0.6)] border border-[var(--border-glass)] rounded-lg text-xs text-zinc-300 outline-none focus:border-primary transition-colors cursor-pointer"
                aria-label="Sort contacts"
              >
                <option value="recent">Sort: Recent Activity</option>
                <option value="volume">Sort: Msg Volume</option>
                <option value="alpha">Sort: Alphabetical</option>
              </select>
            </div>
          </div>

          {/* Contacts List Grid (Independent Scroll) */}
          <div className="flex-1 overflow-y-auto pr-1 space-y-1.5 scrollbar-thin scrollbar-thumb-zinc-800">
            {isLoadingContacts ? (
              <ContactListSkeleton rows={6} />
            ) : contacts.length > 0 ? (
              contacts.map((contact) => (
                <ContactCard
                  key={contact.name}
                  contact={contact}
                  isSelected={selectedContact === contact.name}
                  onSelect={setSelectedContact}
                />
              ))
            ) : (
              <EmptyState
                icon={<Database className="w-5 h-5" />}
                title={contactSearch ? 'No contacts match your search' : 'No DMs imported yet'}
                description={
                  contactSearch
                    ? `Nothing matches "${contactSearch}". Try a different name or clear the search.`
                    : 'Import an Instagram or Facebook data export to populate this list.'
                }
                action={
                  contactSearch
                    ? undefined
                    : { label: 'Import DMs', onClick: () => setActiveSection('import') }
                }
              />
            )}
          </div>

          {/* Pagination Controls */}
          {contactPages > 1 && (
            <div className="mt-4 pt-3 border-t border-[var(--border-glass)] shrink-0 flex items-center justify-between text-[11px] font-semibold text-zinc-500">
              <button 
                onClick={() => fetchContacts({ page: Math.max(contactPage - 1, 1), limit: 50, search: contactSearch })}
                disabled={contactPage <= 1}
                className="px-2.5 py-1 rounded bg-zinc-900 border border-zinc-700 hover:bg-zinc-800 disabled:opacity-30 disabled:pointer-events-none text-white transition-colors"
                aria-label="Previous page"
              >
                ◀ Prev
              </button>
              <span>
                Page <strong className="text-white font-mono">{contactPage}</strong> of {contactPages} ({contactTotal} contacts)
              </span>
              <button 
                onClick={() => fetchContacts({ page: Math.min(contactPage + 1, contactPages), limit: 50, search: contactSearch })}
                disabled={contactPage >= contactPages}
                className="px-2.5 py-1 rounded bg-zinc-900 border border-zinc-700 hover:bg-zinc-800 disabled:opacity-30 disabled:pointer-events-none text-white transition-colors"
                aria-label="Next page"
              >
                Next ▶
              </button>
            </div>
          )}

        </div>
      ) : (
        
        /* ==================== STATE B: SELECTED CONTACT WORKSPACE ==================== */
        <div className="flex-1 flex flex-col overflow-hidden">
          
          {/* Header Controls (Exit and Title) */}
          <div className="p-4 border-b border-zinc-800 bg-zinc-900 shrink-0 flex items-center justify-between">
            <button 
              onClick={() => setSelectedContact(null)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-primary/30 bg-primary/15 text-xs font-bold text-white hover:bg-primary/25 hover:border-primary/50 transition-all cursor-pointer"
            >
              <ArrowLeft className="w-3.5 h-3.5" /> Exit Chat
            </button>

            <div className="flex items-center gap-2">
              <div 
                className="w-6.5 h-6.5 rounded-full flex items-center justify-center font-bold text-white text-[10px]"
                style={{ background: getAvatarGradient(selectedContact, false) }}
              >
                {selectedContact.slice(0, 2).toUpperCase()}
              </div>
              <h2 className="text-xs font-bold text-white max-w-[120px] truncate">{selectedContact}</h2>
            </div>

            {/* Dashboard Tabs Toggle */}
            <div className="flex p-0.5 bg-zinc-950 border border-zinc-900 rounded-lg shrink-0">
              <button 
                onClick={() => setActiveTab('chat')}
                className={`px-3 py-1 rounded-md text-[10px] font-bold flex items-center gap-1.5 transition-colors cursor-pointer ${
                  activeTab === 'chat' ? 'bg-primary text-white' : 'text-zinc-400 hover:text-zinc-200'
                }`}
              >
                <MessageSquare className="w-3 h-3" /> Chats
              </button>
              <button 
                onClick={() => setActiveTab('analytics')}
                className={`px-3 py-1 rounded-md text-[10px] font-bold flex items-center gap-1.5 transition-colors cursor-pointer ${
                  activeTab === 'analytics' ? 'bg-primary text-white' : 'text-zinc-400 hover:text-zinc-200'
                }`}
              >
                <BarChart3 className="w-3 h-3" /> Metrics
              </button>
            </div>
          </div>

          {/* Tab content wrapper — both views always rendered, hidden via display:none */}
          <div className="flex-1 overflow-hidden flex flex-col">
            
            {/* -------------------- VIEW 1: CHAT VIEWER (always mounted) -------------------- */}
            <div
              className="flex-1 flex flex-col overflow-hidden"
              style={{ display: activeTab === 'chat' ? 'flex' : 'none' }}
            >
                
                {/* Horizontal Monthly Tabs Selector */}
                {availableMonths.length > 0 && (
                  <div className="p-3 border-b border-[var(--border-glass)] bg-[rgba(10,10,12,0.1)] shrink-0 flex items-center gap-2 overflow-x-auto scrollbar-none">
                    <Calendar className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
                    <div className="flex gap-1.5">
                      {availableMonths.map((m) => (
                        <button
                          key={m}
                          onClick={() => setSelectedMonth(m)}
                          className={`px-2.5 py-1 rounded-md text-[10px] font-bold tracking-wide transition-all shrink-0 cursor-pointer ${
                            selectedMonth === m 
                              ? 'bg-[rgba(121,99,255,0.12)] border border-[rgba(121,99,255,0.3)] text-primary glow-primary' 
                              : 'bg-[rgba(255,255,255,0.01)] border border-[var(--border-glass)] text-zinc-400 hover:text-white'
                          }`}
                        >
                          {m.replace('.md', '')}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Search within month */}
                <div className="px-4 py-2 border-b border-[var(--border-glass)] bg-[rgba(10,10,12,0.05)] shrink-0 relative">
                  <Search className="w-3.5 h-3.5 text-zinc-500 absolute left-7 top-4" />
                  <input 
                    type="text"
                    value={chatSearch}
                    onChange={(e) => setChatSearch(e.target.value)}
                    placeholder="Search in this month's messages..."
                    className="w-full pl-9 pr-4 py-1.5 bg-[rgba(255,255,255,0.01)] border border-[var(--border-glass)] rounded-lg text-[11px] text-white outline-none focus:border-primary transition-colors"
                  />
                </div>

                {/* Messages Thread (Scrollable) */}
                <div className="flex-1 overflow-y-auto p-4 space-y-3.5 scrollbar-thin scrollbar-thumb-zinc-800">
                  {messages.length === 0 && selectedMonth ? (
                    <MessageThreadSkeleton rows={5} />
                  ) : filteredMessages.length > 0 ? (
                    filteredMessages.map((msg) => (
                      <MessageBubble key={msg.id} msg={msg} audioBase={audioBase} />
                    ))
                  ) : (
                    <EmptyState
                      icon={<MessageSquare className="w-5 h-5" />}
                      title={chatSearch ? 'No messages match' : 'Empty conversation'}
                      description={
                        chatSearch
                          ? `Nothing in this log matches "${chatSearch}".`
                          : 'This contact has no messages in the selected month.'
                      }
                    />
                  )}
                  <div ref={chatEndRef} />
                </div>

            </div>

            {/* -------------------- VIEW 2: CONNECTION ANALYTICS (lazy-loaded, kept mounted once loaded) -------------------- */}
            {analytics ? (
              <div style={{ display: activeTab === 'analytics' ? 'flex' : 'none', flex: '1 1 0%' }} className="overflow-hidden flex-col">
                <LazyWorkspaceAnalytics
                  analytics={analytics}
                  selectedContact={selectedContact}
                />
              </div>
            ) : null}

          </div>

        </div>
      )}

    </div>
  );
}
