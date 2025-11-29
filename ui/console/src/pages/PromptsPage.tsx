import { useState, useEffect } from 'react';
import {
  BookOpen,
  Search,
  Plus,
  Star,
  Play,
  Edit3,
  Trash2,
  Copy,
  Tag,
  FolderOpen,
  ChevronRight,
  X,
  Sparkles,
  Code,
  FileText,
  Mail,
  Database,
  Users,
  BarChart3,
  Languages,
  CheckCircle,
  Clock,
  Loader2
} from 'lucide-react';

interface Prompt {
  id: string;
  name: string;
  description?: string;
  template: string;
  variables: string[];
  category: string;
  tags: string[];
  is_public: boolean;
  is_favorite: boolean;
  usage_count: number;
  created_at: string;
  author?: string;
}

interface ExecuteResult {
  prompt: string;
  response: string;
  model: string;
}

const API_BASE = 'http://localhost:8000/api/v1';

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  writing: <FileText size={16} />,
  coding: <Code size={16} />,
  education: <BookOpen size={16} />,
  productivity: <CheckCircle size={16} />,
  analysis: <BarChart3 size={16} />,
  general: <Sparkles size={16} />
};

const CATEGORY_COLORS: Record<string, string> = {
  writing: '#10b981',
  coding: '#00d4ff',
  education: '#8b5cf6',
  productivity: '#f59e0b',
  analysis: '#ec4899',
  general: '#6b7280'
};

export default function PromptsPage() {
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [showFavorites, setShowFavorites] = useState(false);
  
  // Selected prompt for detail view
  const [selectedPrompt, setSelectedPrompt] = useState<Prompt | null>(null);
  const [variableValues, setVariableValues] = useState<Record<string, string>>({});
  const [executing, setExecuting] = useState(false);
  const [executeResult, setExecuteResult] = useState<ExecuteResult | null>(null);
  
  // Create/Edit modal
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingPrompt, setEditingPrompt] = useState<Prompt | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    template: '',
    category: 'general',
    tags: ''
  });

  useEffect(() => {
    fetchPrompts();
    fetchCategories();
  }, []);

  const fetchPrompts = async () => {
    try {
      const params = new URLSearchParams();
      if (searchQuery) params.append('search', searchQuery);
      if (selectedCategory) params.append('category', selectedCategory);
      if (showFavorites) params.append('favorites_only', 'true');
      
      const res = await fetch(`${API_BASE}/prompts?${params}`);
      const data = await res.json();
      setPrompts(data.prompts || []);
    } catch (error) {
      console.error('Failed to fetch prompts:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchCategories = async () => {
    try {
      const res = await fetch(`${API_BASE}/prompts/categories`);
      const data = await res.json();
      setCategories(data.categories || []);
    } catch (error) {
      console.error('Failed to fetch categories:', error);
    }
  };

  useEffect(() => {
    fetchPrompts();
  }, [searchQuery, selectedCategory, showFavorites]);

  const toggleFavorite = async (promptId: string) => {
    try {
      await fetch(`${API_BASE}/prompts/${promptId}/favorite`, { method: 'POST' });
      setPrompts(prev => prev.map(p => 
        p.id === promptId ? { ...p, is_favorite: !p.is_favorite } : p
      ));
      if (selectedPrompt?.id === promptId) {
        setSelectedPrompt(prev => prev ? { ...prev, is_favorite: !prev.is_favorite } : null);
      }
    } catch (error) {
      console.error('Failed to toggle favorite:', error);
    }
  };

  const executePrompt = async () => {
    if (!selectedPrompt) return;
    
    // Check required variables
    const missing = selectedPrompt.variables.filter(v => !variableValues[v]?.trim());
    if (missing.length > 0) {
      alert(`Please fill in: ${missing.join(', ')}`);
      return;
    }
    
    setExecuting(true);
    setExecuteResult(null);
    
    try {
      const res = await fetch(`${API_BASE}/prompts/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt_id: selectedPrompt.id,
          variables: variableValues
        })
      });
      
      const data = await res.json();
      setExecuteResult({
        prompt: data.prompt,
        response: data.response,
        model: data.model
      });
    } catch (error) {
      console.error('Failed to execute prompt:', error);
      alert('Failed to execute prompt');
    } finally {
      setExecuting(false);
    }
  };

  const createOrUpdatePrompt = async () => {
    try {
      const body = {
        name: formData.name,
        description: formData.description,
        template: formData.template,
        category: formData.category,
        tags: formData.tags.split(',').map(t => t.trim()).filter(Boolean)
      };
      
      if (editingPrompt) {
        await fetch(`${API_BASE}/prompts/${editingPrompt.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });
      } else {
        await fetch(`${API_BASE}/prompts`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });
      }
      
      setShowCreateModal(false);
      setEditingPrompt(null);
      setFormData({ name: '', description: '', template: '', category: 'general', tags: '' });
      fetchPrompts();
    } catch (error) {
      console.error('Failed to save prompt:', error);
    }
  };

  const deletePrompt = async (promptId: string) => {
    if (!confirm('Are you sure you want to delete this prompt?')) return;
    
    try {
      await fetch(`${API_BASE}/prompts/${promptId}`, { method: 'DELETE' });
      setPrompts(prev => prev.filter(p => p.id !== promptId));
      if (selectedPrompt?.id === promptId) {
        setSelectedPrompt(null);
      }
    } catch (error) {
      console.error('Failed to delete prompt:', error);
    }
  };

  const openEditModal = (prompt: Prompt) => {
    setEditingPrompt(prompt);
    setFormData({
      name: prompt.name,
      description: prompt.description || '',
      template: prompt.template,
      category: prompt.category,
      tags: prompt.tags.join(', ')
    });
    setShowCreateModal(true);
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <>
      <header className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 className="page-title">Prompt Library</h1>
            <p className="page-subtitle">Save, manage, and execute reusable prompt templates</p>
          </div>
          <button 
            className="btn btn-primary"
            onClick={() => {
              setEditingPrompt(null);
              setFormData({ name: '', description: '', template: '', category: 'general', tags: '' });
              setShowCreateModal(true);
            }}
          >
            <Plus size={18} />
            New Prompt
          </button>
        </div>
      </header>

      <div className="page-content">
        <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr 400px', gap: 24, height: 'calc(100vh - 180px)' }}>
          {/* Sidebar - Categories */}
          <div className="card" style={{ overflow: 'auto' }}>
            <div style={{ padding: 16 }}>
              {/* Search */}
              <div style={{ position: 'relative', marginBottom: 16 }}>
                <Search size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                <input
                  type="text"
                  placeholder="Search prompts..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{ paddingLeft: 36, width: '100%' }}
                />
              </div>
              
              {/* Filters */}
              <div style={{ marginBottom: 16 }}>
                <button
                  className={`btn btn-sm ${!selectedCategory && !showFavorites ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => { setSelectedCategory(null); setShowFavorites(false); }}
                  style={{ width: '100%', justifyContent: 'flex-start', marginBottom: 8 }}
                >
                  <FolderOpen size={16} />
                  All Prompts
                </button>
                <button
                  className={`btn btn-sm ${showFavorites ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => { setShowFavorites(!showFavorites); setSelectedCategory(null); }}
                  style={{ width: '100%', justifyContent: 'flex-start' }}
                >
                  <Star size={16} fill={showFavorites ? 'currentColor' : 'none'} />
                  Favorites
                </button>
              </div>
              
              {/* Categories */}
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1 }}>
                Categories
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                {categories.map(cat => (
                  <button
                    key={cat}
                    className={`btn btn-sm ${selectedCategory === cat ? 'btn-primary' : ''}`}
                    onClick={() => { setSelectedCategory(cat); setShowFavorites(false); }}
                    style={{ 
                      justifyContent: 'flex-start', 
                      background: selectedCategory === cat ? undefined : 'transparent',
                      border: 'none',
                      color: selectedCategory === cat ? undefined : CATEGORY_COLORS[cat] || 'var(--text-primary)'
                    }}
                  >
                    {CATEGORY_ICONS[cat] || <Tag size={16} />}
                    <span style={{ textTransform: 'capitalize' }}>{cat}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Main - Prompt List */}
          <div className="card" style={{ overflow: 'auto' }}>
            <div style={{ padding: 16 }}>
              {loading ? (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 60 }}>
                  <Loader2 size={24} className="spin" />
                </div>
              ) : prompts.length === 0 ? (
                <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>
                  <BookOpen size={48} style={{ opacity: 0.3, marginBottom: 16 }} />
                  <p>No prompts found</p>
                  <p style={{ fontSize: 13 }}>Create your first prompt to get started!</p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {prompts.map(prompt => (
                    <div
                      key={prompt.id}
                      onClick={() => {
                        setSelectedPrompt(prompt);
                        setVariableValues({});
                        setExecuteResult(null);
                      }}
                      style={{
                        padding: 16,
                        background: selectedPrompt?.id === prompt.id ? 'rgba(0, 212, 255, 0.1)' : 'var(--bg-tertiary)',
                        borderRadius: 'var(--radius-md)',
                        cursor: 'pointer',
                        border: selectedPrompt?.id === prompt.id ? '1px solid var(--accent-primary)' : '1px solid transparent',
                        transition: 'all 0.15s ease'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 8 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <span style={{ color: CATEGORY_COLORS[prompt.category] }}>
                            {CATEGORY_ICONS[prompt.category] || <Sparkles size={16} />}
                          </span>
                          <span style={{ fontWeight: 600 }}>{prompt.name}</span>
                          {prompt.is_favorite && (
                            <Star size={14} fill="#f59e0b" color="#f59e0b" />
                          )}
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                          <button
                            className="btn btn-sm"
                            onClick={(e) => { e.stopPropagation(); toggleFavorite(prompt.id); }}
                            style={{ padding: 4, background: 'transparent', border: 'none' }}
                            title="Toggle favorite"
                          >
                            <Star size={14} fill={prompt.is_favorite ? '#f59e0b' : 'none'} color={prompt.is_favorite ? '#f59e0b' : 'var(--text-muted)'} />
                          </button>
                          <button
                            className="btn btn-sm"
                            onClick={(e) => { e.stopPropagation(); openEditModal(prompt); }}
                            style={{ padding: 4, background: 'transparent', border: 'none' }}
                            title="Edit"
                          >
                            <Edit3 size={14} />
                          </button>
                          <button
                            className="btn btn-sm"
                            onClick={(e) => { e.stopPropagation(); deletePrompt(prompt.id); }}
                            style={{ padding: 4, background: 'transparent', border: 'none', color: '#ef4444' }}
                            title="Delete"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </div>
                      
                      {prompt.description && (
                        <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 8 }}>
                          {prompt.description}
                        </p>
                      )}
                      
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                        <span style={{ 
                          fontSize: 11, 
                          background: CATEGORY_COLORS[prompt.category] + '20',
                          color: CATEGORY_COLORS[prompt.category],
                          padding: '2px 8px',
                          borderRadius: 4,
                          textTransform: 'capitalize'
                        }}>
                          {prompt.category}
                        </span>
                        {prompt.variables.length > 0 && (
                          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                            {prompt.variables.length} variable{prompt.variables.length !== 1 ? 's' : ''}
                          </span>
                        )}
                        <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 'auto' }}>
                          <Clock size={10} style={{ marginRight: 4 }} />
                          Used {prompt.usage_count}x
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Right Panel - Execute */}
          <div className="card" style={{ overflow: 'auto', display: 'flex', flexDirection: 'column' }}>
            {selectedPrompt ? (
              <>
                <div style={{ padding: 16, borderBottom: '1px solid var(--border-color)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                    <h3 style={{ margin: 0 }}>{selectedPrompt.name}</h3>
                    <button
                      className="btn btn-sm btn-secondary"
                      onClick={() => copyToClipboard(selectedPrompt.template)}
                      title="Copy template"
                    >
                      <Copy size={14} />
                    </button>
                  </div>
                  <p style={{ fontSize: 13, color: 'var(--text-secondary)', margin: 0 }}>
                    {selectedPrompt.description}
                  </p>
                </div>
                
                <div style={{ padding: 16, flex: 1, overflow: 'auto' }}>
                  {/* Template Preview */}
                  <div style={{ marginBottom: 16 }}>
                    <label style={{ display: 'block', marginBottom: 8, fontWeight: 500, fontSize: 12, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                      Template
                    </label>
                    <div style={{ 
                      background: 'var(--bg-primary)', 
                      padding: 12, 
                      borderRadius: 'var(--radius-sm)',
                      fontSize: 13,
                      fontFamily: 'monospace',
                      whiteSpace: 'pre-wrap',
                      maxHeight: 150,
                      overflow: 'auto'
                    }}>
                      {selectedPrompt.template}
                    </div>
                  </div>
                  
                  {/* Variables */}
                  {selectedPrompt.variables.length > 0 && (
                    <div style={{ marginBottom: 16 }}>
                      <label style={{ display: 'block', marginBottom: 12, fontWeight: 500, fontSize: 12, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                        Variables
                      </label>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                        {selectedPrompt.variables.map(variable => (
                          <div key={variable}>
                            <label style={{ display: 'block', marginBottom: 4, fontSize: 13, color: 'var(--accent-primary)' }}>
                              {`{{${variable}}}`}
                            </label>
                            <textarea
                              placeholder={`Enter ${variable}...`}
                              value={variableValues[variable] || ''}
                              onChange={(e) => setVariableValues(prev => ({ ...prev, [variable]: e.target.value }))}
                              style={{ width: '100%', minHeight: 60, resize: 'vertical' }}
                            />
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Execute Button */}
                  <button
                    className="btn btn-primary"
                    onClick={executePrompt}
                    disabled={executing}
                    style={{ width: '100%', marginBottom: 16 }}
                  >
                    {executing ? (
                      <>
                        <Loader2 size={18} className="spin" />
                        Executing...
                      </>
                    ) : (
                      <>
                        <Play size={18} />
                        Execute Prompt
                      </>
                    )}
                  </button>
                  
                  {/* Result */}
                  {executeResult && (
                    <div>
                      <label style={{ display: 'block', marginBottom: 8, fontWeight: 500, fontSize: 12, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                        Result
                        <span style={{ fontSize: 11, fontWeight: 400, marginLeft: 8, color: 'var(--text-muted)' }}>
                          ({executeResult.model})
                        </span>
                      </label>
                      <div style={{ 
                        background: 'var(--bg-primary)', 
                        padding: 12, 
                        borderRadius: 'var(--radius-sm)',
                        fontSize: 13,
                        whiteSpace: 'pre-wrap',
                        borderLeft: '3px solid var(--accent-primary)'
                      }}>
                        {executeResult.response}
                      </div>
                    </div>
                  )}
                </div>
                
                {/* Tags */}
                {selectedPrompt.tags.length > 0 && (
                  <div style={{ padding: 12, borderTop: '1px solid var(--border-color)', display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    {selectedPrompt.tags.map(tag => (
                      <span key={tag} style={{ 
                        fontSize: 11, 
                        background: 'var(--bg-tertiary)', 
                        padding: '2px 8px', 
                        borderRadius: 4 
                      }}>
                        #{tag}
                      </span>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 1, color: 'var(--text-muted)', textAlign: 'center', padding: 40 }}>
                <div>
                  <ChevronRight size={48} style={{ opacity: 0.3, marginBottom: 16 }} />
                  <p>Select a prompt to execute</p>
                  <p style={{ fontSize: 13 }}>Fill in variables and run with one click</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Create/Edit Modal */}
      {showCreateModal && (
        <div 
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0,0,0,0.7)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000
          }}
          onClick={() => setShowCreateModal(false)}
        >
          <div 
            className="card"
            style={{ width: 600, maxHeight: '80vh', overflow: 'auto' }}
            onClick={e => e.stopPropagation()}
          >
            <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ margin: 0 }}>{editingPrompt ? 'Edit Prompt' : 'Create New Prompt'}</h3>
              <button className="btn btn-sm" onClick={() => setShowCreateModal(false)} style={{ background: 'transparent', border: 'none' }}>
                <X size={20} />
              </button>
            </div>
            
            <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div>
                <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>Name *</label>
                <input
                  type="text"
                  placeholder="My Awesome Prompt"
                  value={formData.name}
                  onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  style={{ width: '100%' }}
                />
              </div>
              
              <div>
                <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>Description</label>
                <input
                  type="text"
                  placeholder="What does this prompt do?"
                  value={formData.description}
                  onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                  style={{ width: '100%' }}
                />
              </div>
              
              <div>
                <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>
                  Template *
                  <span style={{ fontSize: 12, fontWeight: 400, marginLeft: 8, color: 'var(--text-muted)' }}>
                    Use {"{{variable}}"} for placeholders
                  </span>
                </label>
                <textarea
                  placeholder="Write your prompt template here...&#10;&#10;Use {{topic}} to create a variable named 'topic'"
                  value={formData.template}
                  onChange={(e) => setFormData(prev => ({ ...prev, template: e.target.value }))}
                  style={{ width: '100%', minHeight: 150 }}
                />
              </div>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                <div>
                  <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>Category</label>
                  <select
                    value={formData.category}
                    onChange={(e) => setFormData(prev => ({ ...prev, category: e.target.value }))}
                    style={{ width: '100%' }}
                  >
                    <option value="general">General</option>
                    <option value="writing">Writing</option>
                    <option value="coding">Coding</option>
                    <option value="education">Education</option>
                    <option value="productivity">Productivity</option>
                    <option value="analysis">Analysis</option>
                  </select>
                </div>
                
                <div>
                  <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>Tags</label>
                  <input
                    type="text"
                    placeholder="tag1, tag2, tag3"
                    value={formData.tags}
                    onChange={(e) => setFormData(prev => ({ ...prev, tags: e.target.value }))}
                    style={{ width: '100%' }}
                  />
                </div>
              </div>
            </div>
            
            <div style={{ padding: '12px 20px', borderTop: '1px solid var(--border-color)', display: 'flex', justifyContent: 'flex-end', gap: 12 }}>
              <button className="btn btn-secondary" onClick={() => setShowCreateModal(false)}>
                Cancel
              </button>
              <button 
                className="btn btn-primary" 
                onClick={createOrUpdatePrompt}
                disabled={!formData.name || !formData.template}
              >
                {editingPrompt ? 'Update' : 'Create'} Prompt
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

