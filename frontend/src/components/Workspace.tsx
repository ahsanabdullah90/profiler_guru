'use client';

import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { useContactsStore } from '../store/contactsStore';
import { useStatusStore } from '../store/statusStore';
import { getApiBase } from '../store/api';
import { 
  Search, ArrowLeft, MessageSquare, BarChart3, 
  Volume2, Download, Calendar, Activity, Database
} from 'lucide-react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, 
  Tooltip, ResponsiveContainer
} from 'recharts';

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
        {msg.audio_url && (
          <audio controls preload="none" className="mt-2 w-full h-8">
            <source src={`${audioBase}/${msg.audio_url}`} />
          </audio>
        )}
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

  const [sortBy, setSortBy] = useState<'recent' | 'volume' | 'alpha'>('recent');
  const [chatSearch, setChatSearch] = useState('');
  const [exportFormat, setExportFormat] = useState<'csv' | 'json'>('csv');
  const [contactSearch, setContactSearch] = useState('');
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const chatEndRef = useRef<HTMLDivElement>(null);

  const appOnline = status.app_online;
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

  const handleContactSearch = useCallback((value: string) => {
    setContactSearch(value);
    if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current);
    searchTimeoutRef.current = setTimeout(() => {
      fetchContacts({ page: 1, limit: 50, search: value });
    }, 300);
  }, [fetchContacts]);

  const filteredMessages = useMemo(() => 
    messages.filter(m => !chatSearch || m.text.toLowerCase().includes(chatSearch.toLowerCase())),
    [messages, chatSearch]
  );

  const audioBase = typeof window === 'undefined' ? '' : `http://${window.location.hostname}:8000/static/audio`;

  // Handle connection export
  const handleExport = () => {
    if (!selectedContact) return;
    // Download via simple file download or API trigger
    const url = `${getApiBase()}/contacts/${selectedContact}/export?format=${exportFormat}`;
    window.open(url, '_blank');
  };

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
              <select 
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as 'recent' | 'volume' | 'alpha')}
                className="px-3 py-2 bg-[rgba(10,10,12,0.6)] border border-[var(--border-glass)] rounded-lg text-xs text-zinc-300 outline-none focus:border-primary transition-colors cursor-pointer"
              >
                <option value="recent">Sort: Recent Activity</option>
                <option value="volume">Sort: Msg Volume</option>
                <option value="alpha">Sort: Alphabetical</option>
              </select>
            </div>
          </div>

          {/* Contacts List Grid (Independent Scroll) */}
          <div className="flex-1 overflow-y-auto pr-1 space-y-1.5 scrollbar-thin scrollbar-thumb-zinc-800">
            {contacts.length > 0 ? (
              contacts.map((contact) => (
                <ContactCard 
                  key={contact.name} 
                  contact={contact} 
                  isSelected={selectedContact === contact.name}
                  onSelect={setSelectedContact}
                />
              ))
            ) : (
              <div className="h-40 flex items-center justify-center text-xs text-zinc-500 italic">
                No DMs contacts found.
              </div>
            )}
          </div>

          {/* Pagination Controls */}
          {contactPages > 1 && (
            <div className="mt-4 pt-3 border-t border-[var(--border-glass)] shrink-0 flex items-center justify-between text-[11px] font-semibold text-zinc-500">
              <button 
                onClick={() => fetchContacts({ page: Math.max(contactPage - 1, 1), limit: 50, search: contactSearch })}
                disabled={contactPage <= 1}
                className="px-2.5 py-1 bg-[rgba(255,255,255,0.02)] border border-[var(--border-glass)] rounded hover:bg-[rgba(255,255,255,0.05)] disabled:opacity-30 disabled:pointer-events-none text-white transition-colors"
              >
                ◀ Prev
              </button>
              <span>
                Page <strong className="text-white font-mono">{contactPage}</strong> of {contactPages} ({contactTotal} contacts)
              </span>
              <button 
                onClick={() => fetchContacts({ page: Math.min(contactPage + 1, contactPages), limit: 50, search: contactSearch })}
                disabled={contactPage >= contactPages}
                className="px-2.5 py-1 bg-[rgba(255,255,255,0.02)] border border-[var(--border-glass)] rounded hover:bg-[rgba(255,255,255,0.05)] disabled:opacity-30 disabled:pointer-events-none text-white transition-colors"
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
          <div className="p-4 border-b border-[var(--border-glass)] bg-[rgba(10,10,12,0.2)] shrink-0 flex items-center justify-between">
            <button 
              onClick={() => setSelectedContact(null)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[var(--border-glass)] bg-[rgba(255,255,255,0.01)] text-xs font-bold text-white hover:bg-[rgba(255,255,255,0.04)] hover:border-zinc-700 transition-all cursor-pointer"
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
                  activeTab === 'chat' ? 'bg-primary text-white' : 'text-zinc-500 hover:text-zinc-300'
                }`}
              >
                <MessageSquare className="w-3 h-3" /> Chats
              </button>
              <button 
                onClick={() => setActiveTab('analytics')}
                className={`px-3 py-1 rounded-md text-[10px] font-bold flex items-center gap-1.5 transition-colors cursor-pointer ${
                  activeTab === 'analytics' ? 'bg-primary text-white' : 'text-zinc-500 hover:text-zinc-300'
                }`}
              >
                <BarChart3 className="w-3 h-3" /> Metrics
              </button>
            </div>
          </div>

          {/* Tab content wrapper */}
          <div className="flex-1 overflow-hidden flex flex-col">
            
            {/* -------------------- VIEW 1: CHAT VIEWER -------------------- */}
            {activeTab === 'chat' && (
              <div className="flex-1 flex flex-col overflow-hidden">
                
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
                  {filteredMessages.length > 0 ? (
                    filteredMessages.map((msg) => (
                      <MessageBubble key={msg.id} msg={msg} audioBase={audioBase} />
                    ))
                  ) : (
                    <div className="h-40 flex items-center justify-center text-xs text-zinc-500 italic">
                      No messages found in this log.
                    </div>
                  )}
                  <div ref={chatEndRef} />
                </div>

              </div>
            )}

            {/* -------------------- VIEW 2: CONNECTION ANALYTICS -------------------- */}
            {activeTab === 'analytics' && analytics && (
              <div className="flex-1 overflow-y-auto p-5 space-y-5 scrollbar-thin scrollbar-thumb-zinc-800 font-sans">
                
                {/* Connection Metrics Cards Grid */}
                <div className="grid grid-cols-3 gap-3">
                  <div className="p-3 bg-[rgba(255,255,255,0.015)] border border-[var(--border-glass)] rounded-lg text-center flex flex-col justify-center">
                    <span className="text-[9px] uppercase tracking-wider text-zinc-500 font-bold">Connection Status</span>
                    <strong 
                      className="text-xs font-bold mt-2.5 truncate"
                      style={{ color: analytics.depth_color }}
                    >
                      {analytics.depth_label}
                    </strong>
                  </div>

                  <div className="p-3 bg-[rgba(255,255,255,0.015)] border border-[var(--border-glass)] rounded-lg text-center flex flex-col justify-center">
                    <span className="text-[9px] uppercase tracking-wider text-zinc-500 font-bold">Weekly Daily Avg</span>
                    <strong className="text-lg font-bold mt-1.5 text-primary font-mono">
                      {analytics.avg_msg_weekly.toFixed(2)}
                    </strong>
                  </div>

                  <div className="p-3 bg-[rgba(255,255,255,0.015)] border border-[var(--border-glass)] rounded-lg text-center flex flex-col justify-center">
                    <span className="text-[9px] uppercase tracking-wider text-zinc-500 font-bold">Monthly Daily Avg</span>
                    <strong className="text-lg font-bold mt-1.5 text-success font-mono">
                      {analytics.avg_msg_monthly.toFixed(2)}
                    </strong>
                  </div>
                </div>

                {/* 14-Day activity Recharts Line Chart */}
                {analytics.timeline.length > 0 ? (
                  <div className="p-4 bg-[rgba(255,255,255,0.01)] border border-[var(--border-glass)] rounded-lg">
                    <h3 className="text-xs font-bold text-white mb-3.5 flex items-center gap-2">
                      <Activity className="w-4 h-4 text-primary" /> 14-Day Messaging Activity
                    </h3>
                    <div className="h-44 w-full text-[10px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={analytics.timeline}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#1c1c20" />
                          <XAxis dataKey="date" stroke="#6b6b75" />
                          <YAxis stroke="#6b6b75" />
                          <Tooltip 
                            contentStyle={{ 
                              background: '#131314', 
                              borderColor: 'rgba(255,255,255,0.08)',
                              borderRadius: '8px',
                              color: '#fff'
                            }} 
                          />
                          <Line 
                            type="monotone" 
                            dataKey="messages" 
                            stroke="#7963FF" 
                            strokeWidth={2}
                            dot={{ r: 3, fill: '#7963FF', strokeWidth: 0 }}
                            activeDot={{ r: 5 }}
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                ) : (
                  <div className="p-6 bg-[rgba(255,255,255,0.01)] border border-[var(--border-glass)] rounded-lg text-center text-xs text-zinc-500 italic">
                    No daily metrics activity recorded yet.
                  </div>
                )}

                {/* Audio voice metrics */}
                <div className="p-4 bg-[rgba(255,255,255,0.01)] border border-[var(--border-glass)] rounded-lg">
                  <h3 className="text-xs font-bold text-white mb-3 flex items-center gap-2">
                    <Volume2 className="w-4 h-4 text-warning" /> Voice Messaging Ratio
                  </h3>
                  
                  <div className="flex items-center justify-between gap-10">
                    <div className="flex flex-col">
                      <span className="text-[10px] text-zinc-400">Voice Clips Ingested:</span>
                      <strong className="text-base font-bold text-white mt-0.5 font-mono">{analytics.audio_count} clips</strong>
                    </div>
                    <div className="flex flex-col text-right">
                      <span className="text-[10px] text-zinc-400">Percentage of DMs:</span>
                      <strong className="text-base font-bold text-warning mt-0.5 font-mono">{analytics.audio_ratio}%</strong>
                    </div>
                  </div>
                  
                  {/* Progress bar ratio */}
                  <div className="w-full h-1.5 bg-zinc-900 rounded-full mt-3 overflow-hidden">
                    <div 
                      className="h-full bg-warning rounded-full"
                      style={{ width: `${Math.min(100, analytics.audio_ratio)}%` }}
                    />
                  </div>
                </div>

                {/* Export Panel */}
                <div className="p-4 bg-[rgba(255,255,255,0.01)] border border-[var(--border-glass)] rounded-lg flex flex-col gap-3">
                  <div>
                    <h3 className="text-xs font-bold text-white flex items-center gap-2">
                      <Download className="w-4 h-4 text-success" /> Export Metrics Data
                    </h3>
                    <p className="text-[10px] text-zinc-500 mt-1">Download the SQLite connection metrics in standard CSV or JSON format.</p>
                  </div>

                  <div className="flex items-center justify-between mt-1">
                    <div className="flex p-0.5 bg-zinc-950 border border-zinc-900 rounded-lg">
                      <button 
                        onClick={() => setExportFormat('csv')}
                        className={`px-3 py-1 rounded text-[10px] font-bold transition-colors ${
                          exportFormat === 'csv' ? 'bg-primary text-white' : 'text-zinc-500 hover:text-zinc-300'
                        }`}
                      >
                        CSV
                      </button>
                      <button 
                        onClick={() => setExportFormat('json')}
                        className={`px-3 py-1 rounded text-[10px] font-bold transition-colors ${
                          exportFormat === 'json' ? 'bg-primary text-white' : 'text-zinc-500 hover:text-zinc-300'
                        }`}
                      >
                        JSON
                      </button>
                    </div>

                    <button 
                      onClick={handleExport}
                      className="px-4 py-1.5 bg-success hover:bg-success/90 text-black font-bold text-[10px] rounded-lg transition-colors flex items-center gap-1.5 cursor-pointer"
                    >
                      <Download className="w-3.5 h-3.5" /> Download Export
                    </button>
                  </div>
                </div>

              </div>
            )}

          </div>

        </div>
      )}

    </div>
  );
}
