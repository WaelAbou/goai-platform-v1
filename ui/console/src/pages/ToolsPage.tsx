import { useState, useEffect } from 'react';
import {
  Wrench,
  Play,
  Calculator,
  Globe,
  Code,
  Link,
  Clock,
  FileJson,
  Loader2,
  CheckCircle,
  XCircle,
  ChevronDown,
  ChevronUp,
  Sparkles
} from 'lucide-react';
import { useToast } from '../components/Toast';

interface Tool {
  name: string;
  description: string;
  parameters: Record<string, { type: string; description: string; required?: boolean }>;
}

const TOOL_ICONS: Record<string, React.ReactNode> = {
  calculator: <Calculator size={20} />,
  web_search: <Globe size={20} />,
  execute_python: <Code size={20} />,
  url_fetcher: <Link size={20} />,
  datetime: <Clock size={20} />,
  json_parser: <FileJson size={20} />
};

const TOOL_COLORS: Record<string, string> = {
  calculator: '#f59e0b',
  web_search: '#00d4ff',
  execute_python: '#10b981',
  url_fetcher: '#8b5cf6',
  datetime: '#ec4899',
  json_parser: '#6366f1'
};

const EXAMPLE_INPUTS: Record<string, string> = {
  calculator: '(25 * 4) + 100 / 5',
  web_search: 'latest developments in AI',
  execute_python: 'import math\nresult = [math.sqrt(x) for x in range(1, 6)]\nprint(result)',
  url_fetcher: 'https://api.github.com/zen',
  datetime: 'now',
  json_parser: '{"name": "GoAI", "version": "1.0", "features": ["RAG", "Agents"]}'
};

const API_BASE = 'http://localhost:8000/api/v1';

export default function ToolsPage() {
  const [tools, setTools] = useState<Tool[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTool, setSelectedTool] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<{ success: boolean; output: string; duration?: number } | null>(null);
  const [expandedTool, setExpandedTool] = useState<string | null>(null);
  
  const toast = useToast();

  useEffect(() => {
    fetchTools();
  }, []);

  const fetchTools = async () => {
    try {
      const res = await fetch(`${API_BASE}/agents/tools`);
      const data = await res.json();
      setTools(data.tools || []);
      if (data.tools?.length > 0) {
        setSelectedTool(data.tools[0].name);
        setInput(EXAMPLE_INPUTS[data.tools[0].name] || '');
      }
    } catch (error) {
      toast.error('Failed to load tools');
    } finally {
      setLoading(false);
    }
  };

  const runTool = async () => {
    if (!selectedTool || !input.trim()) return;
    
    setRunning(true);
    setResult(null);
    const startTime = Date.now();
    
    try {
      // Run tool via agent endpoint
      const res = await fetch(`${API_BASE}/agents/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task: `Use the ${selectedTool} tool with this input: ${input}`,
          tools: [selectedTool],
          max_iterations: 1
        })
      });
      
      const reader = res.body?.getReader();
      if (!reader) throw new Error('No response stream');
      
      let output = '';
      const decoder = new TextDecoder();
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value);
        const lines = chunk.split('\n').filter(l => l.startsWith('data: '));
        
        for (const line of lines) {
          const data = JSON.parse(line.slice(6));
          if (data.type === 'tool_result') {
            output = typeof data.data === 'string' ? data.data : JSON.stringify(data.data, null, 2);
          } else if (data.type === 'final') {
            if (!output && data.data) {
              output = data.data;
            }
          }
        }
      }
      
      setResult({
        success: true,
        output: output || 'Tool executed successfully',
        duration: Date.now() - startTime
      });
    } catch (error) {
      setResult({
        success: false,
        output: error instanceof Error ? error.message : 'Tool execution failed',
        duration: Date.now() - startTime
      });
    } finally {
      setRunning(false);
    }
  };

  const selectTool = (toolName: string) => {
    setSelectedTool(toolName);
    setInput(EXAMPLE_INPUTS[toolName] || '');
    setResult(null);
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
        <Loader2 size={32} className="spin" />
      </div>
    );
  }

  const currentTool = tools.find(t => t.name === selectedTool);

  return (
    <>
      <header className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 className="page-title">AI Tools</h1>
            <p className="page-subtitle">Test and explore available agent tools</p>
          </div>
          <div className="stat-badge">
            <Wrench size={16} />
            {tools.length} tools available
          </div>
        </div>
      </header>

      <div className="page-content">
        <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: 24 }}>
          {/* Tool List */}
          <div className="card" style={{ padding: 0 }}>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-color)' }}>
              <h3 style={{ margin: 0, fontSize: 14 }}>Available Tools</h3>
            </div>
            <div style={{ padding: 8 }}>
              {tools.map(tool => {
                const isSelected = selectedTool === tool.name;
                const isExpanded = expandedTool === tool.name;
                const color = TOOL_COLORS[tool.name] || '#00d4ff';
                
                return (
                  <div key={tool.name}>
                    <div
                      onClick={() => selectTool(tool.name)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 12,
                        padding: '12px 16px',
                        borderRadius: 'var(--radius-md)',
                        cursor: 'pointer',
                        background: isSelected ? `${color}15` : 'transparent',
                        border: isSelected ? `1px solid ${color}40` : '1px solid transparent',
                        marginBottom: 4,
                        transition: 'all 0.15s ease'
                      }}
                    >
                      <div style={{
                        width: 40,
                        height: 40,
                        borderRadius: 'var(--radius-md)',
                        background: `${color}20`,
                        color: color,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center'
                      }}>
                        {TOOL_ICONS[tool.name] || <Wrench size={20} />}
                      </div>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 600, fontSize: 14 }}>{tool.name}</div>
                        <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.3 }}>
                          {tool.description.slice(0, 50)}...
                        </div>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setExpandedTool(isExpanded ? null : tool.name);
                        }}
                        style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 4 }}
                      >
                        {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                      </button>
                    </div>
                    
                    {isExpanded && (
                      <div style={{
                        margin: '0 8px 8px',
                        padding: 12,
                        background: 'var(--bg-tertiary)',
                        borderRadius: 'var(--radius-sm)',
                        fontSize: 12
                      }}>
                        <p style={{ color: 'var(--text-secondary)', marginBottom: 8 }}>{tool.description}</p>
                        {Object.keys(tool.parameters || {}).length > 0 && (
                          <>
                            <div style={{ fontWeight: 600, marginBottom: 4 }}>Parameters:</div>
                            {Object.entries(tool.parameters).map(([name, param]) => (
                              <div key={name} style={{ color: 'var(--text-muted)', marginLeft: 8 }}>
                                • <code style={{ color }}>{name}</code>: {param.description}
                              </div>
                            ))}
                          </>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Tool Playground */}
          <div className="card">
            {currentTool ? (
              <>
                <div style={{ 
                  padding: '20px 24px', 
                  borderBottom: '1px solid var(--border-color)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 16
                }}>
                  <div style={{
                    width: 48,
                    height: 48,
                    borderRadius: 'var(--radius-md)',
                    background: `${TOOL_COLORS[currentTool.name] || '#00d4ff'}20`,
                    color: TOOL_COLORS[currentTool.name] || '#00d4ff',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}>
                    {TOOL_ICONS[currentTool.name] || <Wrench size={24} />}
                  </div>
                  <div>
                    <h2 style={{ margin: 0, fontSize: 18 }}>{currentTool.name}</h2>
                    <p style={{ margin: 0, fontSize: 13, color: 'var(--text-secondary)' }}>
                      {currentTool.description}
                    </p>
                  </div>
                </div>

                <div style={{ padding: 24 }}>
                  <label style={{ display: 'block', marginBottom: 8, fontWeight: 600 }}>
                    Input
                  </label>
                  <textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder={`Enter input for ${currentTool.name}...`}
                    style={{
                      width: '100%',
                      minHeight: currentTool.name === 'execute_python' ? 120 : 80,
                      fontFamily: currentTool.name === 'execute_python' || currentTool.name === 'json_parser' 
                        ? 'var(--font-mono)' : 'inherit'
                    }}
                  />
                  
                  <button
                    className="btn btn-primary"
                    onClick={runTool}
                    disabled={running || !input.trim()}
                    style={{ marginTop: 16 }}
                  >
                    {running ? (
                      <>
                        <Loader2 size={16} className="spin" />
                        Running...
                      </>
                    ) : (
                      <>
                        <Play size={16} />
                        Run Tool
                      </>
                    )}
                  </button>

                  {result && (
                    <div style={{
                      marginTop: 24,
                      padding: 16,
                      background: result.success ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                      border: `1px solid ${result.success ? '#10b981' : '#ef4444'}`,
                      borderRadius: 'var(--radius-md)'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                        {result.success ? (
                          <CheckCircle size={18} color="#10b981" />
                        ) : (
                          <XCircle size={18} color="#ef4444" />
                        )}
                        <span style={{ fontWeight: 600, color: result.success ? '#10b981' : '#ef4444' }}>
                          {result.success ? 'Success' : 'Error'}
                        </span>
                        {result.duration && (
                          <span style={{ fontSize: 12, color: 'var(--text-muted)', marginLeft: 'auto' }}>
                            {result.duration}ms
                          </span>
                        )}
                      </div>
                      <pre style={{
                        margin: 0,
                        padding: 12,
                        background: 'var(--bg-primary)',
                        borderRadius: 'var(--radius-sm)',
                        overflow: 'auto',
                        maxHeight: 300,
                        fontSize: 13,
                        fontFamily: 'var(--font-mono)'
                      }}>
                        {result.output}
                      </pre>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 300, color: 'var(--text-muted)' }}>
                <div style={{ textAlign: 'center' }}>
                  <Wrench size={48} style={{ opacity: 0.3, marginBottom: 16 }} />
                  <p>Select a tool to test</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Quick Examples */}
        <div className="card" style={{ marginTop: 24 }}>
          <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-color)' }}>
            <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
              <Sparkles size={18} color="var(--accent-primary)" />
              Quick Examples
            </h3>
          </div>
          <div style={{ padding: 16, display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
            {[
              { tool: 'calculator', input: '(100 * 12) / 4 + 50', label: 'Math calculation' },
              { tool: 'web_search', input: 'What is RAG in AI?', label: 'Web search' },
              { tool: 'datetime', input: 'now', label: 'Current time' },
              { tool: 'execute_python', input: 'print([x**2 for x in range(10)])', label: 'Python code' }
            ].map((ex, i) => (
              <button
                key={i}
                onClick={() => {
                  selectTool(ex.tool);
                  setInput(ex.input);
                }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                  padding: '12px 16px',
                  background: 'var(--bg-tertiary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: 'var(--radius-md)',
                  cursor: 'pointer',
                  textAlign: 'left',
                  transition: 'all 0.15s ease'
                }}
              >
                <div style={{ color: TOOL_COLORS[ex.tool] }}>
                  {TOOL_ICONS[ex.tool]}
                </div>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>{ex.label}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    {ex.input.slice(0, 30)}...
                  </div>
                </div>
              </button>
            ))}
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

