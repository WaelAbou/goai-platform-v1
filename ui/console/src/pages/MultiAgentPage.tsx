import { useState, useEffect, useRef } from 'react';
import {
  Users,
  Play,
  Loader2,
  ArrowRight,
  GitBranch,
  MessageSquare,
  Layers,
  ChevronRight,
  Sparkles,
  Code,
  Search,
  BarChart3,
  FileText,
  Eye,
  Briefcase
} from 'lucide-react';

interface AgentRole {
  name: string;
  icon: string;
  color: string;
  capabilities: string[];
}

interface TeamPreset {
  name: string;
  description: string;
  pattern: string;
  agents: string[];
}

interface AgentEvent {
  type: string;
  agent?: string;
  role?: string;
  result?: string;
  argument?: string;
  task?: string;
  plan?: any;
  step?: number;
  total_steps?: number;
  round?: number;
  total_rounds?: number;
  final_result?: string;
  [key: string]: any;
}

const API_BASE = 'http://localhost:8000/api/v1';

const ROLE_ICONS: Record<string, React.ReactNode> = {
  coordinator: <Briefcase size={18} />,
  researcher: <Search size={18} />,
  coder: <Code size={18} />,
  analyst: <BarChart3 size={18} />,
  writer: <FileText size={18} />,
  critic: <Eye size={18} />
};

const ROLE_COLORS: Record<string, string> = {
  coordinator: '#8b5cf6',
  researcher: '#00d4ff',
  coder: '#10b981',
  analyst: '#f59e0b',
  writer: '#ec4899',
  critic: '#ef4444'
};

const PATTERN_ICONS: Record<string, React.ReactNode> = {
  sequential: <ArrowRight size={18} />,
  parallel: <GitBranch size={18} />,
  debate: <MessageSquare size={18} />,
  hierarchical: <Layers size={18} />
};

export default function MultiAgentPage() {
  const [roles, setRoles] = useState<Record<string, AgentRole>>({});
  const [teams, setTeams] = useState<Record<string, TeamPreset>>({});
  const [loading, setLoading] = useState(true);
  
  // Task configuration
  const [task, setTask] = useState('');
  const [pattern, setPattern] = useState<'sequential' | 'parallel' | 'debate' | 'hierarchical'>('hierarchical');
  const [selectedAgents, setSelectedAgents] = useState<string[]>(['researcher', 'analyst', 'writer']);
  const [debateRounds, setDebateRounds] = useState(2);
  
  // Execution state
  const [running, setRunning] = useState(false);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [finalResult, setFinalResult] = useState<string | null>(null);
  const eventsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchConfig();
  }, []);

  useEffect(() => {
    eventsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events]);

  const fetchConfig = async () => {
    try {
      const [rolesRes, teamsRes] = await Promise.all([
        fetch(`${API_BASE}/multi-agent/roles`),
        fetch(`${API_BASE}/multi-agent/teams`)
      ]);
      
      const rolesData = await rolesRes.json();
      const teamsData = await teamsRes.json();
      
      setRoles(rolesData.roles || {});
      setTeams(teamsData.teams || {});
    } catch (error) {
      console.error('Failed to fetch config:', error);
    } finally {
      setLoading(false);
    }
  };

  const runMultiAgent = async () => {
    if (!task.trim()) return;
    
    setRunning(true);
    setEvents([]);
    setFinalResult(null);
    
    try {
      const response = await fetch(`${API_BASE}/multi-agent/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task,
          pattern,
          agents: selectedAgents,
          debate_rounds: debateRounds,
          stream: true
        })
      });

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) return;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event = JSON.parse(line.slice(6));
              setEvents(prev => [...prev, event]);
              
              if (event.type === 'complete') {
                setFinalResult(event.final_result);
              }
            } catch {}
          }
        }
      }
    } catch (error) {
      console.error('Multi-agent run failed:', error);
    } finally {
      setRunning(false);
    }
  };

  const selectTeamPreset = (presetKey: string) => {
    const preset = teams[presetKey];
    if (preset) {
      setPattern(preset.pattern as any);
      setSelectedAgents(preset.agents.filter(a => a !== 'coordinator'));
    }
  };

  const toggleAgent = (agent: string) => {
    setSelectedAgents(prev => 
      prev.includes(agent) 
        ? prev.filter(a => a !== agent)
        : [...prev, agent]
    );
  };

  const renderEvent = (event: AgentEvent, index: number) => {
    const roleColor = event.role ? ROLE_COLORS[event.role] : 'var(--accent-primary)';
    
    switch (event.type) {
      case 'start':
        return (
          <div key={index} style={{
            padding: 16,
            background: 'rgba(0, 212, 255, 0.1)',
            borderRadius: 'var(--radius-md)',
            borderLeft: '4px solid var(--accent-primary)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              {PATTERN_ICONS[event.pattern || 'hierarchical']}
              <span style={{ fontWeight: 600, textTransform: 'capitalize' }}>
                {event.pattern} Collaboration Started
              </span>
            </div>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
              Task: {event.task}
            </div>
            {event.agents && (
              <div style={{ display: 'flex', gap: 8, marginTop: 8, flexWrap: 'wrap' }}>
                {event.agents.map((agent: string) => (
                  <span key={agent} style={{
                    padding: '4px 10px',
                    background: ROLE_COLORS[agent] + '20',
                    color: ROLE_COLORS[agent],
                    borderRadius: 'var(--radius-sm)',
                    fontSize: 12,
                    textTransform: 'capitalize'
                  }}>
                    {agent}
                  </span>
                ))}
              </div>
            )}
          </div>
        );
      
      case 'agent_start':
      case 'subtask_start':
        return (
          <div key={index} style={{
            padding: 12,
            background: 'var(--bg-tertiary)',
            borderRadius: 'var(--radius-sm)',
            borderLeft: `3px solid ${roleColor}`
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ color: roleColor }}>
                {ROLE_ICONS[event.role || 'analyst']}
              </span>
              <span style={{ fontWeight: 500, textTransform: 'capitalize' }}>
                {event.role} Agent
              </span>
              {event.step && (
                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                  Step {event.step}/{event.total_steps}
                </span>
              )}
              <Loader2 size={14} className="spin" style={{ marginLeft: 'auto', color: roleColor }} />
            </div>
            {event.task && (
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
                {event.task}
              </div>
            )}
          </div>
        );
      
      case 'agent_result':
      case 'subtask_complete':
        return (
          <div key={index} style={{
            padding: 16,
            background: 'var(--bg-tertiary)',
            borderRadius: 'var(--radius-md)',
            borderLeft: `4px solid ${roleColor}`
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
              <span style={{ color: roleColor }}>
                {ROLE_ICONS[event.role || 'analyst']}
              </span>
              <span style={{ fontWeight: 600, textTransform: 'capitalize', color: roleColor }}>
                {event.role} Result
              </span>
            </div>
            <div style={{ 
              whiteSpace: 'pre-wrap', 
              fontSize: 13, 
              lineHeight: 1.6,
              background: 'var(--bg-primary)',
              padding: 12,
              borderRadius: 'var(--radius-sm)'
            }}>
              {event.result}
            </div>
          </div>
        );
      
      case 'round_start':
        return (
          <div key={index} style={{
            padding: '8px 16px',
            background: 'rgba(124, 58, 237, 0.1)',
            borderRadius: 'var(--radius-sm)',
            display: 'flex',
            alignItems: 'center',
            gap: 8
          }}>
            <MessageSquare size={14} color="#8b5cf6" />
            <span style={{ color: '#8b5cf6', fontWeight: 500 }}>
              Debate Round {event.round}/{event.total_rounds}
            </span>
          </div>
        );
      
      case 'agent_argument':
        return (
          <div key={index} style={{
            padding: 16,
            background: 'var(--bg-tertiary)',
            borderRadius: 'var(--radius-md)',
            marginLeft: 20,
            borderLeft: `3px solid ${roleColor}`
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <span style={{ color: roleColor }}>
                {ROLE_ICONS[event.role || 'analyst']}
              </span>
              <span style={{ fontWeight: 500, textTransform: 'capitalize' }}>
                {event.role}
              </span>
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                Round {event.round}
              </span>
            </div>
            <div style={{ whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: 1.6 }}>
              {event.argument}
            </div>
          </div>
        );
      
      case 'plan_created':
        return (
          <div key={index} style={{
            padding: 16,
            background: 'rgba(139, 92, 246, 0.1)',
            borderRadius: 'var(--radius-md)',
            borderLeft: '4px solid #8b5cf6'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
              <Briefcase size={18} color="#8b5cf6" />
              <span style={{ fontWeight: 600, color: '#8b5cf6' }}>Coordinator's Plan</span>
            </div>
            {event.plan?.analysis && (
              <div style={{ fontSize: 13, marginBottom: 12 }}>
                {event.plan.analysis}
              </div>
            )}
            {event.plan?.subtasks && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {event.plan.subtasks.map((st: any, i: number) => (
                  <div key={i} style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    padding: '8px 12px',
                    background: 'var(--bg-primary)',
                    borderRadius: 'var(--radius-sm)'
                  }}>
                    <span style={{ color: ROLE_COLORS[st.agent], display: 'flex' }}>
                      {ROLE_ICONS[st.agent]}
                    </span>
                    <span style={{ fontWeight: 500, textTransform: 'capitalize', fontSize: 12 }}>
                      {st.agent}:
                    </span>
                    <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                      {st.task}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      
      case 'synthesis_start':
        return (
          <div key={index} style={{
            padding: 12,
            background: 'rgba(16, 185, 129, 0.1)',
            borderRadius: 'var(--radius-sm)',
            display: 'flex',
            alignItems: 'center',
            gap: 8
          }}>
            <Sparkles size={16} color="#10b981" />
            <span style={{ color: '#10b981', fontWeight: 500 }}>
              Synthesizing results...
            </span>
            <Loader2 size={14} className="spin" style={{ color: '#10b981' }} />
          </div>
        );
      
      case 'complete':
        return (
          <div key={index} style={{
            padding: 20,
            background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(0, 212, 255, 0.1))',
            borderRadius: 'var(--radius-md)',
            border: '1px solid rgba(16, 185, 129, 0.3)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
              <Sparkles size={20} color="#10b981" />
              <span style={{ fontWeight: 700, fontSize: 16, color: '#10b981' }}>
                ✅ Collaboration Complete
              </span>
            </div>
            <div style={{ 
              whiteSpace: 'pre-wrap', 
              fontSize: 14, 
              lineHeight: 1.7,
              background: 'var(--bg-primary)',
              padding: 16,
              borderRadius: 'var(--radius-sm)'
            }}>
              {event.final_result}
            </div>
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
            <h1 className="page-title">Multi-Agent Collaboration</h1>
            <p className="page-subtitle">AI agents working together to solve complex tasks</p>
          </div>
        </div>
      </header>

      <div className="page-content">
        <div style={{ display: 'grid', gridTemplateColumns: '350px 1fr', gap: 24, height: 'calc(100vh - 180px)' }}>
          {/* Configuration Panel */}
          <div className="card" style={{ overflow: 'auto' }}>
            <div style={{ padding: 16 }}>
              {/* Team Presets */}
              <div style={{ marginBottom: 20 }}>
                <label style={{ display: 'block', marginBottom: 12, fontWeight: 600, fontSize: 13, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                  Quick Team Presets
                </label>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {Object.entries(teams).map(([key, preset]) => (
                    <button
                      key={key}
                      onClick={() => selectTeamPreset(key)}
                      style={{
                        padding: '10px 14px',
                        background: 'var(--bg-tertiary)',
                        border: '1px solid var(--border-color)',
                        borderRadius: 'var(--radius-sm)',
                        textAlign: 'left',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease'
                      }}
                    >
                      <div style={{ fontWeight: 500, marginBottom: 2 }}>{preset.name}</div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{preset.description}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Pattern Selection */}
              <div style={{ marginBottom: 20 }}>
                <label style={{ display: 'block', marginBottom: 12, fontWeight: 600, fontSize: 13, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                  Collaboration Pattern
                </label>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  {(['sequential', 'parallel', 'debate', 'hierarchical'] as const).map(p => (
                    <button
                      key={p}
                      onClick={() => setPattern(p)}
                      style={{
                        padding: '12px',
                        background: pattern === p ? 'rgba(0, 212, 255, 0.15)' : 'var(--bg-tertiary)',
                        border: pattern === p ? '1px solid var(--accent-primary)' : '1px solid var(--border-color)',
                        borderRadius: 'var(--radius-sm)',
                        cursor: 'pointer',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        gap: 6
                      }}
                    >
                      <span style={{ color: pattern === p ? 'var(--accent-primary)' : 'var(--text-muted)' }}>
                        {PATTERN_ICONS[p]}
                      </span>
                      <span style={{ fontSize: 12, textTransform: 'capitalize', fontWeight: pattern === p ? 600 : 400 }}>
                        {p}
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Agent Selection */}
              {pattern !== 'hierarchical' && (
                <div style={{ marginBottom: 20 }}>
                  <label style={{ display: 'block', marginBottom: 12, fontWeight: 600, fontSize: 13, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                    Select Agents
                  </label>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {Object.entries(roles).filter(([key]) => key !== 'coordinator').map(([key, role]) => (
                      <label
                        key={key}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 10,
                          padding: '10px 12px',
                          background: selectedAgents.includes(key) ? `${ROLE_COLORS[key]}15` : 'var(--bg-tertiary)',
                          border: selectedAgents.includes(key) ? `1px solid ${ROLE_COLORS[key]}` : '1px solid transparent',
                          borderRadius: 'var(--radius-sm)',
                          cursor: 'pointer'
                        }}
                      >
                        <input
                          type="checkbox"
                          checked={selectedAgents.includes(key)}
                          onChange={() => toggleAgent(key)}
                          style={{ accentColor: ROLE_COLORS[key] }}
                        />
                        <span style={{ color: ROLE_COLORS[key] }}>
                          {ROLE_ICONS[key]}
                        </span>
                        <span style={{ fontWeight: 500, flex: 1 }}>{role.name}</span>
                      </label>
                    ))}
                  </div>
                </div>
              )}

              {/* Debate Rounds */}
              {pattern === 'debate' && (
                <div style={{ marginBottom: 20 }}>
                  <label style={{ display: 'block', marginBottom: 8, fontWeight: 600, fontSize: 13 }}>
                    Debate Rounds: {debateRounds}
                  </label>
                  <input
                    type="range"
                    min={1}
                    max={5}
                    value={debateRounds}
                    onChange={(e) => setDebateRounds(Number(e.target.value))}
                    style={{ width: '100%' }}
                  />
                </div>
              )}

              {/* Task Input */}
              <div style={{ marginBottom: 16 }}>
                <label style={{ display: 'block', marginBottom: 8, fontWeight: 600, fontSize: 13, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                  Task
                </label>
                <textarea
                  value={task}
                  onChange={(e) => setTask(e.target.value)}
                  placeholder="Describe the complex task for the team to collaborate on..."
                  style={{ width: '100%', minHeight: 100, resize: 'vertical' }}
                />
              </div>

              {/* Run Button */}
              <button
                className="btn btn-primary"
                onClick={runMultiAgent}
                disabled={running || !task.trim()}
                style={{ width: '100%' }}
              >
                {running ? (
                  <>
                    <Loader2 size={18} className="spin" />
                    Agents Collaborating...
                  </>
                ) : (
                  <>
                    <Users size={18} />
                    Start Collaboration
                  </>
                )}
              </button>

              {/* Example Tasks */}
              <div style={{ marginTop: 16, fontSize: 12, color: 'var(--text-muted)' }}>
                <strong>Example tasks:</strong>
                <ul style={{ marginTop: 8, paddingLeft: 16 }}>
                  <li style={{ cursor: 'pointer', marginBottom: 4 }} onClick={() => setTask("Research and write a comprehensive guide about React hooks best practices")}>
                    📝 Write a guide about React hooks
                  </li>
                  <li style={{ cursor: 'pointer', marginBottom: 4 }} onClick={() => setTask("Analyze the pros and cons of microservices vs monolithic architecture for a startup")}>
                    📊 Analyze microservices vs monolith
                  </li>
                  <li style={{ cursor: 'pointer', marginBottom: 4 }} onClick={() => setTask("Create a Python web scraper with error handling and rate limiting")}>
                    💻 Build a Python web scraper
                  </li>
                </ul>
              </div>
            </div>
          </div>

          {/* Collaboration View */}
          <div className="card" style={{ overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-color)' }}>
              <h3 style={{ margin: 0 }}>Agent Collaboration</h3>
            </div>
            
            <div style={{ flex: 1, overflow: 'auto', padding: 20 }}>
              {events.length === 0 ? (
                <div style={{ 
                  display: 'flex', 
                  flexDirection: 'column',
                  alignItems: 'center', 
                  justifyContent: 'center', 
                  height: '100%',
                  color: 'var(--text-muted)',
                  textAlign: 'center'
                }}>
                  <Users size={64} style={{ opacity: 0.2, marginBottom: 20 }} />
                  <h3 style={{ marginBottom: 8, color: 'var(--text-primary)' }}>Ready to Collaborate</h3>
                  <p style={{ maxWidth: 400 }}>
                    Configure your team of AI agents on the left and describe your task. 
                    Watch as they work together to solve complex problems!
                  </p>
                  <div style={{ display: 'flex', gap: 8, marginTop: 20 }}>
                    {Object.entries(ROLE_ICONS).slice(0, 5).map(([role, icon]) => (
                      <div key={role} style={{
                        width: 40,
                        height: 40,
                        borderRadius: '50%',
                        background: `${ROLE_COLORS[role]}20`,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: ROLE_COLORS[role]
                      }}>
                        {icon}
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  {events.map((event, index) => renderEvent(event, index))}
                  <div ref={eventsEndRef} />
                </div>
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

