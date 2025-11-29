import { useState } from 'react';
import {
  Search,
  FileText,
  Loader2,
  Sparkles,
  Database,
  Clock,
  Tag,
  ChevronDown,
  ChevronUp,
  File
} from 'lucide-react';
import { useToast } from '../components/Toast';

interface SearchResult {
  id: string;
  content: string;
  filename?: string;
  similarity: number;
  metadata?: Record<string, any>;
}

const API_BASE = 'http://localhost:8000/api/v1';

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [topK, setTopK] = useState(10);
  const [searchTime, setSearchTime] = useState<number | null>(null);
  const [expandedResults, setExpandedResults] = useState<Set<string>>(new Set());
  
  const toast = useToast();

  const search = async () => {
    if (!query.trim()) return;
    
    setLoading(true);
    setResults([]);
    const startTime = Date.now();
    
    try {
      const res = await fetch(`${API_BASE}/retrieve/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, top_k: topK })
      });
      
      const data = await res.json();
      setResults(data.results || []);
      setSearchTime(Date.now() - startTime);
      
      if ((data.results || []).length === 0) {
        toast.info('No results found');
      }
    } catch (error) {
      toast.error('Search failed');
    } finally {
      setLoading(false);
    }
  };

  const toggleExpand = (id: string) => {
    setExpandedResults(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      search();
    }
  };

  return (
    <>
      <header className="page-header">
        <div>
          <h1 className="page-title">Semantic Search</h1>
          <p className="page-subtitle">Search your knowledge base with natural language</p>
        </div>
      </header>

      <div className="page-content">
        {/* Search Box */}
        <div className="card" style={{ marginBottom: 24 }}>
          <div style={{ padding: 24 }}>
            <div style={{ display: 'flex', gap: 12 }}>
              <div style={{ flex: 1, position: 'relative' }}>
                <Search 
                  size={20} 
                  style={{ 
                    position: 'absolute', 
                    left: 16, 
                    top: '50%', 
                    transform: 'translateY(-50%)',
                    color: 'var(--text-muted)'
                  }} 
                />
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Enter your search query... (e.g., 'How to implement authentication?')"
                  style={{
                    width: '100%',
                    padding: '14px 16px 14px 48px',
                    fontSize: 15,
                    background: 'var(--bg-tertiary)',
                    border: '2px solid var(--border-color)',
                    borderRadius: 'var(--radius-lg)',
                    color: 'var(--text-primary)',
                    transition: 'border-color 0.2s ease'
                  }}
                />
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <select
                  value={topK}
                  onChange={(e) => setTopK(Number(e.target.value))}
                  style={{ padding: '12px 16px', minWidth: 100 }}
                >
                  <option value={5}>Top 5</option>
                  <option value={10}>Top 10</option>
                  <option value={20}>Top 20</option>
                  <option value={50}>Top 50</option>
                </select>
                <button
                  className="btn btn-primary"
                  onClick={search}
                  disabled={loading || !query.trim()}
                  style={{ padding: '12px 24px' }}
                >
                  {loading ? (
                    <>
                      <Loader2 size={18} className="spin" />
                      Searching...
                    </>
                  ) : (
                    <>
                      <Sparkles size={18} />
                      Search
                    </>
                  )}
                </button>
              </div>
            </div>
            
            {/* Search Tips */}
            <div style={{ 
              marginTop: 16, 
              padding: 12, 
              background: 'var(--bg-secondary)', 
              borderRadius: 'var(--radius-md)',
              display: 'flex',
              gap: 24,
              fontSize: 12,
              color: 'var(--text-muted)'
            }}>
              <span>💡 <strong>Tip:</strong> Use natural language questions for best results</span>
              <span>📊 Uses vector similarity to find semantically related content</span>
            </div>
          </div>
        </div>

        {/* Results */}
        {searchTime !== null && (
          <div style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center',
            marginBottom: 16 
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <Database size={18} color="var(--accent-primary)" />
              <span style={{ fontWeight: 600 }}>{results.length} results found</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-muted)', fontSize: 13 }}>
              <Clock size={14} />
              {searchTime}ms
            </div>
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {results.map((result, index) => {
            const isExpanded = expandedResults.has(result.id);
            const similarityPercent = (result.similarity * 100).toFixed(1);
            
            return (
              <div
                key={result.id}
                className="card"
                style={{
                  overflow: 'hidden',
                  borderLeft: `4px solid ${
                    result.similarity > 0.8 ? '#10b981' :
                    result.similarity > 0.6 ? '#f59e0b' : '#64748b'
                  }`
                }}
              >
                <div
                  onClick={() => toggleExpand(result.id)}
                  style={{
                    padding: '16px 20px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: 16
                  }}
                >
                  <div style={{
                    width: 36,
                    height: 36,
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--bg-tertiary)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'var(--text-muted)',
                    fontWeight: 700,
                    fontSize: 14,
                    flexShrink: 0
                  }}>
                    {index + 1}
                  </div>
                  
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                      <File size={14} color="var(--accent-primary)" />
                      <span style={{ fontWeight: 600, fontSize: 14 }}>
                        {result.filename || result.metadata?.filename || 'Unknown Document'}
                      </span>
                      <div style={{
                        padding: '2px 8px',
                        borderRadius: 4,
                        fontSize: 11,
                        fontWeight: 600,
                        background: result.similarity > 0.8 ? 'rgba(16, 185, 129, 0.2)' :
                                  result.similarity > 0.6 ? 'rgba(245, 158, 11, 0.2)' : 'rgba(100, 116, 139, 0.2)',
                        color: result.similarity > 0.8 ? '#10b981' :
                               result.similarity > 0.6 ? '#f59e0b' : '#64748b'
                      }}>
                        {similarityPercent}% match
                      </div>
                    </div>
                    
                    <p style={{
                      margin: 0,
                      fontSize: 13,
                      color: 'var(--text-secondary)',
                      lineHeight: 1.6,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      display: '-webkit-box',
                      WebkitLineClamp: isExpanded ? 'unset' : 3,
                      WebkitBoxOrient: 'vertical'
                    }}>
                      {result.content}
                    </p>
                    
                    {result.metadata && Object.keys(result.metadata).length > 0 && isExpanded && (
                      <div style={{ 
                        marginTop: 12, 
                        padding: 12, 
                        background: 'var(--bg-tertiary)',
                        borderRadius: 'var(--radius-sm)'
                      }}>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase' }}>
                          Metadata
                        </div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                          {Object.entries(result.metadata).map(([key, value]) => (
                            <div key={key} style={{ 
                              display: 'flex', 
                              alignItems: 'center', 
                              gap: 4,
                              padding: '4px 8px',
                              background: 'var(--bg-secondary)',
                              borderRadius: 4,
                              fontSize: 11
                            }}>
                              <Tag size={10} />
                              <span style={{ color: 'var(--text-muted)' }}>{key}:</span>
                              <span>{String(value).slice(0, 50)}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                  
                  <button style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 4 }}>
                    {isExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        {results.length === 0 && !loading && searchTime === null && (
          <div className="card" style={{ padding: 60, textAlign: 'center' }}>
            <Search size={48} style={{ opacity: 0.3, marginBottom: 16 }} />
            <h3 style={{ marginBottom: 8 }}>Search Your Knowledge Base</h3>
            <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>
              Enter a query above to search through your ingested documents using semantic similarity
            </p>
          </div>
        )}
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

