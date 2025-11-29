import { useState, useEffect } from 'react';
import {
  Brain,
  Plus,
  Trash2,
  Edit3,
  Clock,
  Star,
  Search,
  RefreshCw,
  Sparkles,
  Target,
  FileText,
  MessageSquare,
  Lightbulb,
  Flag,
  Tag,
  X,
  Check,
  Loader2,
  Zap,
  Archive
} from 'lucide-react';
import { useToast } from '../components/Toast';

interface Memory {
  id: string;
  user_id: string;
  memory_type: 'short' | 'medium' | 'long';
  category: string;
  content: string;
  context?: string;
  importance: number;
  access_count: number;
  expires_at?: string;
  created_at: string;
  updated_at: string;
}

interface MemorySummary {
  by_type: Record<string, number>;
  by_category: Record<string, number>;
  total: number;
  top_memories: Array<{ content: string; category: string; importance: number }>;
}

const API_BASE = 'http://localhost:8000/api/v1';

const CATEGORY_CONFIG: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
  preference: { icon: <Star size={14} />, color: '#f59e0b', label: 'Preference' },
  fact: { icon: <FileText size={14} />, color: '#00d4ff', label: 'Fact' },
  instruction: { icon: <MessageSquare size={14} />, color: '#8b5cf6', label: 'Instruction' },
  skill: { icon: <Lightbulb size={14} />, color: '#10b981', label: 'Skill' },
  goal: { icon: <Flag size={14} />, color: '#ec4899', label: 'Goal' },
  context: { icon: <Target size={14} />, color: '#6366f1', label: 'Context' },
  history: { icon: <Clock size={14} />, color: '#64748b', label: 'History' },
  general: { icon: <Tag size={14} />, color: '#94a3b8', label: 'General' }
};

const TYPE_CONFIG: Record<string, { color: string; label: string; icon: React.ReactNode }> = {
  short: { color: '#f59e0b', label: 'Short-term', icon: <Zap size={12} /> },
  medium: { color: '#8b5cf6', label: 'Medium-term', icon: <Clock size={12} /> },
  long: { color: '#10b981', label: 'Long-term', icon: <Archive size={12} /> }
};

export default function MemoryPage() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [summary, setSummary] = useState<MemorySummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<string | null>(null);
  const [filterCategory, setFilterCategory] = useState<string | null>(null);
  
  // Modal state
  const [showModal, setShowModal] = useState(false);
  const [editingMemory, setEditingMemory] = useState<Memory | null>(null);
  const [formData, setFormData] = useState({
    content: '',
    memory_type: 'long' as 'short' | 'medium' | 'long',
    category: 'general',
    importance: 5
  });
  
  // Extract modal
  const [showExtractModal, setShowExtractModal] = useState(false);
  const [extractText, setExtractText] = useState('');
  const [extracting, setExtracting] = useState(false);
  
  const toast = useToast();

  useEffect(() => {
    fetchData();
  }, [filterType, filterCategory]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filterType) params.append('memory_type', filterType);
      if (filterCategory) params.append('category', filterCategory);
      
      const [memoriesRes, summaryRes] = await Promise.all([
        fetch(`${API_BASE}/memory?${params}`),
        fetch(`${API_BASE}/memory/summary`)
      ]);
      
      const memoriesData = await memoriesRes.json();
      const summaryData = await summaryRes.json();
      
      setMemories(memoriesData.memories || []);
      setSummary(summaryData);
    } catch (error) {
      console.error('Failed to fetch memories:', error);
      toast.error('Failed to load memories');
    } finally {
      setLoading(false);
    }
  };

  const createOrUpdateMemory = async () => {
    try {
      const url = editingMemory 
        ? `${API_BASE}/memory/${editingMemory.id}`
        : `${API_BASE}/memory`;
      
      const method = editingMemory ? 'PUT' : 'POST';
      
      await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      
      toast.success(editingMemory ? 'Memory updated!' : 'Memory created!');
      setShowModal(false);
      setEditingMemory(null);
      setFormData({ content: '', memory_type: 'long', category: 'general', importance: 5 });
      fetchData();
    } catch (error) {
      toast.error('Failed to save memory');
    }
  };

  const deleteMemory = async (memoryId: string) => {
    if (!confirm('Delete this memory?')) return;
    
    try {
      await fetch(`${API_BASE}/memory/${memoryId}`, { method: 'DELETE' });
      toast.success('Memory deleted');
      fetchData();
    } catch (error) {
      toast.error('Failed to delete memory');
    }
  };

  const extractMemories = async () => {
    if (!extractText.trim()) return;
    
    setExtracting(true);
    try {
      const res = await fetch(`${API_BASE}/memory/extract`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: extractText })
      });
      
      const data = await res.json();
      
      if (data.extracted > 0) {
        toast.success(`Extracted ${data.extracted} memories!`);
        setShowExtractModal(false);
        setExtractText('');
        fetchData();
      } else {
        toast.info('No memories extracted from text');
      }
    } catch (error) {
      toast.error('Failed to extract memories');
    } finally {
      setExtracting(false);
    }
  };

  const seedExamples = async () => {
    try {
      await fetch(`${API_BASE}/memory/seed-examples`, { method: 'POST' });
      toast.success('Example memories created!');
      fetchData();
    } catch (error) {
      toast.error('Failed to create examples');
    }
  };

  const openEditModal = (memory: Memory) => {
    setEditingMemory(memory);
    setFormData({
      content: memory.content,
      memory_type: memory.memory_type,
      category: memory.category,
      importance: memory.importance
    });
    setShowModal(true);
  };

  const filteredMemories = memories.filter(m => {
    if (!searchQuery) return true;
    return m.content.toLowerCase().includes(searchQuery.toLowerCase());
  });

  return (
    <>
      <header className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 className="page-title">User Memory</h1>
            <p className="page-subtitle">Short, medium, and long-term memories for personalization</p>
          </div>
          <div style={{ display: 'flex', gap: 12 }}>
            <button className="btn btn-secondary" onClick={() => setShowExtractModal(true)}>
              <Sparkles size={18} />
              Extract from Text
            </button>
            <button className="btn btn-primary" onClick={() => {
              setEditingMemory(null);
              setFormData({ content: '', memory_type: 'long', category: 'general', importance: 5 });
              setShowModal(true);
            }}>
              <Plus size={18} />
              Add Memory
            </button>
          </div>
        </div>
      </header>

      <div className="page-content">
        {/* Summary Cards */}
        {summary && (
          <div className="grid-4" style={{ marginBottom: 24 }}>
            {Object.entries(TYPE_CONFIG).map(([type, config]) => (
              <div 
                key={type}
                className="stat-card"
                style={{ 
                  cursor: 'pointer',
                  border: filterType === type ? `2px solid ${config.color}` : undefined
                }}
                onClick={() => setFilterType(filterType === type ? null : type)}
              >
                <div className="stat-icon" style={{ background: `${config.color}20`, color: config.color }}>
                  {config.icon}
                </div>
                <div className="stat-value">{summary.by_type[type] || 0}</div>
                <div className="stat-label">{config.label}</div>
              </div>
            ))}
            <div className="stat-card">
              <div className="stat-icon" style={{ background: 'rgba(0, 212, 255, 0.15)', color: '#00d4ff' }}>
                <Brain size={20} />
              </div>
              <div className="stat-value">{summary.total}</div>
              <div className="stat-label">Total Memories</div>
            </div>
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: 24 }}>
          {/* Sidebar - Categories */}
          <div className="card">
            <div style={{ padding: 16 }}>
              <div style={{ position: 'relative', marginBottom: 16 }}>
                <Search size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                <input
                  type="text"
                  placeholder="Search memories..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{ paddingLeft: 36, width: '100%' }}
                />
              </div>
              
              <div style={{ marginBottom: 16 }}>
                <button
                  className={`btn btn-sm ${!filterCategory ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setFilterCategory(null)}
                  style={{ width: '100%', justifyContent: 'flex-start', marginBottom: 8 }}
                >
                  <Brain size={16} />
                  All Categories
                </button>
              </div>
              
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1 }}>
                Filter by Category
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                {Object.entries(CATEGORY_CONFIG).map(([key, config]) => (
                  <button
                    key={key}
                    className={`btn btn-sm ${filterCategory === key ? 'btn-primary' : ''}`}
                    onClick={() => setFilterCategory(filterCategory === key ? null : key)}
                    style={{ 
                      justifyContent: 'flex-start', 
                      background: filterCategory === key ? undefined : 'transparent',
                      border: 'none',
                      color: filterCategory === key ? undefined : config.color
                    }}
                  >
                    {config.icon}
                    <span>{config.label}</span>
                    {summary?.by_category[key] && (
                      <span style={{ marginLeft: 'auto', fontSize: 11, opacity: 0.7 }}>
                        {summary.by_category[key]}
                      </span>
                    )}
                  </button>
                ))}
              </div>
              
              {/* Quick Actions */}
              <div style={{ marginTop: 24, paddingTop: 16, borderTop: '1px solid var(--border-color)' }}>
                <button 
                  className="btn btn-sm btn-secondary"
                  onClick={seedExamples}
                  style={{ width: '100%', marginBottom: 8 }}
                >
                  <Sparkles size={14} />
                  Seed Examples
                </button>
                <button 
                  className="btn btn-sm btn-secondary"
                  onClick={fetchData}
                  style={{ width: '100%' }}
                >
                  <RefreshCw size={14} />
                  Refresh
                </button>
              </div>
            </div>
          </div>

          {/* Memory List */}
          <div className="card" style={{ overflow: 'hidden' }}>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ margin: 0 }}>
                Memories
                {(filterType || filterCategory) && (
                  <span style={{ fontSize: 13, fontWeight: 400, color: 'var(--text-muted)', marginLeft: 8 }}>
                    (filtered)
                  </span>
                )}
              </h3>
              <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>
                {filteredMemories.length} memories
              </span>
            </div>
            
            <div style={{ padding: 16, maxHeight: 'calc(100vh - 400px)', overflow: 'auto' }}>
              {loading ? (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 60 }}>
                  <Loader2 size={24} className="spin" />
                </div>
              ) : filteredMemories.length === 0 ? (
                <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>
                  <Brain size={48} style={{ opacity: 0.3, marginBottom: 16 }} />
                  <p>No memories yet</p>
                  <p style={{ fontSize: 13 }}>Add memories to personalize your AI experience</p>
                  <button className="btn btn-primary" onClick={seedExamples} style={{ marginTop: 16 }}>
                    <Sparkles size={16} />
                    Create Example Memories
                  </button>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {filteredMemories.map(memory => {
                    const catConfig = CATEGORY_CONFIG[memory.category] || CATEGORY_CONFIG.general;
                    const typeConfig = TYPE_CONFIG[memory.memory_type];
                    
                    return (
                      <div
                        key={memory.id}
                        style={{
                          padding: 16,
                          background: 'var(--bg-tertiary)',
                          borderRadius: 'var(--radius-md)',
                          borderLeft: `4px solid ${catConfig.color}`
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 8 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <span style={{ color: catConfig.color }}>
                              {catConfig.icon}
                            </span>
                            <span style={{ 
                              fontSize: 11, 
                              padding: '2px 8px', 
                              background: `${typeConfig.color}20`,
                              color: typeConfig.color,
                              borderRadius: 4,
                              display: 'flex',
                              alignItems: 'center',
                              gap: 4
                            }}>
                              {typeConfig.icon}
                              {typeConfig.label}
                            </span>
                            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                              Importance: {memory.importance}/10
                            </span>
                          </div>
                          <div style={{ display: 'flex', gap: 4 }}>
                            <button
                              onClick={() => openEditModal(memory)}
                              style={{ padding: 4, background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}
                            >
                              <Edit3 size={14} />
                            </button>
                            <button
                              onClick={() => deleteMemory(memory.id)}
                              style={{ padding: 4, background: 'transparent', border: 'none', cursor: 'pointer', color: '#ef4444' }}
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                        </div>
                        
                        <p style={{ margin: 0, lineHeight: 1.6 }}>{memory.content}</p>
                        
                        <div style={{ display: 'flex', gap: 12, marginTop: 8, fontSize: 11, color: 'var(--text-muted)' }}>
                          <span>Created: {new Date(memory.created_at).toLocaleDateString()}</span>
                          {memory.expires_at && (
                            <span style={{ color: '#f59e0b' }}>
                              Expires: {new Date(memory.expires_at).toLocaleDateString()}
                            </span>
                          )}
                          <span>Accessed: {memory.access_count}x</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Create/Edit Modal */}
      {showModal && (
        <div 
          style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            background: 'rgba(0,0,0,0.7)', display: 'flex',
            alignItems: 'center', justifyContent: 'center', zIndex: 1000
          }}
          onClick={() => setShowModal(false)}
        >
          <div className="card" style={{ width: 500 }} onClick={e => e.stopPropagation()}>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ margin: 0 }}>{editingMemory ? 'Edit Memory' : 'Add Memory'}</h3>
              <button onClick={() => setShowModal(false)} style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}>
                <X size={20} />
              </button>
            </div>
            
            <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div>
                <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>Memory Content *</label>
                <textarea
                  value={formData.content}
                  onChange={(e) => setFormData(prev => ({ ...prev, content: e.target.value }))}
                  placeholder="What should I remember?"
                  style={{ width: '100%', minHeight: 80 }}
                />
              </div>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                <div>
                  <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>Type</label>
                  <select
                    value={formData.memory_type}
                    onChange={(e) => setFormData(prev => ({ ...prev, memory_type: e.target.value as any }))}
                    style={{ width: '100%' }}
                  >
                    <option value="short">Short-term (1 hour)</option>
                    <option value="medium">Medium-term (7 days)</option>
                    <option value="long">Long-term (Permanent)</option>
                  </select>
                </div>
                <div>
                  <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>Category</label>
                  <select
                    value={formData.category}
                    onChange={(e) => setFormData(prev => ({ ...prev, category: e.target.value }))}
                    style={{ width: '100%' }}
                  >
                    {Object.entries(CATEGORY_CONFIG).map(([key, config]) => (
                      <option key={key} value={key}>{config.label}</option>
                    ))}
                  </select>
                </div>
              </div>
              
              <div>
                <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>
                  Importance: {formData.importance}/10
                </label>
                <input
                  type="range"
                  min={1}
                  max={10}
                  value={formData.importance}
                  onChange={(e) => setFormData(prev => ({ ...prev, importance: Number(e.target.value) }))}
                  style={{ width: '100%' }}
                />
              </div>
            </div>
            
            <div style={{ padding: '12px 20px', borderTop: '1px solid var(--border-color)', display: 'flex', justifyContent: 'flex-end', gap: 12 }}>
              <button className="btn btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
              <button className="btn btn-primary" onClick={createOrUpdateMemory} disabled={!formData.content.trim()}>
                <Check size={16} />
                {editingMemory ? 'Update' : 'Create'} Memory
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Extract Modal */}
      {showExtractModal && (
        <div 
          style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            background: 'rgba(0,0,0,0.7)', display: 'flex',
            alignItems: 'center', justifyContent: 'center', zIndex: 1000
          }}
          onClick={() => setShowExtractModal(false)}
        >
          <div className="card" style={{ width: 550 }} onClick={e => e.stopPropagation()}>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Sparkles size={20} color="var(--accent-primary)" />
                <h3 style={{ margin: 0 }}>Extract Memories from Text</h3>
              </div>
              <button onClick={() => setShowExtractModal(false)} style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}>
                <X size={20} />
              </button>
            </div>
            
            <div style={{ padding: 20 }}>
              <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 16 }}>
                Paste any text (conversation, notes, profile) and AI will automatically extract memorable facts, preferences, and instructions.
              </p>
              <textarea
                value={extractText}
                onChange={(e) => setExtractText(e.target.value)}
                placeholder="Paste text here...&#10;&#10;Example:&#10;Hi, I'm a Python developer who loves clean code. I prefer concise answers with code examples. I'm currently learning about RAG systems for my startup project."
                style={{ width: '100%', minHeight: 150 }}
              />
            </div>
            
            <div style={{ padding: '12px 20px', borderTop: '1px solid var(--border-color)', display: 'flex', justifyContent: 'flex-end', gap: 12 }}>
              <button className="btn btn-secondary" onClick={() => setShowExtractModal(false)}>Cancel</button>
              <button className="btn btn-primary" onClick={extractMemories} disabled={!extractText.trim() || extracting}>
                {extracting ? <Loader2 size={16} className="spin" /> : <Sparkles size={16} />}
                {extracting ? 'Extracting...' : 'Extract Memories'}
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

