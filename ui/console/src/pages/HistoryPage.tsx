import { useState, useEffect } from 'react';
import {
  History,
  MessageSquare,
  Clock,
  Trash2,
  Play,
  Search,
  Calendar,
  Bot,
  User,
  ChevronRight,
  RefreshCw,
  FileText,
  Loader2
} from 'lucide-react';

interface Conversation {
  id: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  preview: string;
  last_query?: string;
  last_response?: string;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
}

const API_BASE = 'http://localhost:8000/api/v1';

export default function HistoryPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedConversation, setSelectedConversation] = useState<string | null>(null);
  const [conversationMessages, setConversationMessages] = useState<Message[]>([]);
  const [loadingMessages, setLoadingMessages] = useState(false);

  useEffect(() => {
    fetchConversations();
  }, []);

  const fetchConversations = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/rag/conversations`);
      const data = await res.json();
      setConversations(data.conversations || []);
    } catch (error) {
      console.error('Failed to fetch conversations:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchConversationMessages = async (conversationId: string) => {
    setLoadingMessages(true);
    try {
      const res = await fetch(`${API_BASE}/rag/conversation/${conversationId}`);
      const data = await res.json();
      setConversationMessages(data.messages || []);
    } catch (error) {
      console.error('Failed to fetch messages:', error);
      setConversationMessages([]);
    } finally {
      setLoadingMessages(false);
    }
  };

  const deleteConversation = async (conversationId: string) => {
    if (!confirm('Are you sure you want to delete this conversation?')) return;
    
    try {
      await fetch(`${API_BASE}/rag/conversation/${conversationId}`, { method: 'DELETE' });
      setConversations(prev => prev.filter(c => c.id !== conversationId));
      if (selectedConversation === conversationId) {
        setSelectedConversation(null);
        setConversationMessages([]);
      }
    } catch (error) {
      console.error('Failed to delete conversation:', error);
    }
  };

  const handleSelectConversation = (conversationId: string) => {
    setSelectedConversation(conversationId);
    fetchConversationMessages(conversationId);
  };

  const resumeConversation = (conversationId: string) => {
    // Store conversation ID and redirect to chat
    localStorage.setItem('resume_conversation', conversationId);
    window.location.href = '/#chat';
  };

  const filteredConversations = conversations.filter(c => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      c.preview?.toLowerCase().includes(query) ||
      c.last_query?.toLowerCase().includes(query) ||
      c.id.toLowerCase().includes(query)
    );
  });

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    
    if (days === 0) {
      return `Today at ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    } else if (days === 1) {
      return `Yesterday at ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    } else if (days < 7) {
      return `${days} days ago`;
    } else {
      return date.toLocaleDateString();
    }
  };

  return (
    <>
      <header className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 className="page-title">Chat History</h1>
            <p className="page-subtitle">Browse and resume past conversations</p>
          </div>
          <button className="btn btn-secondary" onClick={fetchConversations}>
            <RefreshCw size={18} />
            Refresh
          </button>
        </div>
      </header>

      <div className="page-content">
        <div style={{ display: 'grid', gridTemplateColumns: '380px 1fr', gap: 24, height: 'calc(100vh - 180px)' }}>
          {/* Conversation List */}
          <div className="card" style={{ overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            {/* Search */}
            <div style={{ padding: 16, borderBottom: '1px solid var(--border-color)' }}>
              <div style={{ position: 'relative' }}>
                <Search size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                <input
                  type="text"
                  placeholder="Search conversations..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{ paddingLeft: 36, width: '100%' }}
                />
              </div>
            </div>

            {/* List */}
            <div style={{ flex: 1, overflow: 'auto', padding: 8 }}>
              {loading ? (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 60 }}>
                  <Loader2 size={24} className="spin" />
                </div>
              ) : filteredConversations.length === 0 ? (
                <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>
                  <History size={48} style={{ opacity: 0.3, marginBottom: 16 }} />
                  <p>No conversations yet</p>
                  <p style={{ fontSize: 13 }}>Start chatting to see your history here</p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {filteredConversations.map(conv => (
                    <div
                      key={conv.id}
                      onClick={() => handleSelectConversation(conv.id)}
                      style={{
                        padding: 14,
                        background: selectedConversation === conv.id ? 'rgba(0, 212, 255, 0.1)' : 'var(--bg-tertiary)',
                        borderRadius: 'var(--radius-md)',
                        cursor: 'pointer',
                        border: selectedConversation === conv.id ? '1px solid var(--accent-primary)' : '1px solid transparent',
                        transition: 'all 0.15s ease'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 8 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <MessageSquare size={16} color="var(--accent-primary)" />
                          <span style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                            {conv.id.slice(0, 12)}...
                          </span>
                        </div>
                        <button
                          onClick={(e) => { e.stopPropagation(); deleteConversation(conv.id); }}
                          style={{ padding: 4, background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}
                          title="Delete conversation"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                      
                      <p style={{ 
                        fontSize: 13, 
                        color: 'var(--text-primary)', 
                        margin: 0,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap'
                      }}>
                        {conv.preview || conv.last_query || 'Empty conversation'}
                      </p>
                      
                      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 8, fontSize: 11, color: 'var(--text-muted)' }}>
                        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                          <Clock size={10} />
                          {formatDate(conv.updated_at || conv.created_at)}
                        </span>
                        <span>
                          {conv.message_count || 0} messages
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Conversation Detail */}
          <div className="card" style={{ overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            {selectedConversation ? (
              <>
                <div style={{ 
                  padding: '16px 20px', 
                  borderBottom: '1px solid var(--border-color)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}>
                  <div>
                    <h3 style={{ margin: 0, marginBottom: 4 }}>Conversation</h3>
                    <span style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                      {selectedConversation}
                    </span>
                  </div>
                  <button
                    className="btn btn-primary"
                    onClick={() => resumeConversation(selectedConversation)}
                  >
                    <Play size={16} />
                    Resume Chat
                  </button>
                </div>

                <div style={{ flex: 1, overflow: 'auto', padding: 20 }}>
                  {loadingMessages ? (
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 60 }}>
                      <Loader2 size={24} className="spin" />
                    </div>
                  ) : conversationMessages.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>
                      <FileText size={48} style={{ opacity: 0.3, marginBottom: 16 }} />
                      <p>No messages in this conversation</p>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                      {conversationMessages.map((msg, idx) => (
                        <div
                          key={idx}
                          style={{
                            display: 'flex',
                            gap: 12,
                            padding: 16,
                            background: msg.role === 'user' ? 'rgba(124, 58, 237, 0.1)' : 'var(--bg-tertiary)',
                            borderRadius: 'var(--radius-md)',
                            borderLeft: `3px solid ${msg.role === 'user' ? '#7c3aed' : 'var(--accent-primary)'}`
                          }}
                        >
                          <div style={{
                            width: 32,
                            height: 32,
                            borderRadius: '50%',
                            background: msg.role === 'user' ? 'rgba(124, 58, 237, 0.2)' : 'var(--bg-hover)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            flexShrink: 0
                          }}>
                            {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
                          </div>
                          <div style={{ flex: 1 }}>
                            <div style={{ 
                              fontSize: 11, 
                              color: msg.role === 'user' ? '#7c3aed' : 'var(--accent-primary)',
                              marginBottom: 4,
                              textTransform: 'uppercase',
                              fontWeight: 600
                            }}>
                              {msg.role}
                            </div>
                            <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
                              {msg.content}
                            </div>
                            {msg.timestamp && (
                              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 8 }}>
                                {new Date(msg.timestamp).toLocaleString()}
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div style={{ 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center', 
                flex: 1, 
                color: 'var(--text-muted)',
                textAlign: 'center',
                padding: 40
              }}>
                <div>
                  <ChevronRight size={48} style={{ opacity: 0.3, marginBottom: 16 }} />
                  <p>Select a conversation to view</p>
                  <p style={{ fontSize: 13 }}>Or start a new chat</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .spin {
          animation: spin 1s linear infinite;
        }
      `}</style>
    </>
  );
}

