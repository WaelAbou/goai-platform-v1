import { useState, useEffect } from 'react';
import {
  GitBranch,
  Play,
  Loader2,
  CheckCircle,
  XCircle,
  Clock,
  Plus,
  RefreshCw,
  ChevronRight,
  AlertCircle,
  Zap,
  FileCode,
  Box
} from 'lucide-react';
import { useToast } from '../components/Toast';

interface Workflow {
  name: string;
  description?: string;
  steps: number;
  version?: string;
}

interface WorkflowStep {
  step_name: string;
  status: string;
  output?: any;
  error?: string;
  duration_ms: number;
}

interface WorkflowResult {
  workflow_id: string;
  workflow_name: string;
  status: string;
  result?: Record<string, any>;
  error?: string;
  steps_completed: number;
  total_steps: number;
  step_results: WorkflowStep[];
  duration_ms: number;
}

interface Action {
  name: string;
  description?: string;
}

const API_BASE = 'http://localhost:8000/api/v1';

const STATUS_CONFIG: Record<string, { color: string; icon: React.ReactNode }> = {
  completed: { color: '#10b981', icon: <CheckCircle size={16} /> },
  failed: { color: '#ef4444', icon: <XCircle size={16} /> },
  running: { color: '#f59e0b', icon: <Loader2 size={16} className="spin" /> },
  pending: { color: '#64748b', icon: <Clock size={16} /> }
};

export default function WorkflowsPage() {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [actions, setActions] = useState<Action[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedWorkflow, setSelectedWorkflow] = useState<string | null>(null);
  const [payload, setPayload] = useState('{}');
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<WorkflowResult | null>(null);
  
  // Create workflow modal
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newWorkflow, setNewWorkflow] = useState({
    name: '',
    description: '',
    steps: '[{"action": "llm_call", "input": "${input}"}]'
  });
  
  const toast = useToast();

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [wfRes, actRes] = await Promise.all([
        fetch(`${API_BASE}/orchestrator/workflows`),
        fetch(`${API_BASE}/orchestrator/actions`)
      ]);
      
      const wfData = await wfRes.json();
      const actData = await actRes.json();
      
      setWorkflows(wfData.workflows || []);
      setActions(actData.actions || []);
      
      if (wfData.workflows?.length > 0) {
        setSelectedWorkflow(wfData.workflows[0].name);
      }
    } catch (error) {
      toast.error('Failed to load workflows');
    } finally {
      setLoading(false);
    }
  };

  const executeWorkflow = async () => {
    if (!selectedWorkflow) return;
    
    setRunning(true);
    setResult(null);
    
    try {
      let parsedPayload = {};
      try {
        parsedPayload = JSON.parse(payload);
      } catch {
        toast.error('Invalid JSON payload');
        setRunning(false);
        return;
      }
      
      const res = await fetch(`${API_BASE}/orchestrator/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workflow_name: selectedWorkflow,
          payload: parsedPayload
        })
      });
      
      const data = await res.json();
      setResult(data);
      
      if (data.status === 'completed') {
        toast.success('Workflow completed successfully!');
      } else if (data.status === 'failed') {
        toast.error('Workflow failed');
      }
    } catch (error) {
      toast.error('Failed to execute workflow');
    } finally {
      setRunning(false);
    }
  };

  const createWorkflow = async () => {
    try {
      let steps = [];
      try {
        steps = JSON.parse(newWorkflow.steps);
      } catch {
        toast.error('Invalid steps JSON');
        return;
      }
      
      const res = await fetch(`${API_BASE}/orchestrator/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newWorkflow.name,
          description: newWorkflow.description,
          steps: steps
        })
      });
      
      if (res.ok) {
        toast.success('Workflow created!');
        setShowCreateModal(false);
        setNewWorkflow({ name: '', description: '', steps: '[{"action": "llm_call", "input": "${input}"}]' });
        fetchData();
      } else {
        toast.error('Failed to create workflow');
      }
    } catch (error) {
      toast.error('Failed to create workflow');
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
        <Loader2 size={32} className="spin" />
      </div>
    );
  }

  return (
    <>
      <header className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 className="page-title">Workflows</h1>
            <p className="page-subtitle">Create and execute automated pipelines</p>
          </div>
          <div style={{ display: 'flex', gap: 12 }}>
            <button className="btn btn-secondary" onClick={fetchData}>
              <RefreshCw size={16} />
              Refresh
            </button>
            <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
              <Plus size={16} />
              New Workflow
            </button>
          </div>
        </div>
      </header>

      <div className="page-content">
        <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: 24 }}>
          {/* Workflow List */}
          <div>
            <div className="card" style={{ marginBottom: 16 }}>
              <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-color)' }}>
                <h3 style={{ margin: 0, fontSize: 14 }}>Workflows</h3>
              </div>
              <div style={{ padding: 8 }}>
                {workflows.length === 0 ? (
                  <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
                    No workflows yet
                  </div>
                ) : (
                  workflows.map(wf => (
                    <div
                      key={wf.name}
                      onClick={() => setSelectedWorkflow(wf.name)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 12,
                        padding: '12px 16px',
                        borderRadius: 'var(--radius-md)',
                        cursor: 'pointer',
                        background: selectedWorkflow === wf.name ? 'rgba(0, 212, 255, 0.1)' : 'transparent',
                        border: selectedWorkflow === wf.name ? '1px solid rgba(0, 212, 255, 0.3)' : '1px solid transparent',
                        marginBottom: 4
                      }}
                    >
                      <GitBranch size={18} color={selectedWorkflow === wf.name ? '#00d4ff' : 'var(--text-muted)'} />
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 600, fontSize: 14 }}>{wf.name}</div>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                          {wf.steps} steps
                        </div>
                      </div>
                      <ChevronRight size={16} color="var(--text-muted)" />
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Available Actions */}
            <div className="card">
              <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-color)' }}>
                <h3 style={{ margin: 0, fontSize: 14 }}>Available Actions</h3>
              </div>
              <div style={{ padding: 12 }}>
                {actions.map((action, i) => (
                  <div key={i} style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: 8, 
                    padding: '8px 12px',
                    fontSize: 13
                  }}>
                    <Zap size={14} color="#f59e0b" />
                    <code style={{ color: 'var(--accent-primary)' }}>{action.name || action}</code>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Workflow Execution */}
          <div className="card">
            {selectedWorkflow ? (
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
                    background: 'rgba(0, 212, 255, 0.15)',
                    color: '#00d4ff',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}>
                    <GitBranch size={24} />
                  </div>
                  <div>
                    <h2 style={{ margin: 0, fontSize: 18 }}>{selectedWorkflow}</h2>
                    <p style={{ margin: 0, fontSize: 13, color: 'var(--text-secondary)' }}>
                      {workflows.find(w => w.name === selectedWorkflow)?.description || 'Execute this workflow'}
                    </p>
                  </div>
                </div>

                <div style={{ padding: 24 }}>
                  <label style={{ display: 'block', marginBottom: 8, fontWeight: 600 }}>
                    Input Payload (JSON)
                  </label>
                  <textarea
                    value={payload}
                    onChange={(e) => setPayload(e.target.value)}
                    placeholder='{"input": "your input here"}'
                    style={{
                      width: '100%',
                      minHeight: 100,
                      fontFamily: 'var(--font-mono)',
                      fontSize: 13
                    }}
                  />
                  
                  <button
                    className="btn btn-primary"
                    onClick={executeWorkflow}
                    disabled={running}
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
                        Execute Workflow
                      </>
                    )}
                  </button>

                  {/* Results */}
                  {result && (
                    <div style={{ marginTop: 24 }}>
                      <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 12,
                        marginBottom: 16,
                        padding: 16,
                        background: result.status === 'completed' ? 'rgba(16, 185, 129, 0.1)' : 
                                   result.status === 'failed' ? 'rgba(239, 68, 68, 0.1)' : 'var(--bg-tertiary)',
                        border: `1px solid ${result.status === 'completed' ? '#10b981' : 
                                            result.status === 'failed' ? '#ef4444' : 'var(--border-color)'}`,
                        borderRadius: 'var(--radius-md)'
                      }}>
                        {STATUS_CONFIG[result.status]?.icon}
                        <div>
                          <div style={{ fontWeight: 600, color: STATUS_CONFIG[result.status]?.color }}>
                            {result.status.charAt(0).toUpperCase() + result.status.slice(1)}
                          </div>
                          <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                            {result.steps_completed}/{result.total_steps} steps • {result.duration_ms.toFixed(0)}ms
                          </div>
                        </div>
                      </div>

                      {/* Step Results */}
                      {result.step_results.length > 0 && (
                        <div style={{ marginBottom: 16 }}>
                          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase' }}>
                            Steps
                          </div>
                          {result.step_results.map((step, i) => (
                            <div
                              key={i}
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: 12,
                                padding: 12,
                                background: 'var(--bg-tertiary)',
                                borderRadius: 'var(--radius-sm)',
                                marginBottom: 8
                              }}
                            >
                              <span style={{ color: STATUS_CONFIG[step.status]?.color }}>
                                {STATUS_CONFIG[step.status]?.icon}
                              </span>
                              <div style={{ flex: 1 }}>
                                <div style={{ fontWeight: 500, fontSize: 13 }}>{step.step_name}</div>
                                {step.error && (
                                  <div style={{ fontSize: 12, color: '#ef4444' }}>{step.error}</div>
                                )}
                              </div>
                              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                                {step.duration_ms.toFixed(0)}ms
                              </div>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Output */}
                      {result.result && (
                        <div>
                          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase' }}>
                            Output
                          </div>
                          <pre style={{
                            padding: 16,
                            background: 'var(--bg-tertiary)',
                            borderRadius: 'var(--radius-md)',
                            overflow: 'auto',
                            maxHeight: 200,
                            fontSize: 12,
                            fontFamily: 'var(--font-mono)'
                          }}>
                            {JSON.stringify(result.result, null, 2)}
                          </pre>
                        </div>
                      )}

                      {result.error && (
                        <div style={{
                          padding: 12,
                          background: 'rgba(239, 68, 68, 0.1)',
                          border: '1px solid #ef4444',
                          borderRadius: 'var(--radius-sm)',
                          display: 'flex',
                          alignItems: 'center',
                          gap: 8,
                          fontSize: 13,
                          color: '#ef4444'
                        }}>
                          <AlertCircle size={16} />
                          {result.error}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 300, color: 'var(--text-muted)' }}>
                <div style={{ textAlign: 'center' }}>
                  <GitBranch size={48} style={{ opacity: 0.3, marginBottom: 16 }} />
                  <p>Select a workflow to execute</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Create Workflow Modal */}
      {showCreateModal && (
        <div 
          style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            background: 'rgba(0,0,0,0.7)', display: 'flex',
            alignItems: 'center', justifyContent: 'center', zIndex: 1000
          }}
          onClick={() => setShowCreateModal(false)}
        >
          <div className="card" style={{ width: 550 }} onClick={e => e.stopPropagation()}>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-color)' }}>
              <h3 style={{ margin: 0 }}>Create Workflow</h3>
            </div>
            
            <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div>
                <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>Name *</label>
                <input
                  value={newWorkflow.name}
                  onChange={(e) => setNewWorkflow(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="my-workflow"
                  style={{ width: '100%' }}
                />
              </div>
              
              <div>
                <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>Description</label>
                <input
                  value={newWorkflow.description}
                  onChange={(e) => setNewWorkflow(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="What does this workflow do?"
                  style={{ width: '100%' }}
                />
              </div>
              
              <div>
                <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>Steps (JSON Array)</label>
                <textarea
                  value={newWorkflow.steps}
                  onChange={(e) => setNewWorkflow(prev => ({ ...prev, steps: e.target.value }))}
                  placeholder='[{"action": "llm_call", "input": "${input}"}]'
                  style={{ width: '100%', minHeight: 120, fontFamily: 'var(--font-mono)', fontSize: 12 }}
                />
              </div>
            </div>
            
            <div style={{ padding: '12px 20px', borderTop: '1px solid var(--border-color)', display: 'flex', justifyContent: 'flex-end', gap: 12 }}>
              <button className="btn btn-secondary" onClick={() => setShowCreateModal(false)}>Cancel</button>
              <button className="btn btn-primary" onClick={createWorkflow} disabled={!newWorkflow.name.trim()}>
                Create Workflow
              </button>
            </div>
          </div>
        </div>
      )}

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

