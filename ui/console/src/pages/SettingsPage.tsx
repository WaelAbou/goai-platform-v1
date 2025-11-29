import { useState, useEffect } from 'react';
import { Settings, Key, Cpu, Cloud, Check, X, RefreshCw, Eye, EyeOff, Server, Database, Zap } from 'lucide-react';
import { llmApi, api } from '../api/client';

interface ProviderStatus {
  available: boolean;
  models: string[];
  url?: string;
}

interface SystemStatus {
  cache: { memory: { size: number; hits: number; misses: number } };
  database: { documents: number; chunks: number; persistent: boolean };
  tasks: { completed: number; failed: number; running: boolean };
}

export default function SettingsPage() {
  const [providers, setProviders] = useState<Record<string, ProviderStatus>>({});
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});
  
  // API Keys (stored in localStorage for demo - in production use secure storage)
  const [apiKeys, setApiKeys] = useState({
    openai: localStorage.getItem('OPENAI_API_KEY') || '',
    anthropic: localStorage.getItem('ANTHROPIC_API_KEY') || ''
  });
  
  const [defaultModel, setDefaultModel] = useState(
    localStorage.getItem('DEFAULT_MODEL') || 'gpt-4o-mini'
  );

  useEffect(() => {
    fetchStatus();
  }, []);

  const fetchStatus = async () => {
    setLoading(true);
    try {
      const [providersRes, perfRes, ragRes] = await Promise.all([
        llmApi.getProviders(),
        api.get('/performance/stats'),
        api.get('/rag/stats')
      ]);
      
      setProviders(providersRes.data.providers);
      setSystemStatus({
        cache: perfRes.data.cache,
        database: ragRes.data.database,
        tasks: perfRes.data.tasks
      });
    } catch (error) {
      console.error('Failed to fetch status:', error);
    } finally {
      setLoading(false);
    }
  };

  const saveApiKey = (provider: string, key: string) => {
    setApiKeys(prev => ({ ...prev, [provider]: key }));
    localStorage.setItem(`${provider.toUpperCase()}_API_KEY`, key);
  };

  const saveDefaultModel = (model: string) => {
    setDefaultModel(model);
    localStorage.setItem('DEFAULT_MODEL', model);
  };

  const toggleShowKey = (provider: string) => {
    setShowKeys(prev => ({ ...prev, [provider]: !prev[provider] }));
  };

  const getProviderIcon = (provider: string) => {
    if (provider === 'ollama') return <Cpu size={20} />;
    return <Cloud size={20} />;
  };

  const getProviderColor = (provider: string) => {
    switch (provider) {
      case 'ollama': return '#10b981';
      case 'openai': return '#00d4ff';
      case 'anthropic': return '#d97706';
      default: return 'var(--text-muted)';
    }
  };

  return (
    <>
      <header className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 className="page-title">Settings</h1>
            <p className="page-subtitle">Configure API keys, models, and system settings</p>
          </div>
          <button className="btn btn-secondary" onClick={fetchStatus} disabled={loading}>
            <RefreshCw size={18} className={loading ? 'spin' : ''} />
            Refresh
          </button>
        </div>
      </header>

      <div className="page-content">
        <div className="grid-2">
          {/* LLM Providers */}
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">
                <Key size={20} style={{ marginRight: 8 }} />
                LLM Providers
              </h2>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {/* OpenAI */}
              <div style={{
                padding: 16,
                background: 'var(--bg-tertiary)',
                borderRadius: 'var(--radius-md)',
                border: `1px solid ${providers.openai?.available ? 'rgba(0, 212, 255, 0.3)' : 'var(--border-color)'}`
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Cloud size={20} color="#00d4ff" />
                    <span style={{ fontWeight: 600 }}>OpenAI</span>
                  </div>
                  {providers.openai?.available ? (
                    <span className="tag success"><Check size={12} /> Connected</span>
                  ) : (
                    <span className="tag error"><X size={12} /> Not configured</span>
                  )}
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <input
                    type={showKeys.openai ? 'text' : 'password'}
                    placeholder="sk-..."
                    value={apiKeys.openai}
                    onChange={(e) => saveApiKey('openai', e.target.value)}
                    style={{ flex: 1 }}
                  />
                  <button className="btn btn-secondary btn-icon" onClick={() => toggleShowKey('openai')}>
                    {showKeys.openai ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
                {providers.openai?.available && (
                  <div style={{ marginTop: 8, fontSize: 12, color: 'var(--text-muted)' }}>
                    Models: {providers.openai.models.join(', ')}
                  </div>
                )}
              </div>

              {/* Anthropic */}
              <div style={{
                padding: 16,
                background: 'var(--bg-tertiary)',
                borderRadius: 'var(--radius-md)',
                border: `1px solid ${providers.anthropic?.available ? 'rgba(217, 119, 6, 0.3)' : 'var(--border-color)'}`
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Cloud size={20} color="#d97706" />
                    <span style={{ fontWeight: 600 }}>Anthropic</span>
                  </div>
                  {providers.anthropic?.available ? (
                    <span className="tag success"><Check size={12} /> Connected</span>
                  ) : (
                    <span className="tag" style={{ background: 'var(--bg-hover)' }}>Optional</span>
                  )}
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <input
                    type={showKeys.anthropic ? 'text' : 'password'}
                    placeholder="sk-ant-..."
                    value={apiKeys.anthropic}
                    onChange={(e) => saveApiKey('anthropic', e.target.value)}
                    style={{ flex: 1 }}
                  />
                  <button className="btn btn-secondary btn-icon" onClick={() => toggleShowKey('anthropic')}>
                    {showKeys.anthropic ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              {/* Ollama */}
              <div style={{
                padding: 16,
                background: 'var(--bg-tertiary)',
                borderRadius: 'var(--radius-md)',
                border: `1px solid ${providers.ollama?.available ? 'rgba(16, 185, 129, 0.3)' : 'var(--border-color)'}`
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Cpu size={20} color="#10b981" />
                    <span style={{ fontWeight: 600 }}>Ollama</span>
                    <span style={{ fontSize: 11, background: 'rgba(16, 185, 129, 0.2)', padding: '2px 6px', borderRadius: 4, color: '#10b981' }}>LOCAL</span>
                  </div>
                  {providers.ollama?.available ? (
                    <span className="tag success"><Check size={12} /> Running</span>
                  ) : (
                    <span className="tag error"><X size={12} /> Not running</span>
                  )}
                </div>
                <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                  {providers.ollama?.available ? (
                    <>
                      <div>URL: {providers.ollama.url}</div>
                      <div style={{ marginTop: 4 }}>Models: {providers.ollama.models.slice(0, 5).join(', ')}</div>
                    </>
                  ) : (
                    <div>
                      Start Ollama: <code style={{ background: 'var(--bg-primary)', padding: '2px 6px', borderRadius: 4 }}>ollama serve</code>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Default Settings */}
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">
                <Settings size={20} style={{ marginRight: 8 }} />
                Default Settings
              </h2>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
              {/* Default Model */}
              <div>
                <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>Default Model</label>
                <select 
                  value={defaultModel} 
                  onChange={(e) => saveDefaultModel(e.target.value)}
                  style={{ width: '100%' }}
                >
                  <optgroup label="Ollama (Local)">
                    {providers.ollama?.models.map(m => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </optgroup>
                  <optgroup label="OpenAI">
                    {providers.openai?.models.map(m => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </optgroup>
                  <optgroup label="Anthropic">
                    {providers.anthropic?.models.map(m => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </optgroup>
                </select>
              </div>

              {/* System Status */}
              {systemStatus && (
                <div>
                  <label style={{ display: 'block', marginBottom: 12, fontWeight: 500 }}>System Status</label>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: 12,
                      background: 'var(--bg-tertiary)',
                      borderRadius: 'var(--radius-sm)'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <Zap size={16} color="var(--accent-primary)" />
                        <span>Cache</span>
                      </div>
                      <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                        {systemStatus.cache.memory.size} items | {systemStatus.cache.memory.hits} hits
                      </div>
                    </div>

                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: 12,
                      background: 'var(--bg-tertiary)',
                      borderRadius: 'var(--radius-sm)'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <Database size={16} color="var(--accent-secondary)" />
                        <span>Database</span>
                      </div>
                      <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                        {systemStatus.database.documents} docs | {systemStatus.database.chunks} chunks
                      </div>
                    </div>

                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: 12,
                      background: 'var(--bg-tertiary)',
                      borderRadius: 'var(--radius-sm)'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <Server size={16} color="var(--accent-tertiary)" />
                        <span>Task Queue</span>
                      </div>
                      <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                        {systemStatus.tasks.completed} completed | {systemStatus.tasks.running ? '🟢 Running' : '🔴 Stopped'}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Info Box */}
        <div className="card" style={{ marginTop: 24 }}>
          <div className="card-header">
            <h2 className="card-title">ℹ️ Configuration Notes</h2>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
            <div style={{ padding: 16, background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-md)' }}>
              <h4 style={{ marginBottom: 8, color: '#00d4ff' }}>OpenAI</h4>
              <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                Get your API key from <a href="https://platform.openai.com/api-keys" target="_blank" style={{ color: 'var(--accent-primary)' }}>platform.openai.com</a>. 
                Supports GPT-4o and GPT-4o-mini.
              </p>
            </div>
            <div style={{ padding: 16, background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-md)' }}>
              <h4 style={{ marginBottom: 8, color: '#d97706' }}>Anthropic</h4>
              <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                Get your API key from <a href="https://console.anthropic.com" target="_blank" style={{ color: 'var(--accent-primary)' }}>console.anthropic.com</a>. 
                Supports Claude 3 models.
              </p>
            </div>
            <div style={{ padding: 16, background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-md)' }}>
              <h4 style={{ marginBottom: 8, color: '#10b981' }}>Ollama</h4>
              <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                Install from <a href="https://ollama.ai" target="_blank" style={{ color: 'var(--accent-primary)' }}>ollama.ai</a>. 
                Run <code>ollama serve</code> then <code>ollama pull llama3.2</code>.
              </p>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

