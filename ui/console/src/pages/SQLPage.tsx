import { useState, useEffect } from 'react';
import { Database, Play, Code, FileText, Cpu, Cloud, ChevronDown } from 'lucide-react';
import { sqlApi, llmApi } from '../api/client';

interface SQLResult {
  sql: string;
  explanation: string;
  tables_used: string[];
  success: boolean;
  error?: string;
  latency_ms?: number;
  model?: string;
}

interface ModelOption {
  id: string;
  name: string;
  provider: 'openai' | 'anthropic' | 'ollama';
  available: boolean;
}

export default function SQLPage() {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SQLResult | null>(null);
  const [schemaRegistered, setSchemaRegistered] = useState(false);
  
  // Model selection
  const [models, setModels] = useState<ModelOption[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('gpt-4o-mini');
  const [showModelDropdown, setShowModelDropdown] = useState(false);

  useEffect(() => {
    fetchModels();
  }, []);

  const fetchModels = async () => {
    try {
      const response = await llmApi.getProviders();
      const providers = response.data.providers;
      const modelList: ModelOption[] = [];
      
      if (providers.ollama?.available) {
        providers.ollama.models.forEach((m: string) => {
          modelList.push({ id: m, name: m, provider: 'ollama', available: true });
        });
      }
      if (providers.openai?.available) {
        providers.openai.models.forEach((m: string) => {
          modelList.push({ id: m, name: m, provider: 'openai', available: true });
        });
      }
      if (providers.anthropic?.available) {
        providers.anthropic.models.forEach((m: string) => {
          modelList.push({ id: m, name: m, provider: 'anthropic', available: true });
        });
      }
      
      setModels(modelList);
      if (modelList.length > 0) setSelectedModel(modelList[0].id);
    } catch (error) {
      console.error('Failed to fetch models:', error);
    }
  };

  const getProviderIcon = (provider: string) => {
    if (provider === 'ollama') return <Cpu size={14} />;
    return <Cloud size={14} />;
  };
  
  const getProviderColor = (provider: string) => {
    switch (provider) {
      case 'ollama': return '#10b981';
      case 'openai': return '#00d4ff';
      case 'anthropic': return '#d97706';
      default: return 'var(--text-muted)';
    }
  };
  
  const currentModel = models.find(m => m.id === selectedModel);

  const registerSampleSchema = async () => {
    try {
      await sqlApi.registerSchema('ecommerce', 'postgresql', {
        customers: {
          columns: [
            { name: 'id', type: 'INTEGER' },
            { name: 'name', type: 'VARCHAR(100)' },
            { name: 'email', type: 'VARCHAR(100)' },
            { name: 'created_at', type: 'TIMESTAMP' }
          ],
          primary_key: 'id'
        },
        orders: {
          columns: [
            { name: 'id', type: 'INTEGER' },
            { name: 'customer_id', type: 'INTEGER' },
            { name: 'total', type: 'DECIMAL(10,2)' },
            { name: 'status', type: 'VARCHAR(50)' },
            { name: 'created_at', type: 'TIMESTAMP' }
          ],
          primary_key: 'id',
          foreign_keys: [{ column: 'customer_id', references: 'customers.id' }]
        },
        products: {
          columns: [
            { name: 'id', type: 'INTEGER' },
            { name: 'name', type: 'VARCHAR(200)' },
            { name: 'price', type: 'DECIMAL(10,2)' },
            { name: 'category', type: 'VARCHAR(50)' },
            { name: 'stock', type: 'INTEGER' }
          ],
          primary_key: 'id'
        }
      });
      setSchemaRegistered(true);
    } catch (error) {
      console.error('Failed to register schema:', error);
    }
  };

  const generateSQL = async () => {
    if (!question.trim()) return;

    setLoading(true);
    setResult(null);

    try {
      const response = await sqlApi.query(question, 'ecommerce');
      setResult({
        sql: response.data.sql,
        explanation: response.data.explanation,
        tables_used: response.data.tables_used,
        success: response.data.success,
        error: response.data.error
      });
    } catch (error) {
      console.error('Failed to generate SQL:', error);
      setResult({
        sql: '',
        explanation: '',
        tables_used: [],
        success: false,
        error: 'Failed to generate SQL. Please try again.'
      });
    } finally {
      setLoading(false);
    }
  };

  const sampleQuestions = [
    'Show all customers who placed orders over $100',
    'Find the top 5 products by total sales',
    'List customers with their total order count',
    'Get all pending orders from this month',
    'Find products with low stock (less than 10)'
  ];

  return (
    <>
      <header className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 className="page-title">SQL Agent</h1>
            <p className="page-subtitle">Convert natural language to SQL queries</p>
          </div>
          
          {/* Model Selector */}
          <div style={{ position: 'relative' }}>
            <button
              className="btn btn-secondary"
              onClick={() => setShowModelDropdown(!showModelDropdown)}
              style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 160 }}
            >
              <span style={{ color: getProviderColor(currentModel?.provider || 'openai') }}>
                {getProviderIcon(currentModel?.provider || 'openai')}
              </span>
              <span style={{ flex: 1, textAlign: 'left' }}>{selectedModel}</span>
              <ChevronDown size={14} />
            </button>
            
            {showModelDropdown && (
              <div style={{
                position: 'absolute',
                top: '100%',
                right: 0,
                marginTop: 4,
                background: 'var(--bg-secondary)',
                border: '1px solid var(--border-color)',
                borderRadius: 'var(--radius-md)',
                padding: 8,
                minWidth: 200,
                zIndex: 100,
                boxShadow: '0 8px 32px rgba(0,0,0,0.4)'
              }}>
                {['ollama', 'openai', 'anthropic'].map(provider => {
                  const providerModels = models.filter(m => m.provider === provider);
                  if (providerModels.length === 0) return null;
                  
                  return (
                    <div key={provider}>
                      <div style={{
                        fontSize: 10,
                        color: getProviderColor(provider),
                        padding: '8px 8px 4px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 6,
                        textTransform: 'uppercase'
                      }}>
                        {getProviderIcon(provider)}
                        {provider}
                        {provider === 'ollama' && <span style={{ 
                          fontSize: 9, 
                          background: 'rgba(16, 185, 129, 0.2)',
                          padding: '2px 6px',
                          borderRadius: 4
                        }}>LOCAL</span>}
                      </div>
                      {providerModels.map(model => (
                        <button
                          key={model.id}
                          onClick={() => {
                            setSelectedModel(model.id);
                            setShowModelDropdown(false);
                          }}
                          style={{
                            display: 'block',
                            width: '100%',
                            padding: '8px 12px',
                            textAlign: 'left',
                            background: model.id === selectedModel ? 'var(--bg-hover)' : 'transparent',
                            border: 'none',
                            borderRadius: 'var(--radius-sm)',
                            color: 'var(--text-primary)',
                            cursor: 'pointer',
                            fontSize: 13
                          }}
                        >
                          {model.name}
                        </button>
                      ))}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </header>

      <div className="page-content">
        {!schemaRegistered && (
          <div
            style={{
              padding: 20,
              background: 'linear-gradient(135deg, rgba(0, 212, 255, 0.1), rgba(124, 58, 237, 0.05))',
              borderRadius: 'var(--radius-lg)',
              border: '1px solid var(--border-glow)',
              marginBottom: 24,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}
          >
            <div>
              <div style={{ fontWeight: 600, marginBottom: 4 }}>Register Sample Schema</div>
              <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                Load an e-commerce database schema to start generating SQL queries
              </div>
            </div>
            <button className="btn btn-primary" onClick={registerSampleSchema}>
              <Database size={18} />
              Load Schema
            </button>
          </div>
        )}

        <div className="grid-2">
          {/* Query Input */}
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">
                <FileText size={20} style={{ marginRight: 8 }} />
                Ask a Question
              </h2>
            </div>

            <div style={{ marginBottom: 16 }}>
              <textarea
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Describe what data you want to retrieve..."
                style={{ minHeight: 120 }}
              />
            </div>

            <button
              className="btn btn-primary"
              onClick={generateSQL}
              disabled={loading || !question.trim() || !schemaRegistered}
              style={{ width: '100%' }}
            >
              {loading ? (
                <>
                  <div className="spinner" />
                  Generating...
                </>
              ) : (
                <>
                  <Play size={18} />
                  Generate SQL
                </>
              )}
            </button>

            <div style={{ marginTop: 20 }}>
              <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 8, color: 'var(--text-secondary)' }}>
                Example questions:
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {sampleQuestions.map((q, i) => (
                  <div
                    key={i}
                    onClick={() => setQuestion(q)}
                    style={{
                      padding: '8px 12px',
                      background: 'var(--bg-tertiary)',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: 13,
                      cursor: 'pointer',
                      transition: 'all 0.2s ease'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = 'var(--bg-hover)';
                      e.currentTarget.style.color = 'var(--accent-primary)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = 'var(--bg-tertiary)';
                      e.currentTarget.style.color = 'inherit';
                    }}
                  >
                    {q}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Result */}
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">
                <Code size={20} style={{ marginRight: 8 }} />
                Generated SQL
              </h2>
            </div>

            {result ? (
              <div>
                {result.success ? (
                  <>
                    <div className="code-block" style={{ marginBottom: 16 }}>
                      {result.sql || 'No SQL generated'}
                    </div>

                    {result.tables_used.length > 0 && (
                      <div style={{ marginBottom: 16 }}>
                        <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 8 }}>Tables used:</div>
                        <div style={{ display: 'flex', gap: 8 }}>
                          {result.tables_used.map((table, i) => (
                            <span key={i} className="tag info">{table}</span>
                          ))}
                        </div>
                      </div>
                    )}

                    {result.explanation && (
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 8 }}>Explanation:</div>
                        <div style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                          {result.explanation}
                        </div>
                      </div>
                    )}
                    
                    {/* Model & Latency */}
                    <div style={{ 
                      marginTop: 16, 
                      paddingTop: 16, 
                      borderTop: '1px solid var(--border-color)',
                      display: 'flex',
                      gap: 16,
                      fontSize: 12,
                      color: 'var(--text-muted)'
                    }}>
                      <span style={{ 
                        color: getProviderColor(currentModel?.provider || 'openai'), 
                        display: 'flex', 
                        alignItems: 'center', 
                        gap: 4 
                      }}>
                        {getProviderIcon(currentModel?.provider || 'openai')}
                        {result.model || selectedModel}
                      </span>
                      {result.latency_ms && (
                        <span>
                          {result.latency_ms > 1000 
                            ? `${(result.latency_ms / 1000).toFixed(1)}s` 
                            : `${Math.round(result.latency_ms)}ms`}
                        </span>
                      )}
                    </div>
                  </>
                ) : (
                  <div
                    style={{
                      padding: 16,
                      background: 'rgba(239, 68, 68, 0.1)',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--accent-danger)',
                      color: 'var(--accent-danger)'
                    }}
                  >
                    {result.error || 'An error occurred'}
                  </div>
                )}
              </div>
            ) : (
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: 40,
                  color: 'var(--text-muted)',
                  textAlign: 'center'
                }}
              >
                <Database size={48} style={{ marginBottom: 16, opacity: 0.3 }} />
                <div>Enter a question to generate SQL</div>
              </div>
            )}
          </div>
        </div>

        {/* Schema Info */}
        {schemaRegistered && (
          <div className="card" style={{ marginTop: 24 }}>
            <div className="card-header">
              <h2 className="card-title">Database Schema: ecommerce</h2>
              <span className="tag success">Registered</span>
            </div>

            <div className="grid-3">
              {['customers', 'orders', 'products'].map((table) => (
                <div
                  key={table}
                  style={{
                    padding: 16,
                    background: 'var(--bg-tertiary)',
                    borderRadius: 'var(--radius-md)'
                  }}
                >
                  <div style={{ fontWeight: 600, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Database size={16} color="var(--accent-primary)" />
                    {table}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                    {table === 'customers' && 'id, name, email, created_at'}
                    {table === 'orders' && 'id, customer_id, total, status, created_at'}
                    {table === 'products' && 'id, name, price, category, stock'}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </>
  );
}

