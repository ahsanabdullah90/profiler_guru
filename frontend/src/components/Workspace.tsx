'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useSyncStore, getApiBase } from '../store/useSyncStore';
import { 
  Search, ArrowLeft, MessageSquare, BarChart3, 
  Volume2, Download, Calendar, Activity, Database
} from 'lucide-react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, 
  Tooltip, ResponsiveContainer
} from 'recharts';

export default function Workspace() {
  const {
    contacts,
    selectedContact,
    selectedMonth,
    availableMonths,
    messages,
    analytics,
    activeTab,
    searchQuery,
    status,
    setSelectedContact,
    setSelectedMonth,
    setActiveTab,
    setSearchQuery,
    fetchContacts
  } = useSyncStore();

  const [sortBy, setSortBy] = useState<'recent' | 'volume' | 'alpha'>('recent');
  const [currentPage, setCurrentPage] = useState(1);
  const [chatSearch, setChatSearch] = useState('');
  const [exportFormat, setExportFormat] = useState<'csv' | 'json'>('csv');
  
  const chatEndRef = useRef<HTMLDivElement>(null);
  const CONTACTS_PER_PAGE = 25;

  // Fetch contacts when backend is confirmed online.
  // Using status.app_online (set by the StatusBar WebSocket) as the trigger
  // ensures this fires as soon as the backend is ready — even if the frontend
  // loaded before the backend finished booting. Also auto-recovers if the
  // backend restarts mid-session.
  useEffect(() => {
    if (status.app_online) {
      fetchContacts();
    }
  }, [status.app_online, fetchContacts]);

  // Scroll chat thread to bottom when messages or month changes
  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  // Handle contact search and sorting
  const filteredContacts = contacts.filter(c => 
    c.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const sortedContacts = [...filteredContacts].sort((a, b) => {
    if (sortBy === 'alpha') {
      return a.name.localeCompare(b.name);
    } else if (sortBy === 'volume') {
      return b.avg_msg - a.avg_msg;
    } else {
      // Recent activity (latest date -> oldest)
      const dateA = a.last_date === 'Never' || !a.last_date ? '0000-00-00' : a.last_date;
      const dateB = b.last_date === 'Never' || !b.last_date ? '0000-00-00' : b.last_date;
      return dateB.localeCompare(dateA);
    }
  });

  // Paginated contacts
  const totalContacts = sortedContacts.length;
  const totalPages = Math.ceil(totalContacts / CONTACTS_PER_PAGE) || 1;
  const paginatedContacts = sortedContacts.slice(
    (currentPage - 1) * CONTACTS_PER_PAGE,
    currentPage * CONTACTS_PER_PAGE
  );

  // Generate initials gradient for avatars
  const getAvatarGradient = (name: string, isSelected: boolean) => {
    if (isSelected) {
      return 'linear-gradient(135deg, #7963FF 0%, #5E5CE6 100%)';
    }
    const gradients = [
      'linear-gradient(135deg, #FF5E62 0%, #FF9966 100%)',
      'linear-gradient(135deg, #EF4D7B 0%, #C82B57 100%)',
      'linear-gradient(135deg, #11998E 0%, #38EF7D 100%)',
      'linear-gradient(135deg, #7F00FF 0%, #E100FF 100%)',
      'linear-gradient(135deg, #00C6FF 0%, #0072FF 100%)',
      'linear-gradient(135deg, #F12711 0%, #F5AF19 100%)',
      'linear-gradient(135deg, #8E2DE2 0%, #4A00E0 100%)',
    ];
    const idx = name.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0) % gradients.length;
    return gradients[idx];
  };

  // Filter messages inside selected monthly log
  const filteredMessages = messages.filter(m => 
    !chatSearch || m.text.toLowerCase().includes(chatSearch.toLowerCase())
  );

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
                  value={searchQuery}
                  onChange={(e) => { setSearchQuery(e.target.value); setCurrentPage(1); }}
                  placeholder="Search 843+ contacts..."
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
            {paginatedContacts.length > 0 ? (
              paginatedContacts.map((contact) => {
                const initials = contact.name.slice(0, 2).toUpperCase();
                const isSelected = selectedContact === contact.name;
                const isRagComplete = contact.rag_progress === 100;
                
                return (
                  <div 
                    key={contact.name}
                    onClick={() => setSelectedContact(contact.name)}
                    className="p-3.5 glass-card flex flex-col cursor-pointer transition-all duration-200"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-3">
                        {/* Avatar initials with gradients */}
                        <div 
                          className="w-8 h-8 rounded-full flex items-center justify-center font-bold text-white text-xs font-outfit shrink-0 shadow-inner"
                          style={{ background: getAvatarGradient(contact.name, isSelected) }}
                        >
                          {initials}
                        </div>
                        <span className="text-xs font-bold text-white font-sans truncate max-w-[150px]">
                          {contact.name}
                        </span>
                      </div>
                      <span className="text-[10px] text-zinc-500 font-mono">
                        {contact.last_date}
                      </span>
                    </div>

                    <div className="flex justify-between items-center gap-5 mt-1">
                      <span className="text-[11px] text-zinc-400 truncate flex-1 font-sans">
                        {contact.last_snippet}
                      </span>
                      <span className="text-[10px] bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.05)] text-zinc-300 px-2 py-0.5 rounded-full font-bold">
                        {contact.msg_count} msgs
                      </span>
                    </div>

                    <div className="flex justify-between items-center mt-3 pt-2 border-t border-[rgba(255,255,255,0.03)]">
                      {/* Connection Depth badge */}
                      <span 
                        className="text-[9px] font-bold px-2 py-0.5 rounded border"
                        style={{ 
                          color: contact.depth_color, 
                          borderColor: `${contact.depth_color}30`, 
                          background: `${contact.depth_color}08` 
                        }}
                      >
                        {contact.depth_label} ({contact.avg_msg.toFixed(1)}/d)
                      </span>
                      
                      {/* RAG Progress badge */}
                      <span 
                        className={`text-[9px] font-bold px-2 py-0.5 rounded border flex items-center gap-1 ${
                          isRagComplete 
                            ? 'text-primary bg-primary/5 border-primary/15' 
                            : 'text-warning bg-warning/5 border-warning/15'
                        }`}
                      >
                        🤖 RAG {contact.rag_progress}%
                      </span>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="h-40 flex items-center justify-center text-xs text-zinc-500 italic">
                No DMs contacts found.
              </div>
            )}
          </div>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="mt-4 pt-3 border-t border-[var(--border-glass)] shrink-0 flex items-center justify-between text-[11px] font-semibold text-zinc-500">
              <button 
                onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                disabled={currentPage === 1}
                className="px-2.5 py-1 bg-[rgba(255,255,255,0.02)] border border-[var(--border-glass)] rounded hover:bg-[rgba(255,255,255,0.05)] disabled:opacity-30 disabled:pointer-events-none text-white transition-colors"
              >
                ◀ Prev
              </button>
              <span>
                Page <strong className="text-white font-mono">{currentPage}</strong> of {totalPages}
              </span>
              <button 
                onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                disabled={currentPage === totalPages}
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
                    filteredMessages.map((msg) => {
                      return (
                        <div 
                          key={msg.id}
                          className={`flex flex-col max-w-[80%] ${msg.is_self ? 'ml-auto items-end' : 'mr-auto items-start'}`}
                        >
                          {/* Chat bubble */}
                          <div 
                            className={`p-3 rounded-xl border flex flex-col shadow-lg relative ${
                              msg.is_self 
                                ? 'bg-[rgba(121,99,255,0.06)] border-[rgba(121,99,255,0.2)] rounded-tr-sm' 
                                : 'bg-[rgba(255,255,255,0.02)] border-[var(--border-glass)] rounded-tl-sm'
                            }`}
                          >
                            {/* Header */}
                            <div className="flex justify-between items-center gap-10 mb-1.5">
                              <strong 
                                className={`text-[10px] font-bold ${
                                  msg.is_self ? 'text-primary' : 'text-success'
                                }`}
                              >
                                {msg.sender}
                              </strong>
                              <span className="text-[9px] text-zinc-500 font-mono">{msg.time}</span>
                            </div>
                            
                            {/* Body text */}
                            <div className="text-xs text-zinc-200 leading-relaxed whitespace-pre-wrap font-sans">
                              {msg.text}
                            </div>

                            {/* Voice message player static stream */}
                            {msg.audio_url && (
                              <div className="mt-3 w-full max-w-[240px] p-2 rounded-lg bg-[rgba(0,0,0,0.2)] border border-[var(--border-glass)] flex flex-col gap-2">
                                <div className="flex items-center gap-2 text-[10px] font-bold text-zinc-300">
                                  <Volume2 className="w-3.5 h-3.5 text-warning" /> Voice message audio
                                </div>
                                <audio 
                                  controls 
                                  src={`${getApiBase()}${msg.audio_url}`} 
                                  className="w-full h-8 accent-primary opacity-80 mt-1"
                                />
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })
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
