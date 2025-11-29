import { useState, useRef, useEffect } from 'react';
import { 
  Bot, 
  Send, 
  Wrench, 
  Calculator, 
  Globe, 
  Code, 
  Clock, 
  Link, 
  FileJson,
  Loader2,
  CheckCircle,
  AlertCircle,
  ChevronDown,
  Zap,
  Terminal,
  Search,
  Play,
  RotateCcw
} from 'lucide-react';
import axios from 'axios';

interface ToolCall {
  tool: string;
  arguments: Record<string, any>;
  result?: any;
  status: 'pending' | 'running' | 'success' | 'error';
}

interface AgentStep {
  type: 'thinking' | 'tool_call' | 'tool_result' | 'answer' | 'done';
  content?: string;
  tool?: string;
  arguments?: Record<string, any>;
  result?: any;
  iteration?: number;
  tools_used?: string[];
  latency_ms?: number;
}

interface AgentResult {
  answer: string;
  tools_used: string[];
  steps: any[];
  total_tokens: number;
  latency_ms: number;
  model: string;
}

const TOOL_ICONS: Record<string, React.ReactNode> = {
  calculator: <Calculator size={16} />,
  web_search: <Globe size={16} />,
  execute_python: <Code size={16} />,
  get_datetime: <Clock size={16} />,
  fetch_url: <Link size={16} />,
  parse_json: <FileJson size={16} />,
};

const TOOL_COLORS: Record<string, string> = {
  calculator: '#f59e0b',
  web_search: '#3b82f6',
  execute_python: '#10b981',
  get_datetime: '#8b5cf6',
  fetch_url: '#ec4899',
  parse_json: '#06b6d4',
};

const EXAMPLE_TASKS = [
  "What is 15% of 847 plus the square root of 144?",
  "Search the web for the latest news about AI",
  "What is the current date and time?",
  "Write a Python function to calculate fibonacci numbers",
  "Fetch and summarize the content from https://example.com",
];

export default function AgentsPage() {
  const [task, setTask] = useState('');
  const [loading, setLoading] = useState(false);
  const [steps, setSteps] = useState<AgentStep[]>([]);
  const [result, setResult] = useState<AgentResult | null>(null);
  const [useStreaming, setUseStreaming] = useState(true);
  const [selectedModel, setSelectedModel] = useState('gpt-4o-mini');
  const [tools, setTools] = useState<any[]>([]);
  const [showTools, setShowTools] = useState(false);
  const stepsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchTools();
  }, []);

  useEffect(() => {
    stepsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [steps]);

  const fetchTools = async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/v1/agents/tools');
      setTools(response.data.tools || []);
    } catch (error) {
      console.error('Failed to fetch tools:', error);
    }
  };

  const runAgent = async () => {
    if (!task.trim() || loading) return;

    setLoading(true);
    setSteps([]);
    setResult(null);

    if (useStreaming) {
      await runStreamingAgent();
    } else {
      await runBatchAgent();
    }
  };

  const runStreamingAgent = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/agents/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task,
          model: selectedModel,
          stream: true
        })
      });

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) throw new Error('No reader');

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ') && !line.includes('[DONE]')) {
            try {
              const data = JSON.parse(line.slice(6));
              setSteps(prev => [...prev, data]);

              if (data.type === 'done') {
                setResult({
                  answer: '',
                  tools_used: data.tools_used || [],
                  steps: [],
                  total_tokens: 0,
                  latency_ms: data.latency_ms || 0,
                  model: selectedModel
                });
              }
            } catch (e) {
              // Skip invalid JSON
            }
          }
        }
      }
    } catch (error) {
      console.error('Streaming error:', error);
      setSteps(prev => [...prev, { 
        type: 'answer', 
        content: 'Error: Failed to run agent. Please try again.' 
      }]);
    } finally {
      setLoading(false);
    }
  };

  const runBatchAgent = async () => {
    try {
      const response = await axios.post('http://localhost:8000/api/v1/agents/run', {
        task,
        model: selectedModel,
        stream: false
      });

      setResult(response.data);
      setSteps([{ type: 'answer', content: response.data.answer }]);
    } catch (error) {
      console.error('Agent error:', error);
      setSteps([{ 
        type: 'answer', 
        content: 'Error: Failed to run agent. Please try again.' 
      }]);
    } finally {
      setLoading(false);
    }
  };

  const resetAgent = () => {
    setTask('');
    setSteps([]);
    setResult(null);
  };

  const getStepIcon = (step: AgentStep) => {
    switch (step.type) {
      case 'thinking':
        return <Loader2 size={16} className="spin" style={{ color: 'var(--accent-primary)' }} />;
      case 'tool_call':
        return TOOL_ICONS[step.tool || ''] || <Wrench size={16} />;
      case 'tool_result':
        return <CheckCircle size={16} style={{ color: 'var(--accent-tertiary)' }} />;
      case 'answer':
        return <Bot size={16} style={{ color: 'var(--accent-primary)' }} />;
      case 'done':
        return <CheckCircle size={16} style={{ color: 'var(--accent-tertiary)' }} />;
      default:
        return <Zap size={16} />;
    }
  };

  const renderStepContent = (step: AgentStep) => {
    switch (step.type) {
      case 'thinking':
        return (
          <div style={{ color: 'var(--text-muted)' }}>
            Thinking... (iteration {step.iteration})
          </div>
        );
      
      case 'tool_call':
        return (
          <div>
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: 8,
              marginBottom: 8,
              color: TOOL_COLORS[step.tool || ''] || 'var(--accent-primary)'
            }}>
              {TOOL_ICONS[step.tool || ''] || <Wrench size={16} />}
              <span style={{ fontWeight: 600 }}>Calling: {step.tool}</span>
            </div>
            <pre style={{
              background: 'var(--bg-primary)',
              padding: 12,
              borderRadius: 'var(--radius-md)',
              fontSize: 12,
              overflow: 'auto',
              maxHeight: 150
            }}>
              {JSON.stringify(step.arguments, null, 2)}
            </pre>
          </div>
        );
      
      case 'tool_result':
        const isSuccess = step.result?.success !== false;
        return (
          <div>
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: 8,
              marginBottom: 8,
              color: isSuccess ? 'var(--accent-tertiary)' : 'var(--accent-danger)'
            }}>
              {isSuccess ? <CheckCircle size={16} /> : <AlertCircle size={16} />}
              <span style={{ fontWeight: 600 }}>Result from: {step.tool}</span>
            </div>
            <pre style={{
              background: 'var(--bg-primary)',
              padding: 12,
              borderRadius: 'var(--radius-md)',
              fontSize: 12,
              overflow: 'auto',
              maxHeight: 200
            }}>
              {JSON.stringify(step.result, null, 2)}
            </pre>
          </div>
        );
      
      case 'answer':
        return (
          <div style={{ 
            whiteSpace: 'pre-wrap',
            lineHeight: 1.6
          }}>
            {step.content}
          </div>
        );
      
      case 'done':
        return (
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: 12,
            color: 'var(--accent-tertiary)'
          }}>
            <CheckCircle size={16} />
            <span>Complete in {step.latency_ms?.toFixed(0)}ms</span>
            {step.tools_used && step.tools_used.length > 0 && (
              <span style={{ color: 'var(--text-muted)' }}>
                • Used: {step.tools_used.join(', ')}
              </span>
            )}
          </div>
        );
      
      default:
        return null;
    }
  };

  return (
    <>
      <header className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 className="page-title">
              <Bot size={28} style={{ marginRight: 12, color: 'var(--accent-primary)' }} />
              AI Agents
            </h1>
            <p className="page-subtitle">Autonomous AI that uses tools to complete tasks</p>
          </div>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            {/* Streaming Toggle */}
            <button
              className={`btn ${useStreaming ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setUseStreaming(!useStreaming)}
              style={{ display: 'flex', alignItems: 'center', gap: 6 }}
            >
              <Zap size={14} />
              {useStreaming ? 'Stream' : 'Batch'}
            </button>

            {/* Model Selector */}
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              style={{
                background: 'var(--bg-tertiary)',
                border: '1px solid var(--border-color)',
                borderRadius: 'var(--radius-md)',
                padding: '8px 12px',
                color: 'var(--text-primary)',
                cursor: 'pointer'
              }}
            >
              <option value="gpt-4o-mini">gpt-4o-mini</option>
              <option value="gpt-4o">gpt-4o</option>
              <option value="claude-3-sonnet-20240229">claude-3-sonnet</option>
            </select>

            {/* Tools Button */}
            <button
              className="btn btn-secondary"
              onClick={() => setShowTools(!showTools)}
            >
              <Wrench size={16} />
              Tools ({tools.length})
            </button>
          </div>
        </div>
      </header>

      <div className="page-content">
        <div className="grid-2" style={{ gap: 24 }}>
          {/* Left Panel - Input & Examples */}
          <div>
            {/* Task Input */}
            <div className="card" style={{ marginBottom: 24 }}>
              <div className="card-header">
                <h2 className="card-title">
                  <Terminal size={18} style={{ marginRight: 8 }} />
                  Task
                </h2>
              </div>

              <textarea
                value={task}
                onChange={(e) => setTask(e.target.value)}
                placeholder="Describe what you want the agent to do..."
                style={{ 
                  minHeight: 120,
                  marginBottom: 16,
                  resize: 'vertical'
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && e.metaKey) {
                    runAgent();
                  }
                }}
              />

              <div style={{ display: 'flex', gap: 12 }}>
                <button
                  className="btn btn-primary"
                  onClick={runAgent}
                  disabled={loading || !task.trim()}
                  style={{ flex: 1 }}
                >
                  {loading ? (
                    <>
                      <Loader2 size={18} className="spin" />
                      Running...
                    </>
                  ) : (
                    <>
                      <Play size={18} />
                      Run Agent
                    </>
                  )}
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={resetAgent}
                  disabled={loading}
                >
                  <RotateCcw size={18} />
                </button>
              </div>

              <div style={{ 
                marginTop: 12, 
                fontSize: 12, 
                color: 'var(--text-muted)',
                textAlign: 'center'
              }}>
                ⌘ + Enter to run
              </div>
            </div>

            {/* Example Tasks */}
            <div className="card">
              <div className="card-header">
                <h2 className="card-title">
                  <Zap size={18} style={{ marginRight: 8 }} />
                  Example Tasks
                </h2>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {EXAMPLE_TASKS.map((example, i) => (
                  <button
                    key={i}
                    onClick={() => setTask(example)}
                    style={{
                      background: 'var(--bg-tertiary)',
                      border: '1px solid var(--border-color)',
                      borderRadius: 'var(--radius-md)',
                      padding: '12px 16px',
                      textAlign: 'left',
                      cursor: 'pointer',
                      color: 'var(--text-secondary)',
                      fontSize: 13,
                      transition: 'all 0.15s ease'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = 'var(--accent-primary)';
                      e.currentTarget.style.color = 'var(--text-primary)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = 'var(--border-color)';
                      e.currentTarget.style.color = 'var(--text-secondary)';
                    }}
                  >
                    {example}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Right Panel - Execution Steps */}
          <div className="card" style={{ maxHeight: 'calc(100vh - 200px)', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div className="card-header">
              <h2 className="card-title">
                <Bot size={18} style={{ marginRight: 8 }} />
                Agent Execution
              </h2>
              {result && (
                <span style={{ 
                  fontSize: 12, 
                  color: 'var(--text-muted)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8
                }}>
                  <span style={{ color: 'var(--accent-tertiary)' }}>
                    {result.latency_ms?.toFixed(0)}ms
                  </span>
                  {result.tools_used?.length > 0 && (
                    <span>• {result.tools_used.length} tools</span>
                  )}
                </span>
              )}
            </div>

            <div style={{ 
              flex: 1, 
              overflow: 'auto', 
              padding: '0 4px'
            }}>
              {steps.length === 0 && !loading ? (
                <div style={{ 
                  display: 'flex', 
                  flexDirection: 'column',
                  alignItems: 'center', 
                  justifyContent: 'center',
                  height: '100%',
                  color: 'var(--text-muted)',
                  textAlign: 'center',
                  padding: 40
                }}>
                  <Bot size={48} style={{ opacity: 0.3, marginBottom: 16 }} />
                  <p>Enter a task and click "Run Agent"</p>
                  <p style={{ fontSize: 13, marginTop: 8 }}>
                    The agent will use tools to complete your request
                  </p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12, padding: '8px 0' }}>
                  {steps.map((step, i) => (
                    <div
                      key={i}
                      style={{
                        background: step.type === 'answer' 
                          ? 'linear-gradient(135deg, rgba(0, 212, 255, 0.1), rgba(124, 58, 237, 0.05))'
                          : 'var(--bg-tertiary)',
                        border: `1px solid ${step.type === 'answer' ? 'var(--border-glow)' : 'var(--border-color)'}`,
                        borderRadius: 'var(--radius-md)',
                        padding: 16
                      }}
                    >
                      <div style={{ 
                        display: 'flex', 
                        alignItems: 'center', 
                        gap: 8,
                        marginBottom: step.type !== 'done' && step.type !== 'thinking' ? 12 : 0,
                        fontSize: 12,
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px',
                        color: 'var(--text-muted)'
                      }}>
                        {getStepIcon(step)}
                        <span>{step.type.replace('_', ' ')}</span>
                      </div>
                      {renderStepContent(step)}
                    </div>
                  ))}
                  <div ref={stepsEndRef} />
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Tools Panel */}
        {showTools && (
          <div className="card" style={{ marginTop: 24 }}>
            <div className="card-header">
              <h2 className="card-title">
                <Wrench size={18} style={{ marginRight: 8 }} />
                Available Tools
              </h2>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setShowTools(false)}
              >
                Close
              </button>
            </div>

            <div className="grid-3">
              {tools.map((tool, i) => (
                <div
                  key={i}
                  style={{
                    background: 'var(--bg-tertiary)',
                    border: '1px solid var(--border-color)',
                    borderRadius: 'var(--radius-md)',
                    padding: 16
                  }}
                >
                  <div style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: 10,
                    marginBottom: 8
                  }}>
                    <span style={{ color: TOOL_COLORS[tool.name] || 'var(--accent-primary)' }}>
                      {TOOL_ICONS[tool.name] || <Wrench size={20} />}
                    </span>
                    <span style={{ fontWeight: 600 }}>{tool.name}</span>
                    <span 
                      className="tag info"
                      style={{ marginLeft: 'auto', fontSize: 10 }}
                    >
                      {tool.category}
                    </span>
                  </div>
                  <p style={{ 
                    fontSize: 13, 
                    color: 'var(--text-secondary)',
                    marginBottom: 12,
                    lineHeight: 1.5
                  }}>
                    {tool.description}
                  </p>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    <strong>Parameters:</strong>
                    <div style={{ marginTop: 4 }}>
                      {tool.parameters?.map((p: any, j: number) => (
                        <div key={j} style={{ marginLeft: 8 }}>
                          • <code style={{ color: 'var(--accent-primary)' }}>{p.name}</code>
                          <span style={{ color: 'var(--text-muted)' }}> ({p.type})</span>
                          {!p.required && <span style={{ color: 'var(--accent-warning)' }}> optional</span>}
                        </div>
                      ))}
                    </div>
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

