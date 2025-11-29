import { useState, useEffect } from 'react';
import {
  Shield,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Info,
  Play,
  Loader2,
  FileText,
  Lightbulb,
  RefreshCw,
  ToggleLeft,
  ToggleRight
} from 'lucide-react';
import { useToast } from '../components/Toast';

interface ValidationIssue {
  category: string;
  severity: string;
  message: string;
  location?: string;
  suggestion?: string;
}

interface ValidationResult {
  valid: boolean;
  score: number;
  errors: string[];
  warnings: string[];
  issues: ValidationIssue[];
  metadata: Record<string, any>;
}

interface FactCheckResult {
  claim: string;
  verdict: string;
  confidence: number;
  evidence: string[];
  sources: string[];
}

interface Rule {
  name: string;
  enabled: boolean;
  description?: string;
}

const API_BASE = 'http://localhost:8000/api/v1';

const SEVERITY_CONFIG: Record<string, { color: string; icon: React.ReactNode }> = {
  error: { color: '#ef4444', icon: <XCircle size={16} /> },
  warning: { color: '#f59e0b', icon: <AlertTriangle size={16} /> },
  info: { color: '#00d4ff', icon: <Info size={16} /> }
};

const VERDICT_CONFIG: Record<string, { color: string; label: string }> = {
  supported: { color: '#10b981', label: 'Supported' },
  refuted: { color: '#ef4444', label: 'Refuted' },
  unverifiable: { color: '#f59e0b', label: 'Unverifiable' }
};

export default function ValidatorPage() {
  const [mode, setMode] = useState<'validate' | 'factcheck' | 'quality'>('validate');
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ValidationResult | null>(null);
  const [factResult, setFactResult] = useState<FactCheckResult | null>(null);
  const [qualityResult, setQualityResult] = useState<any>(null);
  const [rules, setRules] = useState<Rule[]>([]);
  const [useLLM, setUseLLM] = useState(true);
  
  const toast = useToast();

  useEffect(() => {
    fetchRules();
  }, []);

  const fetchRules = async () => {
    try {
      const res = await fetch(`${API_BASE}/validator/rules`);
      const data = await res.json();
      setRules(data.rules || []);
    } catch (error) {
      console.error('Failed to fetch rules:', error);
    }
  };

  const validate = async () => {
    if (!content.trim()) return;
    
    setLoading(true);
    setResult(null);
    setFactResult(null);
    setQualityResult(null);
    
    try {
      if (mode === 'validate') {
        const res = await fetch(`${API_BASE}/validator/validate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content, use_llm: useLLM })
        });
        const data = await res.json();
        setResult(data);
      } else if (mode === 'factcheck') {
        const res = await fetch(`${API_BASE}/validator/fact-check`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ claim: content })
        });
        const data = await res.json();
        setFactResult(data);
      } else {
        const res = await fetch(`${API_BASE}/validator/quality`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content })
        });
        const data = await res.json();
        setQualityResult(data);
      }
      toast.success(`${mode === 'factcheck' ? 'Fact check' : 'Validation'} complete!`);
    } catch (error) {
      toast.error('Validation failed');
    } finally {
      setLoading(false);
    }
  };

  const toggleRule = async (ruleName: string, currentEnabled: boolean) => {
    try {
      const endpoint = currentEnabled ? 'disable' : 'enable';
      await fetch(`${API_BASE}/validator/rules/${ruleName}/${endpoint}`, { method: 'POST' });
      fetchRules();
    } catch (error) {
      toast.error('Failed to toggle rule');
    }
  };

  return (
    <>
      <header className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 className="page-title">Content Validator</h1>
            <p className="page-subtitle">Validate content, fact-check claims, assess quality</p>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            {(['validate', 'factcheck', 'quality'] as const).map(m => (
              <button
                key={m}
                className={`btn btn-sm ${mode === m ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setMode(m)}
              >
                {m === 'validate' ? 'Validate' : m === 'factcheck' ? 'Fact Check' : 'Quality'}
              </button>
            ))}
          </div>
        </div>
      </header>

      <div className="page-content">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: 24 }}>
          {/* Main Panel */}
          <div>
            <div className="card">
              <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3 style={{ margin: 0 }}>
                  {mode === 'validate' ? 'Content to Validate' : mode === 'factcheck' ? 'Claim to Check' : 'Content for Quality Assessment'}
                </h3>
                {mode === 'validate' && (
                  <button
                    onClick={() => setUseLLM(!useLLM)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                      padding: '6px 12px',
                      background: useLLM ? 'rgba(16, 185, 129, 0.15)' : 'var(--bg-tertiary)',
                      border: `1px solid ${useLLM ? '#10b981' : 'var(--border-color)'}`,
                      borderRadius: 'var(--radius-sm)',
                      color: useLLM ? '#10b981' : 'var(--text-muted)',
                      cursor: 'pointer',
                      fontSize: 12
                    }}
                  >
                    {useLLM ? <ToggleRight size={16} /> : <ToggleLeft size={16} />}
                    LLM Validation
                  </button>
                )}
              </div>
              <div style={{ padding: 20 }}>
                <textarea
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  placeholder={
                    mode === 'factcheck' 
                      ? 'Enter a claim to fact-check...\n\nExample: "The Earth is 4.5 billion years old"'
                      : 'Enter content to validate...\n\nExample: Check for spelling, grammar, factual accuracy...'
                  }
                  style={{ width: '100%', minHeight: 150 }}
                />
                <button
                  className="btn btn-primary"
                  onClick={validate}
                  disabled={loading || !content.trim()}
                  style={{ marginTop: 16 }}
                >
                  {loading ? (
                    <>
                      <Loader2 size={16} className="spin" />
                      Processing...
                    </>
                  ) : (
                    <>
                      <Play size={16} />
                      {mode === 'factcheck' ? 'Check Claim' : mode === 'quality' ? 'Assess Quality' : 'Validate'}
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Results */}
            {result && mode === 'validate' && (
              <div className="card" style={{ marginTop: 24 }}>
                <div style={{ 
                  padding: '16px 20px', 
                  borderBottom: '1px solid var(--border-color)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12
                }}>
                  {result.valid ? (
                    <CheckCircle size={24} color="#10b981" />
                  ) : (
                    <XCircle size={24} color="#ef4444" />
                  )}
                  <div>
                    <h3 style={{ margin: 0, color: result.valid ? '#10b981' : '#ef4444' }}>
                      {result.valid ? 'Content Valid' : 'Issues Found'}
                    </h3>
                    <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                      Score: {(result.score * 100).toFixed(0)}%
                    </div>
                  </div>
                  <div style={{
                    marginLeft: 'auto',
                    width: 60,
                    height: 60,
                    borderRadius: '50%',
                    background: `conic-gradient(${result.valid ? '#10b981' : '#ef4444'} ${result.score * 360}deg, var(--bg-tertiary) 0deg)`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}>
                    <div style={{
                      width: 48,
                      height: 48,
                      borderRadius: '50%',
                      background: 'var(--bg-card)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontWeight: 700,
                      fontSize: 14
                    }}>
                      {(result.score * 100).toFixed(0)}
                    </div>
                  </div>
                </div>
                
                {result.issues.length > 0 && (
                  <div style={{ padding: 16 }}>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 12, textTransform: 'uppercase' }}>
                      Issues ({result.issues.length})
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                      {result.issues.map((issue, i) => {
                        const config = SEVERITY_CONFIG[issue.severity] || SEVERITY_CONFIG.info;
                        return (
                          <div
                            key={i}
                            style={{
                              padding: 12,
                              background: `${config.color}10`,
                              border: `1px solid ${config.color}40`,
                              borderRadius: 'var(--radius-sm)'
                            }}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                              <span style={{ color: config.color }}>{config.icon}</span>
                              <span style={{ fontWeight: 600, fontSize: 13, color: config.color }}>
                                {issue.category}
                              </span>
                            </div>
                            <p style={{ margin: 0, fontSize: 13 }}>{issue.message}</p>
                            {issue.suggestion && (
                              <div style={{ marginTop: 8, display: 'flex', alignItems: 'flex-start', gap: 6, fontSize: 12, color: 'var(--text-secondary)' }}>
                                <Lightbulb size={14} color="#f59e0b" style={{ flexShrink: 0, marginTop: 2 }} />
                                {issue.suggestion}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}

            {factResult && mode === 'factcheck' && (
              <div className="card" style={{ marginTop: 24 }}>
                <div style={{ padding: 20 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 20 }}>
                    <div style={{
                      padding: '8px 16px',
                      borderRadius: 'var(--radius-md)',
                      background: `${VERDICT_CONFIG[factResult.verdict]?.color || '#64748b'}20`,
                      color: VERDICT_CONFIG[factResult.verdict]?.color || '#64748b',
                      fontWeight: 700,
                      fontSize: 14
                    }}>
                      {VERDICT_CONFIG[factResult.verdict]?.label || factResult.verdict}
                    </div>
                    <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                      Confidence: {(factResult.confidence * 100).toFixed(0)}%
                    </div>
                  </div>
                  
                  <div style={{ 
                    padding: 16, 
                    background: 'var(--bg-tertiary)', 
                    borderRadius: 'var(--radius-md)',
                    marginBottom: 16,
                    fontStyle: 'italic'
                  }}>
                    "{factResult.claim}"
                  </div>
                  
                  {factResult.evidence.length > 0 && (
                    <div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase' }}>
                        Evidence
                      </div>
                      {factResult.evidence.map((e, i) => (
                        <div key={i} style={{ 
                          padding: 12, 
                          background: 'var(--bg-secondary)', 
                          borderRadius: 'var(--radius-sm)',
                          marginBottom: 8,
                          fontSize: 13
                        }}>
                          {e}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {qualityResult && mode === 'quality' && (
              <div className="card" style={{ marginTop: 24 }}>
                <div style={{ padding: 20 }}>
                  <h3 style={{ marginBottom: 16 }}>Quality Assessment</h3>
                  <pre style={{
                    padding: 16,
                    background: 'var(--bg-tertiary)',
                    borderRadius: 'var(--radius-md)',
                    overflow: 'auto',
                    fontSize: 13,
                    fontFamily: 'var(--font-mono)'
                  }}>
                    {JSON.stringify(qualityResult, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </div>

          {/* Rules Sidebar */}
          <div className="card" style={{ height: 'fit-content' }}>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ margin: 0, fontSize: 14 }}>Validation Rules</h3>
              <button onClick={fetchRules} style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}>
                <RefreshCw size={14} />
              </button>
            </div>
            <div style={{ padding: 12 }}>
              {rules.length === 0 ? (
                <div style={{ textAlign: 'center', padding: 20, color: 'var(--text-muted)', fontSize: 13 }}>
                  No rules configured
                </div>
              ) : (
                rules.map(rule => (
                  <div
                    key={rule.name}
                    onClick={() => toggleRule(rule.name, rule.enabled)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '10px 12px',
                      borderRadius: 'var(--radius-sm)',
                      cursor: 'pointer',
                      marginBottom: 4,
                      background: rule.enabled ? 'rgba(16, 185, 129, 0.1)' : 'transparent'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <Shield size={14} color={rule.enabled ? '#10b981' : 'var(--text-muted)'} />
                      <span style={{ fontSize: 13 }}>{rule.name}</span>
                    </div>
                    {rule.enabled ? (
                      <ToggleRight size={18} color="#10b981" />
                    ) : (
                      <ToggleLeft size={18} color="var(--text-muted)" />
                    )}
                  </div>
                ))
              )}
            </div>
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

