import { useState, useEffect } from 'react';
import {
  Brain,
  Database,
  MessageSquare,
  Zap,
  FileText,
  Activity,
  CheckCircle,
  AlertCircle,
  RefreshCw,
  Clock,
  TrendingUp,
  Server,
  Cpu,
  Cloud,
  ThumbsUp,
  ThumbsDown
} from 'lucide-react';
import { ragApi, healthApi, api, llmApi } from '../api/client';

interface Stats {
  documents: number;
  chunks: number;
  conversations: number;
  llmConfigured: boolean;
  faissAvailable: boolean;
  cacheHits: number;
  cacheMisses: number;
  totalRequests: number;
  avgLatency: number;
}

interface FeedbackStats {
  total: number;
  positive: number;
  negative: number;
  positive_rate: number;
  by_model: Record<string, { positive: number; negative: number; total: number }>;
  recent_negative: Array<{ id: string; query: string; comment: string; model: string; created_at: string }>;
}

interface ConfigStatus {
  openai_configured: boolean;
  anthropic_configured: boolean;
  environment: string;
}

interface ProviderStatus {
  available: boolean;
  models: string[];
}

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats>({
    documents: 0,
    chunks: 0,
    conversations: 0,
    llmConfigured: false,
    faissAvailable: false,
    cacheHits: 0,
    cacheMisses: 0,
    totalRequests: 0,
    avgLatency: 0
  });
  const [config, setConfig] = useState<ConfigStatus | null>(null);
  const [providers, setProviders] = useState<Record<string, ProviderStatus>>({});
  const [telemetry, setTelemetry] = useState<any>(null);
  const [feedbackStats, setFeedbackStats] = useState<FeedbackStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);

  useEffect(() => {
    loadData();
    
    // Auto-refresh every 5 seconds
    const interval = autoRefresh ? setInterval(loadData, 5000) : null;
    return () => { if (interval) clearInterval(interval); };
  }, [autoRefresh]);

  const loadData = async () => {
    try {
      const [ragStats, configData, perfData, providerData, telemetryData, feedbackData] = await Promise.all([
        ragApi.getStats(),
        healthApi.config(),
        api.get('/performance/stats').catch(() => ({ data: {} })),
        llmApi.getProviders().catch(() => ({ data: { providers: {} } })),
        api.get('/telemetry/dashboard').catch(() => ({ data: {} })),
        api.get('/feedback/stats').catch(() => ({ data: null }))
      ]);

      setStats({
        documents: ragStats.data.database?.documents || ragStats.data.vector_store?.document_count || 0,
        chunks: ragStats.data.database?.chunks || 0,
        conversations: ragStats.data.conversations || 0,
        llmConfigured: ragStats.data.llm_configured || false,
        faissAvailable: ragStats.data.vector_store?.faiss_available || false,
        cacheHits: perfData.data.cache?.memory?.hits || 0,
        cacheMisses: perfData.data.cache?.memory?.misses || 0,
        totalRequests: telemetryData.data.requests?.total || 0,
        avgLatency: Object.values(telemetryData.data.latency || {}).reduce((acc: number, l: any) => acc + (l.mean || 0), 0) / Math.max(Object.keys(telemetryData.data.latency || {}).length, 1)
      });

      setConfig(configData.data);
      setProviders(providerData.data.providers || {});
      setTelemetry(telemetryData.data);
      setFeedbackStats(feedbackData.data);
    } catch (error) {
      console.error('Failed to load stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const cacheHitRate = stats.cacheHits + stats.cacheMisses > 0 
    ? ((stats.cacheHits / (stats.cacheHits + stats.cacheMisses)) * 100).toFixed(1)
    : '0';

  if (loading) {
    return (
      <>
        <header className="page-header">
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">Loading...</p>
        </header>
        <div className="page-content">
          <div className="loading">
            <div className="spinner" />
            <span>Loading dashboard...</span>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <header className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 className="page-title">Dashboard</h1>
            <p className="page-subtitle">GoAI Sovereign Platform Overview</p>
          </div>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'var(--text-secondary)' }}>
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                style={{ width: 16, height: 16 }}
              />
              Auto-refresh
            </label>
            <button className="btn btn-secondary" onClick={loadData}>
              <RefreshCw size={18} />
              Refresh
            </button>
          </div>
        </div>
      </header>

      <div className="page-content">
        {/* Main Stats Grid */}
        <div className="grid-4" style={{ marginBottom: 24 }}>
          <div className="stat-card">
            <div className="stat-icon blue">
              <FileText size={20} />
            </div>
            <div className="stat-value">{stats.documents}</div>
            <div className="stat-label">Documents</div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
              {stats.chunks} chunks indexed
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon purple">
              <Activity size={20} />
            </div>
            <div className="stat-value">{stats.totalRequests}</div>
            <div className="stat-label">Total Requests</div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
              {stats.avgLatency > 0 ? `~${Math.round(stats.avgLatency)}ms avg` : 'No data yet'}
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon green">
              <Zap size={20} />
            </div>
            <div className="stat-value">{cacheHitRate}%</div>
            <div className="stat-label">Cache Hit Rate</div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
              {stats.cacheHits} hits / {stats.cacheMisses} misses
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon orange">
              <MessageSquare size={20} />
            </div>
            <div className="stat-value">{stats.conversations}</div>
            <div className="stat-label">Conversations</div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
              Active sessions
            </div>
          </div>
        </div>

        <div className="grid-2" style={{ marginBottom: 24 }}>
          {/* LLM Providers */}
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">
                <Brain size={20} style={{ marginRight: 8 }} />
                LLM Providers
              </h2>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {/* Ollama */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: 12,
                background: 'var(--bg-tertiary)',
                borderRadius: 'var(--radius-md)',
                borderLeft: `3px solid ${providers.ollama?.available ? '#10b981' : 'var(--border-color)'}`
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <Cpu size={18} color={providers.ollama?.available ? '#10b981' : 'var(--text-muted)'} />
                  <div>
                    <div style={{ fontWeight: 500 }}>Ollama</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                      {providers.ollama?.available ? providers.ollama.models.slice(0, 3).join(', ') : 'Not running'}
                    </div>
                  </div>
                </div>
                {providers.ollama?.available ? (
                  <span className="tag success">LOCAL</span>
                ) : (
                  <span className="tag">Offline</span>
                )}
              </div>

              {/* OpenAI */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: 12,
                background: 'var(--bg-tertiary)',
                borderRadius: 'var(--radius-md)',
                borderLeft: `3px solid ${providers.openai?.available ? '#00d4ff' : 'var(--border-color)'}`
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <Cloud size={18} color={providers.openai?.available ? '#00d4ff' : 'var(--text-muted)'} />
                  <div>
                    <div style={{ fontWeight: 500 }}>OpenAI</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                      {providers.openai?.available ? 'gpt-4o, gpt-4o-mini' : 'API key not set'}
                    </div>
                  </div>
                </div>
                {providers.openai?.available ? (
                  <span className="tag info">Connected</span>
                ) : (
                  <span className="tag">Not configured</span>
                )}
              </div>

              {/* Anthropic */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: 12,
                background: 'var(--bg-tertiary)',
                borderRadius: 'var(--radius-md)',
                borderLeft: `3px solid ${providers.anthropic?.available ? '#d97706' : 'var(--border-color)'}`
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <Cloud size={18} color={providers.anthropic?.available ? '#d97706' : 'var(--text-muted)'} />
                  <div>
                    <div style={{ fontWeight: 500 }}>Anthropic</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                      {providers.anthropic?.available ? 'Claude 3' : 'Optional'}
                    </div>
                  </div>
                </div>
                {providers.anthropic?.available ? (
                  <span className="tag" style={{ background: 'rgba(217, 119, 6, 0.2)', color: '#d97706' }}>Connected</span>
                ) : (
                  <span className="tag">Optional</span>
                )}
              </div>
            </div>
          </div>

          {/* Request Stats */}
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">
                <TrendingUp size={20} style={{ marginRight: 8 }} />
                Request Latency
              </h2>
            </div>
            {telemetry?.latency && Object.keys(telemetry.latency).length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {Object.entries(telemetry.latency).slice(0, 5).map(([endpoint, data]: [string, any]) => (
                  <div key={endpoint} style={{
                    padding: 12,
                    background: 'var(--bg-tertiary)',
                    borderRadius: 'var(--radius-md)'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                      <span style={{ fontSize: 12, fontFamily: 'monospace', color: 'var(--accent-primary)' }}>
                        {endpoint}
                      </span>
                      <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                        p95: {data.p95?.toFixed(0)}ms
                      </span>
                    </div>
                    <div style={{ height: 6, background: 'var(--bg-primary)', borderRadius: 3, overflow: 'hidden' }}>
                      <div style={{
                        height: '100%',
                        width: `${Math.min((data.mean / 5000) * 100, 100)}%`,
                        background: data.mean < 500 ? '#10b981' : data.mean < 2000 ? '#eab308' : '#ef4444',
                        borderRadius: 3,
                        transition: 'width 0.5s ease'
                      }} />
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                      Mean: {data.mean?.toFixed(0)}ms
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ 
                padding: 40, 
                textAlign: 'center', 
                color: 'var(--text-muted)' 
              }}>
                <Clock size={32} style={{ marginBottom: 12, opacity: 0.3 }} />
                <div>No request data yet</div>
                <div style={{ fontSize: 12, marginTop: 4 }}>Make some API calls to see latency stats</div>
              </div>
            )}
          </div>
        </div>

        {/* Feedback Stats */}
        {feedbackStats && feedbackStats.total > 0 && (
          <div className="card" style={{ marginBottom: 24 }}>
            <div className="card-header">
              <h2 className="card-title">
                <ThumbsUp size={20} style={{ marginRight: 8 }} />
                User Feedback
              </h2>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 20 }}>
              <div style={{ 
                padding: 16, 
                background: 'var(--bg-tertiary)', 
                borderRadius: 'var(--radius-md)',
                textAlign: 'center'
              }}>
                <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--text-primary)' }}>
                  {feedbackStats.total}
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Total Feedback</div>
              </div>
              <div style={{ 
                padding: 16, 
                background: 'rgba(16, 185, 129, 0.1)', 
                borderRadius: 'var(--radius-md)',
                textAlign: 'center',
                border: '1px solid rgba(16, 185, 129, 0.3)'
              }}>
                <div style={{ fontSize: 28, fontWeight: 700, color: '#10b981', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
                  <ThumbsUp size={20} />
                  {feedbackStats.positive}
                </div>
                <div style={{ fontSize: 12, color: '#10b981' }}>Positive</div>
              </div>
              <div style={{ 
                padding: 16, 
                background: 'rgba(239, 68, 68, 0.1)', 
                borderRadius: 'var(--radius-md)',
                textAlign: 'center',
                border: '1px solid rgba(239, 68, 68, 0.3)'
              }}>
                <div style={{ fontSize: 28, fontWeight: 700, color: '#ef4444', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
                  <ThumbsDown size={20} />
                  {feedbackStats.negative}
                </div>
                <div style={{ fontSize: 12, color: '#ef4444' }}>Negative</div>
              </div>
              <div style={{ 
                padding: 16, 
                background: 'var(--bg-tertiary)', 
                borderRadius: 'var(--radius-md)',
                textAlign: 'center'
              }}>
                <div style={{ 
                  fontSize: 28, 
                  fontWeight: 700, 
                  color: feedbackStats.positive_rate >= 80 ? '#10b981' : feedbackStats.positive_rate >= 50 ? '#f59e0b' : '#ef4444'
                }}>
                  {feedbackStats.positive_rate}%
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Satisfaction</div>
              </div>
            </div>

            {/* Satisfaction Bar */}
            <div style={{ marginBottom: 20 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 8 }}>
                <span style={{ color: '#10b981' }}>👍 {feedbackStats.positive_rate}% Positive</span>
                <span style={{ color: '#ef4444' }}>{100 - feedbackStats.positive_rate}% Negative 👎</span>
              </div>
              <div style={{ height: 8, background: 'var(--bg-primary)', borderRadius: 4, overflow: 'hidden', display: 'flex' }}>
                <div style={{ 
                  width: `${feedbackStats.positive_rate}%`, 
                  background: '#10b981',
                  transition: 'width 0.5s ease'
                }} />
                <div style={{ 
                  width: `${100 - feedbackStats.positive_rate}%`, 
                  background: '#ef4444',
                  transition: 'width 0.5s ease'
                }} />
              </div>
            </div>

            {/* By Model */}
            {Object.keys(feedbackStats.by_model).length > 0 && (
              <div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                  Feedback by Model
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
                  {Object.entries(feedbackStats.by_model).map(([model, data]) => (
                    <div key={model} style={{
                      padding: '10px 16px',
                      background: 'var(--bg-tertiary)',
                      borderRadius: 'var(--radius-sm)',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 12
                    }}>
                      <span style={{ fontFamily: 'monospace', fontSize: 12 }}>{model}</span>
                      <span style={{ color: '#10b981', display: 'flex', alignItems: 'center', gap: 4, fontSize: 12 }}>
                        <ThumbsUp size={12} /> {data.positive}
                      </span>
                      <span style={{ color: '#ef4444', display: 'flex', alignItems: 'center', gap: 4, fontSize: 12 }}>
                        <ThumbsDown size={12} /> {data.negative}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Recent Negative */}
            {feedbackStats.recent_negative && feedbackStats.recent_negative.length > 0 && (
              <div style={{ marginTop: 20 }}>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                  Recent Negative Feedback (Review Queue)
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {feedbackStats.recent_negative.slice(0, 3).map(fb => (
                    <div key={fb.id} style={{
                      padding: 12,
                      background: 'rgba(239, 68, 68, 0.05)',
                      borderRadius: 'var(--radius-sm)',
                      borderLeft: '3px solid #ef4444'
                    }}>
                      <div style={{ fontSize: 13, marginBottom: 4 }}>
                        <strong>Q:</strong> {fb.query}
                      </div>
                      {fb.comment && (
                        <div style={{ fontSize: 12, color: '#ef4444' }}>
                          💬 {fb.comment}
                        </div>
                      )}
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>
                        {fb.model} • {new Date(fb.created_at).toLocaleString()}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Recent Traces */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">
              <Activity size={20} style={{ marginRight: 8 }} />
              Recent Requests
            </h2>
          </div>
          {telemetry?.traces?.recent && telemetry.traces.recent.length > 0 ? (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                    <th style={{ textAlign: 'left', padding: 12, color: 'var(--text-secondary)', fontWeight: 500 }}>Endpoint</th>
                    <th style={{ textAlign: 'left', padding: 12, color: 'var(--text-secondary)', fontWeight: 500 }}>Status</th>
                    <th style={{ textAlign: 'right', padding: 12, color: 'var(--text-secondary)', fontWeight: 500 }}>Latency</th>
                    <th style={{ textAlign: 'right', padding: 12, color: 'var(--text-secondary)', fontWeight: 500 }}>Time</th>
                  </tr>
                </thead>
                <tbody>
                  {telemetry.traces.recent.slice(0, 8).map((trace: any, i: number) => (
                    <tr key={i} style={{ borderBottom: '1px solid var(--border-color)' }}>
                      <td style={{ padding: 12 }}>
                        <span style={{ fontFamily: 'monospace', fontSize: 13 }}>{trace.name}</span>
                      </td>
                      <td style={{ padding: 12 }}>
                        <span className={`tag ${trace.status === 'ok' ? 'success' : 'error'}`}>
                          {trace.status}
                        </span>
                      </td>
                      <td style={{ padding: 12, textAlign: 'right', fontFamily: 'monospace' }}>
                        <span style={{ 
                          color: trace.duration_ms < 500 ? '#10b981' : 
                                 trace.duration_ms < 2000 ? '#eab308' : '#ef4444'
                        }}>
                          {trace.duration_ms > 1000 
                            ? `${(trace.duration_ms / 1000).toFixed(1)}s` 
                            : `${Math.round(trace.duration_ms)}ms`}
                        </span>
                      </td>
                      <td style={{ padding: 12, textAlign: 'right', color: 'var(--text-muted)', fontSize: 12 }}>
                        {new Date(trace.start_time).toLocaleTimeString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div style={{ 
              padding: 40, 
              textAlign: 'center', 
              color: 'var(--text-muted)' 
            }}>
              <Server size={32} style={{ marginBottom: 12, opacity: 0.3 }} />
              <div>No recent requests</div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
