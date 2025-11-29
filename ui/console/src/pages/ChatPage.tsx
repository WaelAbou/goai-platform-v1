import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, FileText, RefreshCw, Cpu, Cloud, ChevronDown, Zap, Database, MessageSquare, Files, Download, FileJson, FileCode, Loader2, ThumbsUp, ThumbsDown, MessageCircle, Copy, Check } from 'lucide-react';
import { useToast } from '../components/Toast';
import { ragApi, llmApi, getAuthHeaders } from '../api/client';

interface Source {
  content: string;
  score: number;
  page?: number;
  filename?: string;
  metadata?: Record<string, any>;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  timestamp: Date;
  model?: string;
  latency_ms?: number;
  isStreaming?: boolean;
  id?: string;
  feedback?: 'positive' | 'negative' | null;
  feedbackComment?: string;
}

interface ModelOption {
  id: string;
  name: string;
  provider: 'openai' | 'anthropic' | 'ollama';
  available: boolean;
}

interface Document {
  id: string;
  filename: string;
  display_name?: string;
  chunk_count: number;
  preview?: string;
}

type RagMode = 'none' | 'all' | 'selected';

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // Model selection
  const [models, setModels] = useState<ModelOption[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('gpt-4o-mini');
  const [showModelDropdown, setShowModelDropdown] = useState(false);
  
  // Streaming
  const [useStreaming, setUseStreaming] = useState(true);
  const [streamingContent, setStreamingContent] = useState('');
  
  // RAG Mode & Document Selection
  const [ragMode, setRagMode] = useState<RagMode>('all');
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedDocs, setSelectedDocs] = useState<Set<string>>(new Set());
  const [showDocSelector, setShowDocSelector] = useState(false);
  
  // Export
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [exporting, setExporting] = useState(false);
  
  // Feedback
  const [feedbackModal, setFeedbackModal] = useState<{ messageIndex: number; type: 'positive' | 'negative' } | null>(null);
  const [feedbackComment, setFeedbackComment] = useState('');
  
  // Copy
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const toast = useToast();

  useEffect(() => {
    createNewConversation();
    fetchModels();
    fetchDocuments();
  }, []);
  
  const fetchDocuments = async () => {
    try {
      const response = await ragApi.getDocuments({ limit: 100 });
      const docs = response.data.documents || [];
      setDocuments(docs.map((d: any) => ({
        id: d.id,
        filename: d.filename || d.id,
        display_name: d.display_name || d.filename || d.id,
        chunk_count: d.chunk_count || 0,
        preview: d.preview
      })));
    } catch (error) {
      console.error('Failed to fetch documents:', error);
    }
  };
  
  const fetchModels = async () => {
    try {
      const response = await llmApi.getProviders();
      const providers = response.data.providers;
      const modelList: ModelOption[] = [];
      
      // OpenAI models
      if (providers.openai?.available) {
        providers.openai.models.forEach((m: string) => {
          modelList.push({ id: m, name: m, provider: 'openai', available: true });
        });
      }
      
      // Anthropic models
      if (providers.anthropic?.available) {
        providers.anthropic.models.forEach((m: string) => {
          modelList.push({ id: m, name: m, provider: 'anthropic', available: true });
        });
      }
      
      // Ollama models
      if (providers.ollama?.available) {
        providers.ollama.models.forEach((m: string) => {
          modelList.push({ id: m, name: m, provider: 'ollama', available: true });
        });
      }
      
      setModels(modelList);
      
      // Auto-select first available
      if (modelList.length > 0) {
        setSelectedModel(modelList[0].id);
      }
    } catch (error) {
      console.error('Failed to fetch models:', error);
      // Fallback models
      setModels([
        { id: 'gpt-4o-mini', name: 'gpt-4o-mini', provider: 'openai', available: true },
        { id: 'gpt-4o', name: 'gpt-4o', provider: 'openai', available: true },
      ]);
    }
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const createNewConversation = async () => {
    try {
      const response = await ragApi.createConversation();
      setConversationId(response.data.conversation_id);
      setMessages([]);
    } catch (error) {
      console.error('Failed to create conversation:', error);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      role: 'user',
      content: input.trim(),
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    const query = input.trim();
    setInput('');
    setLoading(true);

    if (useStreaming) {
      // Streaming mode
      await sendStreamingMessage(query);
    } else {
      // Regular mode
      try {
        const response = conversationId
          ? await ragApi.chat(query, conversationId, selectedModel)
          : await ragApi.query(query, { top_k: 5, model: selectedModel });

        const assistantMessage: Message = {
          role: 'assistant',
          content: response.data.answer,
          sources: response.data.sources?.map((s: any) => ({
            content: s.content.slice(0, 200) + (s.content.length > 200 ? '...' : ''),
            score: s.score,
            page: s.metadata?.page,
            filename: s.metadata?.filename,
            metadata: s.metadata
          })),
          timestamp: new Date(),
          model: response.data.model || selectedModel,
          latency_ms: response.data.latency_ms
        };

        setMessages(prev => [...prev, assistantMessage]);
      } catch (error) {
        console.error('Failed to send message:', error);
        const errorMessage: Message = {
          role: 'assistant',
          content: 'Sorry, I encountered an error. Please try again.',
          timestamp: new Date()
        };
        setMessages(prev => [...prev, errorMessage]);
      } finally {
        setLoading(false);
      }
    }
  };

  const sendStreamingMessage = async (query: string) => {
    const startTime = Date.now();
    let sources: Array<{ content: string; score: number }> = [];
    let fullContent = '';

    // Add placeholder message for streaming
    const placeholderMessage: Message = {
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isStreaming: true
    };
    setMessages(prev => [...prev, placeholderMessage]);
    setStreamingContent('');

    try {
      const response = await fetch('http://localhost:8000/api/v1/stream/chat', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          ...getAuthHeaders()
        },
        body: JSON.stringify({
          query,
          model: selectedModel,
          top_k: 5,
          conversation_id: conversationId,
          rag_mode: ragMode,
          document_ids: ragMode === 'selected' ? Array.from(selectedDocs) : undefined
        })
      });

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) throw new Error('No reader available');

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              
              if (data.type === 'sources') {
                sources = data.data.map((s: any) => ({
                  content: s.content,
                  score: s.score,
                  page: s.metadata?.page,
                  filename: s.metadata?.filename,
                  metadata: s.metadata
                }));
              } else if (data.type === 'token') {
                // Handle both string and object token formats
                const token = typeof data.data === 'string' 
                  ? data.data 
                  : (data.data?.chunk || data.data?.content || '');
                fullContent += token;
                setStreamingContent(fullContent);
                
                // Update the streaming message
                setMessages(prev => {
                  const newMessages = [...prev];
                  const lastMsg = newMessages[newMessages.length - 1];
                  if (lastMsg.isStreaming) {
                    lastMsg.content = fullContent;
                  }
                  return newMessages;
                });
              } else if (data.type === 'done') {
                const latency = Date.now() - startTime;
                
                // Finalize the message
                setMessages(prev => {
                  const newMessages = [...prev];
                  const lastMsg = newMessages[newMessages.length - 1];
                  if (lastMsg.isStreaming) {
                    lastMsg.content = fullContent;
                    lastMsg.sources = sources;
                    lastMsg.model = data.data?.model || selectedModel;
                    lastMsg.latency_ms = latency;
                    lastMsg.isStreaming = false;
                  }
                  return newMessages;
                });
              } else if (data.type === 'error') {
                throw new Error(data.data);
              }
            } catch (e) {
              // Skip invalid JSON
            }
          }
        }
      }
    } catch (error) {
      console.error('Streaming error:', error);
      setMessages(prev => {
        const newMessages = [...prev];
        const lastMsg = newMessages[newMessages.length - 1];
        if (lastMsg.isStreaming) {
          lastMsg.content = 'Sorry, streaming failed. Please try again.';
          lastMsg.isStreaming = false;
        }
        return newMessages;
      });
    } finally {
      setLoading(false);
      setStreamingContent('');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const getProviderIcon = (provider: string) => {
    if (provider === 'ollama') return <Cpu size={14} />;
    return <Cloud size={14} />;
  };
  
  const submitFeedback = async (messageIndex: number, feedbackType: 'positive' | 'negative', comment?: string) => {
    const message = messages[messageIndex];
    const userMessage = messages[messageIndex - 1]; // Previous message is the user query
    
    if (!message || message.role !== 'assistant') return;
    
    try {
      await fetch('http://localhost:8000/api/v1/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message_id: message.id || `msg_${messageIndex}`,
          conversation_id: conversationId,
          query: userMessage?.content || '',
          response: message.content,
          feedback_type: feedbackType,
          comment: comment || undefined,
          model: message.model,
          sources_count: message.sources?.length || 0,
          latency_ms: message.latency_ms
        })
      });
      
      // Update message with feedback
      setMessages(prev => {
        const updated = [...prev];
        updated[messageIndex] = {
          ...updated[messageIndex],
          feedback: feedbackType,
          feedbackComment: comment
        };
        return updated;
      });
      
      // Close modal
      setFeedbackModal(null);
      setFeedbackComment('');
    } catch (error) {
      console.error('Failed to submit feedback:', error);
    }
  };
  
  const copyToClipboard = async (text: string, index: number) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedIndex(index);
      toast.success('Copied to clipboard!');
      setTimeout(() => setCopiedIndex(null), 2000);
    } catch (error) {
      toast.error('Failed to copy');
    }
  };

  const handleQuickFeedback = (messageIndex: number, feedbackType: 'positive' | 'negative') => {
    const message = messages[messageIndex];
    
    // If already has this feedback, remove it
    if (message.feedback === feedbackType) {
      setMessages(prev => {
        const updated = [...prev];
        updated[messageIndex] = { ...updated[messageIndex], feedback: null };
        return updated;
      });
      return;
    }
    
    // For negative feedback, show comment modal
    if (feedbackType === 'negative') {
      setFeedbackModal({ messageIndex, type: feedbackType });
    } else {
      // Positive feedback - submit immediately
      submitFeedback(messageIndex, feedbackType);
    }
  };
  
  const exportChat = async (format: 'markdown' | 'json' | 'html') => {
    if (messages.length === 0) return;
    
    setExporting(true);
    setShowExportMenu(false);
    
    try {
      const exportMessages = messages.map(m => ({
        role: m.role,
        content: m.content,
        timestamp: m.timestamp.toISOString(),
        sources: m.sources?.map(s => ({
          content: s.content,
          filename: s.filename,
          page: s.page
        }))
      }));
      
      const response = await fetch(`http://localhost:8000/api/v1/export/${format}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          messages: exportMessages,
          title: `Chat Export - ${new Date().toLocaleDateString()}`
        })
      });
      
      // Get raw content (not JSON)
      const content = await response.text();
      
      // Determine mime type
      const mimeTypes: Record<string, string> = {
        markdown: 'text/markdown',
        json: 'application/json',
        html: 'text/html'
      };
      
      // Create download
      const blob = new Blob([content], { type: mimeTypes[format] });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `chat-export-${Date.now()}.${format === 'markdown' ? 'md' : format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Export failed:', error);
      alert('Export failed. Please try again.');
    } finally {
      setExporting(false);
    }
  };
  
  const getProviderColor = (provider: string) => {
    switch (provider) {
      case 'ollama': return '#10b981';  // Green for local
      case 'openai': return '#00d4ff';  // Cyan for OpenAI
      case 'anthropic': return '#d97706'; // Orange for Anthropic
      default: return 'var(--text-muted)';
    }
  };
  
  const currentModel = models.find(m => m.id === selectedModel);

  return (
    <>
      <header className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 className="page-title">RAG Chat</h1>
            <p className="page-subtitle">Ask questions about your documents</p>
          </div>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            {/* RAG Mode Selector */}
            <div style={{ 
              display: 'flex', 
              background: 'var(--bg-tertiary)', 
              borderRadius: 'var(--radius-md)',
              padding: 2,
              gap: 2
            }}>
              <button
                className={`btn btn-sm ${ragMode === 'none' ? 'btn-primary' : ''}`}
                onClick={() => setRagMode('none')}
                style={{ 
                  padding: '6px 10px', 
                  fontSize: 12,
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: 4,
                  background: ragMode === 'none' ? undefined : 'transparent',
                  border: 'none'
                }}
                title="Chat without documents (pure LLM)"
              >
                <MessageSquare size={12} />
                No Docs
              </button>
              <button
                className={`btn btn-sm ${ragMode === 'all' ? 'btn-primary' : ''}`}
                onClick={() => setRagMode('all')}
                style={{ 
                  padding: '6px 10px', 
                  fontSize: 12,
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: 4,
                  background: ragMode === 'all' ? undefined : 'transparent',
                  border: 'none'
                }}
                title="Use all documents as context"
              >
                <Database size={12} />
                All Docs
              </button>
              <button
                className={`btn btn-sm ${ragMode === 'selected' ? 'btn-primary' : ''}`}
                onClick={() => {
                  setRagMode('selected');
                  setShowDocSelector(true);
                }}
                style={{ 
                  padding: '6px 10px', 
                  fontSize: 12,
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: 4,
                  background: ragMode === 'selected' ? undefined : 'transparent',
                  border: 'none'
                }}
                title="Select specific documents"
              >
                <Files size={12} />
                Select ({selectedDocs.size})
              </button>
            </div>
            
            {/* Streaming Toggle */}
            <button
              className={`btn ${useStreaming ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setUseStreaming(!useStreaming)}
              style={{ display: 'flex', alignItems: 'center', gap: 6 }}
              title={useStreaming ? 'Streaming enabled - tokens appear live' : 'Streaming disabled'}
            >
              <Zap size={14} />
              {useStreaming ? 'Stream' : 'Batch'}
            </button>
            
            {/* Model Selector */}
            <div style={{ position: 'relative' }}>
              <button
                className="btn btn-secondary"
                onClick={() => setShowModelDropdown(!showModelDropdown)}
                style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: 8,
                  minWidth: 180
                }}
              >
                <span style={{ color: getProviderColor(currentModel?.provider || 'openai') }}>
                  {getProviderIcon(currentModel?.provider || 'openai')}
                </span>
                <span style={{ flex: 1, textAlign: 'left' }}>
                  {selectedModel}
                </span>
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
                  minWidth: 220,
                  zIndex: 100,
                  boxShadow: '0 8px 32px rgba(0,0,0,0.4)'
                }}>
                  <div style={{ 
                    fontSize: 11, 
                    color: 'var(--text-muted)', 
                    marginBottom: 8,
                    padding: '0 8px'
                  }}>
                    SELECT MODEL
                  </div>
                  
                  {/* Group by provider */}
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
                          textTransform: 'uppercase',
                          letterSpacing: 1
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
                              background: model.id === selectedModel 
                                ? 'var(--bg-hover)' 
                                : 'transparent',
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
            
            {/* Export Button */}
            <div style={{ position: 'relative' }}>
              <button 
                className="btn btn-secondary"
                onClick={() => setShowExportMenu(!showExportMenu)}
                disabled={messages.length === 0 || exporting}
                title="Export conversation"
              >
                {exporting ? <Loader2 size={18} className="spin" /> : <Download size={18} />}
                Export
              </button>
              
              {showExportMenu && (
                <div style={{
                  position: 'absolute',
                  top: '100%',
                  right: 0,
                  marginTop: 4,
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: 'var(--radius-md)',
                  padding: 8,
                  minWidth: 160,
                  zIndex: 100,
                  boxShadow: '0 8px 32px rgba(0,0,0,0.4)'
                }}>
                  <button
                    onClick={() => exportChat('markdown')}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      width: '100%',
                      padding: '8px 12px',
                      background: 'transparent',
                      border: 'none',
                      borderRadius: 'var(--radius-sm)',
                      color: 'var(--text-primary)',
                      cursor: 'pointer',
                      textAlign: 'left'
                    }}
                  >
                    <FileCode size={16} color="#10b981" />
                    Markdown (.md)
                  </button>
                  <button
                    onClick={() => exportChat('json')}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      width: '100%',
                      padding: '8px 12px',
                      background: 'transparent',
                      border: 'none',
                      borderRadius: 'var(--radius-sm)',
                      color: 'var(--text-primary)',
                      cursor: 'pointer',
                      textAlign: 'left'
                    }}
                  >
                    <FileJson size={16} color="#00d4ff" />
                    JSON (.json)
                  </button>
                  <button
                    onClick={() => exportChat('html')}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      width: '100%',
                      padding: '8px 12px',
                      background: 'transparent',
                      border: 'none',
                      borderRadius: 'var(--radius-sm)',
                      color: 'var(--text-primary)',
                      cursor: 'pointer',
                      textAlign: 'left'
                    }}
                  >
                    <FileText size={16} color="#8b5cf6" />
                    HTML (.html)
                  </button>
                </div>
              )}
            </div>
            
            <button className="btn btn-secondary" onClick={createNewConversation}>
              <RefreshCw size={18} />
              New Chat
            </button>
          </div>
        </div>
      </header>

      <div className="chat-container">
        <div className="chat-messages">
          {messages.length === 0 && (
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
              color: 'var(--text-muted)',
              textAlign: 'center',
              gap: 16
            }}>
              <div style={{
                width: 80,
                height: 80,
                borderRadius: '50%',
                background: 'linear-gradient(135deg, rgba(0, 212, 255, 0.15), rgba(124, 58, 237, 0.1))',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <Bot size={40} color="var(--accent-primary)" />
              </div>
              <div>
                <h3 style={{ color: 'var(--text-primary)', marginBottom: 8 }}>Start a conversation</h3>
                <p style={{ maxWidth: 400 }}>
                  Ask questions about your ingested documents. I'll find relevant context and provide answers with source citations.
                </p>
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'center', marginTop: 8 }}>
                {['What is machine learning?', 'Tell me about Python', 'How does AI work?'].map((q, i) => (
                  <button
                    key={i}
                    className="btn btn-secondary"
                    style={{ fontSize: 13 }}
                    onClick={() => {
                      setInput(q);
                    }}
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, index) => (
            <div key={index} className={`message ${msg.role}`}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                <div style={{
                  width: 32,
                  height: 32,
                  borderRadius: '50%',
                  background: msg.role === 'user'
                    ? 'rgba(255,255,255,0.2)'
                    : 'var(--bg-hover)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0
                }}>
                  {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ whiteSpace: 'pre-wrap' }}>
                    {msg.content}
                    {msg.isStreaming && (
                      <span 
                        style={{ 
                          display: 'inline-block',
                          width: 8,
                          height: 16,
                          background: 'var(--accent-primary)',
                          marginLeft: 2,
                          animation: 'blink 1s infinite'
                        }} 
                      />
                    )}
                  </div>
                  
                  {/* Model, Latency & Feedback for assistant messages */}
                  {msg.role === 'assistant' && !msg.isStreaming && (
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 12,
                      marginTop: 12,
                      paddingTop: 8,
                      borderTop: '1px solid var(--border-color)'
                    }}>
                      {/* Model & Latency */}
                      <div style={{ display: 'flex', gap: 12, fontSize: 11, color: 'var(--text-muted)', flex: 1 }}>
                        {msg.model && (
                          <span style={{ 
                            display: 'flex', 
                            alignItems: 'center', 
                            gap: 4,
                            color: msg.model.includes('llama') ? '#10b981' : 'var(--accent-primary)'
                          }}>
                            {msg.model.includes('llama') ? <Cpu size={12} /> : <Cloud size={12} />}
                            {msg.model}
                          </span>
                        )}
                        {msg.latency_ms && (
                          <span>
                            {msg.latency_ms > 1000 
                              ? `${(msg.latency_ms / 1000).toFixed(1)}s` 
                              : `${Math.round(msg.latency_ms)}ms`}
                          </span>
                        )}
                      </div>
                      
                      {/* Action Buttons */}
                      <div style={{ display: 'flex', gap: 4 }}>
                        {/* Copy Button */}
                        <button
                          onClick={() => copyToClipboard(msg.content, index)}
                          title="Copy response"
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 4,
                            padding: '4px 8px',
                            background: copiedIndex === index ? 'rgba(16, 185, 129, 0.2)' : 'transparent',
                            border: copiedIndex === index ? '1px solid #10b981' : '1px solid var(--border-color)',
                            borderRadius: 'var(--radius-sm)',
                            color: copiedIndex === index ? '#10b981' : 'var(--text-muted)',
                            cursor: 'pointer',
                            fontSize: 12,
                            transition: 'all 0.15s ease'
                          }}
                        >
                          {copiedIndex === index ? <Check size={14} /> : <Copy size={14} />}
                        </button>
                        
                        {/* Feedback Buttons */}
                        <button
                          onClick={() => handleQuickFeedback(index, 'positive')}
                          title="Good response"
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 4,
                            padding: '4px 8px',
                            background: msg.feedback === 'positive' ? 'rgba(16, 185, 129, 0.2)' : 'transparent',
                            border: msg.feedback === 'positive' ? '1px solid #10b981' : '1px solid var(--border-color)',
                            borderRadius: 'var(--radius-sm)',
                            color: msg.feedback === 'positive' ? '#10b981' : 'var(--text-muted)',
                            cursor: 'pointer',
                            fontSize: 12,
                            transition: 'all 0.15s ease'
                          }}
                        >
                          <ThumbsUp size={14} fill={msg.feedback === 'positive' ? '#10b981' : 'none'} />
                        </button>
                        <button
                          onClick={() => handleQuickFeedback(index, 'negative')}
                          title="Bad response"
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 4,
                            padding: '4px 8px',
                            background: msg.feedback === 'negative' ? 'rgba(239, 68, 68, 0.2)' : 'transparent',
                            border: msg.feedback === 'negative' ? '1px solid #ef4444' : '1px solid var(--border-color)',
                            borderRadius: 'var(--radius-sm)',
                            color: msg.feedback === 'negative' ? '#ef4444' : 'var(--text-muted)',
                            cursor: 'pointer',
                            fontSize: 12,
                            transition: 'all 0.15s ease'
                          }}
                        >
                          <ThumbsDown size={14} fill={msg.feedback === 'negative' ? '#ef4444' : 'none'} />
                        </button>
                      </div>
                    </div>
                  )}
                  
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="message-sources">
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
                        <FileText size={14} />
                        <span>Sources ({msg.sources.length})</span>
                      </div>
                      {msg.sources.map((source, i) => (
                        <div
                          key={i}
                          style={{
                            fontSize: 12,
                            padding: '10px 12px',
                            background: 'var(--bg-primary)',
                            borderRadius: 'var(--radius-sm)',
                            marginTop: 6,
                            borderLeft: '2px solid var(--accent-primary)'
                          }}
                        >
                          <div style={{ 
                            display: 'flex', 
                            alignItems: 'center', 
                            gap: 8, 
                            marginBottom: 4,
                            fontSize: 11,
                            color: 'var(--accent-primary)'
                          }}>
                            <span>[{i + 1}]</span>
                            {source.filename && <span>📄 {source.filename}</span>}
                            {source.page && <span style={{ 
                              background: 'rgba(0, 212, 255, 0.15)', 
                              padding: '1px 6px', 
                              borderRadius: 4 
                            }}>Page {source.page}</span>}
                            <span style={{ marginLeft: 'auto', color: 'var(--text-muted)' }}>
                              {Math.round(source.score * 100)}% match
                            </span>
                          </div>
                          <div style={{ color: 'var(--text-secondary)' }}>
                            {source.content}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}

          {loading && (
            <div className="message assistant">
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div className="spinner" />
                <span>Thinking...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div className="chat-input-container">
          <div className="chat-input-wrapper">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask a question about your documents..."
              disabled={loading}
              style={{ flex: 1 }}
            />
            <button
              className="btn btn-primary btn-icon"
              onClick={sendMessage}
              disabled={loading || !input.trim()}
            >
              <Send size={20} />
            </button>
          </div>
          <div style={{ marginTop: 8, fontSize: 12, color: 'var(--text-muted)', textAlign: 'center' }}>
            Press Enter to send • Shift+Enter for new line
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

      {/* Feedback Comment Modal */}
      {feedbackModal && (
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
          onClick={() => { setFeedbackModal(null); setFeedbackComment(''); }}
        >
          <div 
            className="card"
            style={{ width: 450, padding: 0 }}
            onClick={e => e.stopPropagation()}
          >
            <div style={{ 
              padding: '16px 20px', 
              borderBottom: '1px solid var(--border-color)',
              display: 'flex',
              alignItems: 'center',
              gap: 12
            }}>
              <div style={{
                width: 36,
                height: 36,
                borderRadius: '50%',
                background: 'rgba(239, 68, 68, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <ThumbsDown size={18} color="#ef4444" />
              </div>
              <div>
                <h3 style={{ margin: 0, marginBottom: 2 }}>What went wrong?</h3>
                <p style={{ margin: 0, fontSize: 13, color: 'var(--text-muted)' }}>
                  Your feedback helps us improve
                </p>
              </div>
            </div>
            
            <div style={{ padding: 20 }}>
              <textarea
                placeholder="Tell us what was wrong with this response... (optional)"
                value={feedbackComment}
                onChange={(e) => setFeedbackComment(e.target.value)}
                style={{ width: '100%', minHeight: 100, resize: 'vertical' }}
                autoFocus
              />
              
              <div style={{ display: 'flex', gap: 8, marginTop: 8, flexWrap: 'wrap' }}>
                {['Incorrect information', 'Not helpful', 'Too long', 'Too short', 'Off topic', 'Other'].map(tag => (
                  <button
                    key={tag}
                    onClick={() => setFeedbackComment(prev => prev ? `${prev}, ${tag}` : tag)}
                    style={{
                      padding: '4px 10px',
                      fontSize: 12,
                      background: 'var(--bg-tertiary)',
                      border: '1px solid var(--border-color)',
                      borderRadius: 'var(--radius-sm)',
                      color: 'var(--text-secondary)',
                      cursor: 'pointer'
                    }}
                  >
                    {tag}
                  </button>
                ))}
              </div>
            </div>
            
            <div style={{ 
              padding: '12px 20px', 
              borderTop: '1px solid var(--border-color)',
              display: 'flex',
              justifyContent: 'flex-end',
              gap: 12
            }}>
              <button 
                className="btn btn-secondary"
                onClick={() => { setFeedbackModal(null); setFeedbackComment(''); }}
              >
                Cancel
              </button>
              <button 
                className="btn btn-primary"
                onClick={() => submitFeedback(feedbackModal.messageIndex, feedbackModal.type, feedbackComment)}
                style={{ background: '#ef4444' }}
              >
                <ThumbsDown size={16} />
                Submit Feedback
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Document Selector Modal */}
      {showDocSelector && (
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
          onClick={() => setShowDocSelector(false)}
        >
          <div 
            className="card"
            style={{
              width: 500,
              maxHeight: '70vh',
              overflow: 'hidden',
              display: 'flex',
              flexDirection: 'column'
            }}
            onClick={e => e.stopPropagation()}
          >
            <div style={{ 
              padding: '16px 20px', 
              borderBottom: '1px solid var(--border-color)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <h3 style={{ margin: 0 }}>Select Documents</h3>
              <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>
                {selectedDocs.size} selected
              </span>
            </div>
            
            <div style={{ 
              flex: 1, 
              overflow: 'auto', 
              padding: 16 
            }}>
              {documents.length === 0 ? (
                <div style={{ 
                  textAlign: 'center', 
                  color: 'var(--text-muted)', 
                  padding: 40 
                }}>
                  <Files size={40} style={{ opacity: 0.3, marginBottom: 12 }} />
                  <p>No documents ingested yet.</p>
                  <p style={{ fontSize: 13 }}>Upload documents in the Documents tab first.</p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {/* Select All / Clear All */}
                  <div style={{ 
                    display: 'flex', 
                    gap: 12, 
                    marginBottom: 8,
                    paddingBottom: 12,
                    borderBottom: '1px solid var(--border-color)'
                  }}>
                    <button
                      className="btn btn-sm btn-secondary"
                      onClick={() => setSelectedDocs(new Set(documents.map(d => d.id)))}
                    >
                      Select All
                    </button>
                    <button
                      className="btn btn-sm btn-secondary"
                      onClick={() => setSelectedDocs(new Set())}
                    >
                      Clear All
                    </button>
                  </div>
                  
                  {documents.map(doc => (
                    <label
                      key={doc.id}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 12,
                        padding: '12px 16px',
                        background: selectedDocs.has(doc.id) 
                          ? 'rgba(0, 212, 255, 0.1)' 
                          : 'var(--bg-tertiary)',
                        borderRadius: 'var(--radius-md)',
                        cursor: 'pointer',
                        border: selectedDocs.has(doc.id) 
                          ? '1px solid var(--accent-primary)' 
                          : '1px solid transparent',
                        transition: 'all 0.15s ease'
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={selectedDocs.has(doc.id)}
                        onChange={() => {
                          const newSelected = new Set(selectedDocs);
                          if (newSelected.has(doc.id)) {
                            newSelected.delete(doc.id);
                          } else {
                            newSelected.add(doc.id);
                          }
                          setSelectedDocs(newSelected);
                        }}
                        style={{ 
                          width: 18, 
                          height: 18, 
                          accentColor: 'var(--accent-primary)' 
                        }}
                      />
                      <FileText size={18} style={{ color: 'var(--accent-primary)', flexShrink: 0 }} />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ 
                          fontWeight: 500, 
                          overflow: 'hidden', 
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap'
                        }}>
                          {doc.display_name || doc.filename}
                        </div>
                        {doc.preview && (
                          <div style={{ 
                            fontSize: 11, 
                            color: 'var(--text-muted)', 
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                            marginTop: 2
                          }}>
                            {doc.preview}
                          </div>
                        )}
                        <div style={{ fontSize: 12, color: 'var(--accent-primary)', marginTop: 4 }}>
                          {doc.chunk_count} chunk{doc.chunk_count !== 1 ? 's' : ''}
                        </div>
                      </div>
                    </label>
                  ))}
                </div>
              )}
            </div>
            
            <div style={{ 
              padding: '12px 20px', 
              borderTop: '1px solid var(--border-color)',
              display: 'flex',
              justifyContent: 'flex-end',
              gap: 12
            }}>
              <button 
                className="btn btn-secondary"
                onClick={() => setShowDocSelector(false)}
              >
                Cancel
              </button>
              <button 
                className="btn btn-primary"
                onClick={() => setShowDocSelector(false)}
                disabled={selectedDocs.size === 0}
              >
                Use {selectedDocs.size} Document{selectedDocs.size !== 1 ? 's' : ''}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

