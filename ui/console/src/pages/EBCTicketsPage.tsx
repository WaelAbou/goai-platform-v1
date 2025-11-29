import { useState, useEffect } from 'react';
import {
  Ticket,
  Send,
  AlertTriangle,
  CheckCircle,
  Clock,
  TrendingUp,
  TrendingDown,
  Minus,
  RefreshCw,
  Filter,
  Loader2,
  AlertCircle,
  MessageSquare,
  User,
  Mail,
  Phone,
  Sparkles,
  BarChart3
} from 'lucide-react';
import { useToast } from '../components/Toast';

interface TicketAnalysis {
  ticket_id: string;
  sentiment: string;
  sentiment_score: number;
  priority: string;
  category: string;
  keywords: string[];
  urgency_indicators: string[];
  suggested_response?: string;
  estimated_resolution_time?: string;
  escalation_needed: boolean;
}

interface StoredTicket {
  id: string;
  customer_name?: string;
  subject: string;
  content: string;
  channel: string;
  status: string;
  sentiment: string;
  sentiment_score: number;
  priority: string;
  category: string;
  created_at: string;
  escalation_needed: number;
}

interface Analytics {
  total_tickets: number;
  by_sentiment: Record<string, number>;
  by_priority: Record<string, number>;
  by_category: Record<string, number>;
  average_sentiment_score: number;
  open_tickets: number;
  resolved_tickets: number;
  escalation_rate: number;
}

const API_BASE = 'http://localhost:8000/api/v1';

const PRIORITY_CONFIG: Record<string, { color: string; bg: string }> = {
  critical: { color: '#ef4444', bg: 'rgba(239, 68, 68, 0.15)' },
  high: { color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.15)' },
  medium: { color: '#00d4ff', bg: 'rgba(0, 212, 255, 0.15)' },
  low: { color: '#10b981', bg: 'rgba(16, 185, 129, 0.15)' }
};

const SENTIMENT_CONFIG: Record<string, { color: string; icon: React.ReactNode }> = {
  positive: { color: '#10b981', icon: <TrendingUp size={16} /> },
  negative: { color: '#ef4444', icon: <TrendingDown size={16} /> },
  neutral: { color: '#64748b', icon: <Minus size={16} /> },
  mixed: { color: '#f59e0b', icon: <AlertCircle size={16} /> }
};

const CHANNEL_ICONS: Record<string, React.ReactNode> = {
  email: <Mail size={14} />,
  chat: <MessageSquare size={14} />,
  phone: <Phone size={14} />
};

export default function EBCTicketsPage() {
  const [activeTab, setActiveTab] = useState<'analyze' | 'tickets' | 'dashboard'>('analyze');
  
  // Analyze state
  const [subject, setSubject] = useState('');
  const [content, setContent] = useState('');
  const [customerName, setCustomerName] = useState('');
  const [channel, setChannel] = useState('email');
  const [analyzing, setAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState<TicketAnalysis | null>(null);
  
  // Tickets state
  const [tickets, setTickets] = useState<StoredTicket[]>([]);
  const [ticketsLoading, setTicketsLoading] = useState(false);
  const [filterPriority, setFilterPriority] = useState<string>('');
  const [filterSentiment, setFilterSentiment] = useState<string>('');
  
  // Dashboard state
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  
  const toast = useToast();

  useEffect(() => {
    if (activeTab === 'tickets') fetchTickets();
    if (activeTab === 'dashboard') fetchAnalytics();
  }, [activeTab]);

  const analyzeTicket = async () => {
    if (!content.trim()) return;
    
    setAnalyzing(true);
    setAnalysis(null);
    
    try {
      const res = await fetch(`${API_BASE}/ebc-tickets/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          subject,
          content,
          customer_name: customerName,
          channel,
          use_llm: true,
          save_ticket: true
        })
      });
      
      const data = await res.json();
      setAnalysis(data);
      toast.success('Ticket analyzed and saved!');
    } catch (error) {
      toast.error('Analysis failed');
    } finally {
      setAnalyzing(false);
    }
  };

  const fetchTickets = async () => {
    setTicketsLoading(true);
    try {
      const params = new URLSearchParams();
      if (filterPriority) params.append('priority', filterPriority);
      if (filterSentiment) params.append('sentiment', filterSentiment);
      
      const res = await fetch(`${API_BASE}/ebc-tickets/tickets?${params}`);
      const data = await res.json();
      setTickets(data.tickets || []);
    } catch (error) {
      toast.error('Failed to load tickets');
    } finally {
      setTicketsLoading(false);
    }
  };

  const fetchAnalytics = async () => {
    try {
      const res = await fetch(`${API_BASE}/ebc-tickets/analytics`);
      const data = await res.json();
      setAnalytics(data);
    } catch (error) {
      toast.error('Failed to load analytics');
    }
  };

  const seedDemoData = async () => {
    try {
      const res = await fetch(`${API_BASE}/ebc-tickets/demo/seed`, { method: 'POST' });
      const data = await res.json();
      toast.success(data.message);
      fetchTickets();
      fetchAnalytics();
    } catch (error) {
      toast.error('Failed to seed data');
    }
  };

  return (
    <>
      <header className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 className="page-title">EBC Ticket Analysis</h1>
            <p className="page-subtitle">AI-powered sentiment analysis for customer support</p>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            {(['analyze', 'tickets', 'dashboard'] as const).map(tab => (
              <button
                key={tab}
                className={`btn btn-sm ${activeTab === tab ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setActiveTab(tab)}
              >
                {tab === 'analyze' && <Sparkles size={16} />}
                {tab === 'tickets' && <Ticket size={16} />}
                {tab === 'dashboard' && <BarChart3 size={16} />}
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </div>
        </div>
      </header>

      <div className="page-content">
        {/* ANALYZE TAB */}
        {activeTab === 'analyze' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 400px', gap: 24 }}>
            {/* Input Form */}
            <div className="card">
              <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-color)' }}>
                <h3 style={{ margin: 0 }}>Analyze Ticket</h3>
              </div>
              <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                  <div>
                    <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>Customer Name</label>
                    <input
                      value={customerName}
                      onChange={(e) => setCustomerName(e.target.value)}
                      placeholder="John Smith"
                      style={{ width: '100%' }}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>Channel</label>
                    <select value={channel} onChange={(e) => setChannel(e.target.value)} style={{ width: '100%' }}>
                      <option value="email">Email</option>
                      <option value="chat">Chat</option>
                      <option value="phone">Phone</option>
                    </select>
                  </div>
                </div>
                
                <div>
                  <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>Subject</label>
                  <input
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                    placeholder="URGENT: Cannot access my account"
                    style={{ width: '100%' }}
                  />
                </div>
                
                <div>
                  <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>Ticket Content *</label>
                  <textarea
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    placeholder="Paste the customer's message here..."
                    style={{ width: '100%', minHeight: 150 }}
                  />
                </div>
                
                <button
                  className="btn btn-primary"
                  onClick={analyzeTicket}
                  disabled={analyzing || !content.trim()}
                >
                  {analyzing ? (
                    <>
                      <Loader2 size={16} className="spin" />
                      Analyzing...
                    </>
                  ) : (
                    <>
                      <Send size={16} />
                      Analyze Ticket
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Analysis Results */}
            <div className="card">
              <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-color)' }}>
                <h3 style={{ margin: 0 }}>Analysis Results</h3>
              </div>
              <div style={{ padding: 20 }}>
                {analysis ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                    {/* Sentiment */}
                    <div style={{
                      padding: 16,
                      background: `${SENTIMENT_CONFIG[analysis.sentiment]?.color}15`,
                      borderRadius: 'var(--radius-md)',
                      borderLeft: `4px solid ${SENTIMENT_CONFIG[analysis.sentiment]?.color}`
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                        <span style={{ color: SENTIMENT_CONFIG[analysis.sentiment]?.color }}>
                          {SENTIMENT_CONFIG[analysis.sentiment]?.icon}
                        </span>
                        <span style={{ fontWeight: 600, textTransform: 'capitalize' }}>
                          {analysis.sentiment} Sentiment
                        </span>
                      </div>
                      <div style={{ fontSize: 24, fontWeight: 700 }}>
                        {(analysis.sentiment_score * 100).toFixed(0)}%
                      </div>
                    </div>

                    {/* Priority & Category */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                      <div style={{
                        padding: 12,
                        background: PRIORITY_CONFIG[analysis.priority]?.bg,
                        borderRadius: 'var(--radius-sm)',
                        textAlign: 'center'
                      }}>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>PRIORITY</div>
                        <div style={{ 
                          fontWeight: 700, 
                          textTransform: 'uppercase',
                          color: PRIORITY_CONFIG[analysis.priority]?.color
                        }}>
                          {analysis.priority}
                        </div>
                      </div>
                      <div style={{
                        padding: 12,
                        background: 'var(--bg-tertiary)',
                        borderRadius: 'var(--radius-sm)',
                        textAlign: 'center'
                      }}>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>CATEGORY</div>
                        <div style={{ fontWeight: 600, textTransform: 'capitalize' }}>
                          {analysis.category}
                        </div>
                      </div>
                    </div>

                    {/* Escalation Alert */}
                    {analysis.escalation_needed && (
                      <div style={{
                        padding: 12,
                        background: 'rgba(239, 68, 68, 0.15)',
                        border: '1px solid #ef4444',
                        borderRadius: 'var(--radius-sm)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 8,
                        color: '#ef4444'
                      }}>
                        <AlertTriangle size={18} />
                        <span style={{ fontWeight: 600 }}>Escalation Recommended</span>
                      </div>
                    )}

                    {/* Urgency Indicators */}
                    {analysis.urgency_indicators.length > 0 && (
                      <div>
                        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>
                          Urgency Indicators
                        </div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                          {analysis.urgency_indicators.map((ind, i) => (
                            <span key={i} style={{
                              padding: '4px 8px',
                              background: 'rgba(245, 158, 11, 0.15)',
                              color: '#f59e0b',
                              borderRadius: 4,
                              fontSize: 12
                            }}>
                              {ind}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Suggested Response */}
                    {analysis.suggested_response && (
                      <div>
                        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>
                          Suggested Response
                        </div>
                        <div style={{
                          padding: 12,
                          background: 'var(--bg-tertiary)',
                          borderRadius: 'var(--radius-sm)',
                          fontSize: 13,
                          lineHeight: 1.6
                        }}>
                          {analysis.suggested_response}
                        </div>
                      </div>
                    )}

                    {/* Resolution Time */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text-muted)', fontSize: 13 }}>
                      <Clock size={14} />
                      Est. Resolution: {analysis.estimated_resolution_time}
                    </div>
                  </div>
                ) : (
                  <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
                    <Ticket size={48} style={{ opacity: 0.3, marginBottom: 16 }} />
                    <p>Enter ticket content and click Analyze</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* TICKETS TAB */}
        {activeTab === 'tickets' && (
          <div className="card">
            <div style={{ 
              padding: '16px 20px', 
              borderBottom: '1px solid var(--border-color)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <h3 style={{ margin: 0 }}>Recent Tickets</h3>
              <div style={{ display: 'flex', gap: 8 }}>
                <select 
                  value={filterPriority} 
                  onChange={(e) => { setFilterPriority(e.target.value); }}
                  style={{ padding: '6px 12px', fontSize: 13 }}
                >
                  <option value="">All Priorities</option>
                  <option value="critical">Critical</option>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
                <select 
                  value={filterSentiment} 
                  onChange={(e) => { setFilterSentiment(e.target.value); }}
                  style={{ padding: '6px 12px', fontSize: 13 }}
                >
                  <option value="">All Sentiments</option>
                  <option value="negative">Negative</option>
                  <option value="positive">Positive</option>
                  <option value="neutral">Neutral</option>
                </select>
                <button className="btn btn-sm btn-secondary" onClick={fetchTickets}>
                  <RefreshCw size={14} />
                </button>
                <button className="btn btn-sm btn-primary" onClick={seedDemoData}>
                  <Sparkles size={14} />
                  Seed Demo
                </button>
              </div>
            </div>
            <div style={{ padding: 16 }}>
              {ticketsLoading ? (
                <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}>
                  <Loader2 size={24} className="spin" />
                </div>
              ) : tickets.length === 0 ? (
                <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
                  <Ticket size={48} style={{ opacity: 0.3, marginBottom: 16 }} />
                  <p>No tickets yet. Click "Seed Demo" to create sample data.</p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {tickets.map(ticket => (
                    <div
                      key={ticket.id}
                      style={{
                        padding: 16,
                        background: 'var(--bg-tertiary)',
                        borderRadius: 'var(--radius-md)',
                        borderLeft: `4px solid ${PRIORITY_CONFIG[ticket.priority]?.color || '#64748b'}`
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, marginBottom: 4 }}>{ticket.subject || 'No Subject'}</div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: 'var(--text-muted)' }}>
                            {ticket.customer_name && (
                              <>
                                <User size={12} />
                                {ticket.customer_name}
                              </>
                            )}
                            {CHANNEL_ICONS[ticket.channel]}
                            {ticket.channel}
                          </div>
                        </div>
                        <div style={{ display: 'flex', gap: 8 }}>
                          <span style={{
                            padding: '4px 8px',
                            borderRadius: 4,
                            fontSize: 11,
                            fontWeight: 600,
                            textTransform: 'uppercase',
                            background: PRIORITY_CONFIG[ticket.priority]?.bg,
                            color: PRIORITY_CONFIG[ticket.priority]?.color
                          }}>
                            {ticket.priority}
                          </span>
                          <span style={{
                            padding: '4px 8px',
                            borderRadius: 4,
                            fontSize: 11,
                            fontWeight: 600,
                            background: `${SENTIMENT_CONFIG[ticket.sentiment]?.color}20`,
                            color: SENTIMENT_CONFIG[ticket.sentiment]?.color,
                            display: 'flex',
                            alignItems: 'center',
                            gap: 4
                          }}>
                            {SENTIMENT_CONFIG[ticket.sentiment]?.icon}
                            {ticket.sentiment}
                          </span>
                        </div>
                      </div>
                      <p style={{ margin: 0, fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                        {ticket.content?.slice(0, 200)}...
                      </p>
                      {ticket.escalation_needed === 1 && (
                        <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 6, color: '#ef4444', fontSize: 12 }}>
                          <AlertTriangle size={14} />
                          Escalation needed
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* DASHBOARD TAB */}
        {activeTab === 'dashboard' && analytics && (
          <div>
            {/* Stats Grid */}
            <div className="grid-4" style={{ marginBottom: 24 }}>
              <div className="stat-card">
                <div className="stat-icon" style={{ background: 'rgba(0, 212, 255, 0.15)', color: '#00d4ff' }}>
                  <Ticket size={20} />
                </div>
                <div className="stat-value">{analytics.total_tickets}</div>
                <div className="stat-label">Total Tickets</div>
              </div>
              <div className="stat-card">
                <div className="stat-icon" style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#ef4444' }}>
                  <TrendingDown size={20} />
                </div>
                <div className="stat-value">{analytics.by_sentiment.negative || 0}</div>
                <div className="stat-label">Negative</div>
              </div>
              <div className="stat-card">
                <div className="stat-icon" style={{ background: 'rgba(245, 158, 11, 0.15)', color: '#f59e0b' }}>
                  <AlertTriangle size={20} />
                </div>
                <div className="stat-value">{analytics.by_priority.critical || 0}</div>
                <div className="stat-label">Critical Priority</div>
              </div>
              <div className="stat-card">
                <div className="stat-icon" style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#10b981' }}>
                  <CheckCircle size={20} />
                </div>
                <div className="stat-value">{analytics.resolved_tickets}</div>
                <div className="stat-label">Resolved</div>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
              {/* Sentiment Breakdown */}
              <div className="card">
                <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-color)' }}>
                  <h3 style={{ margin: 0 }}>Sentiment Breakdown</h3>
                </div>
                <div style={{ padding: 20 }}>
                  {Object.entries(analytics.by_sentiment).map(([sentiment, count]) => (
                    <div key={sentiment} style={{ marginBottom: 12 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={{ 
                          textTransform: 'capitalize',
                          display: 'flex',
                          alignItems: 'center',
                          gap: 6,
                          color: SENTIMENT_CONFIG[sentiment]?.color
                        }}>
                          {SENTIMENT_CONFIG[sentiment]?.icon}
                          {sentiment}
                        </span>
                        <span>{count}</span>
                      </div>
                      <div style={{ 
                        height: 8, 
                        background: 'var(--bg-tertiary)', 
                        borderRadius: 4,
                        overflow: 'hidden'
                      }}>
                        <div style={{
                          height: '100%',
                          width: `${(count / analytics.total_tickets) * 100}%`,
                          background: SENTIMENT_CONFIG[sentiment]?.color,
                          borderRadius: 4
                        }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Priority Breakdown */}
              <div className="card">
                <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-color)' }}>
                  <h3 style={{ margin: 0 }}>Priority Breakdown</h3>
                </div>
                <div style={{ padding: 20 }}>
                  {Object.entries(analytics.by_priority).map(([priority, count]) => (
                    <div key={priority} style={{ marginBottom: 12 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={{ 
                          textTransform: 'capitalize',
                          color: PRIORITY_CONFIG[priority]?.color
                        }}>
                          {priority}
                        </span>
                        <span>{count}</span>
                      </div>
                      <div style={{ 
                        height: 8, 
                        background: 'var(--bg-tertiary)', 
                        borderRadius: 4,
                        overflow: 'hidden'
                      }}>
                        <div style={{
                          height: '100%',
                          width: `${(count / analytics.total_tickets) * 100}%`,
                          background: PRIORITY_CONFIG[priority]?.color,
                          borderRadius: 4
                        }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Key Metrics */}
            <div className="card" style={{ marginTop: 24 }}>
              <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-color)' }}>
                <h3 style={{ margin: 0 }}>Key Metrics</h3>
              </div>
              <div style={{ padding: 20, display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 24 }}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 32, fontWeight: 700, color: analytics.average_sentiment_score >= 0 ? '#10b981' : '#ef4444' }}>
                    {analytics.average_sentiment_score > 0 ? '+' : ''}{analytics.average_sentiment_score}
                  </div>
                  <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>Avg Sentiment Score</div>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 32, fontWeight: 700, color: '#f59e0b' }}>
                    {analytics.escalation_rate}%
                  </div>
                  <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>Escalation Rate</div>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 32, fontWeight: 700, color: '#00d4ff' }}>
                    {analytics.open_tickets}
                  </div>
                  <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>Open Tickets</div>
                </div>
              </div>
            </div>
          </div>
        )}
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

