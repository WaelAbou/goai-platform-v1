import { useState, useRef, useCallback, useEffect } from 'react';
import { 
  Upload, 
  FileText, 
  CheckCircle, 
  AlertCircle, 
  Trash2, 
  File,
  FileType,
  Link,
  Settings,
  X,
  FolderOpen,
  Loader2,
  Eye,
  Download,
  Search,
  FileSpreadsheet,
  BookOpen
} from 'lucide-react';
import { ragApi } from '../api/client';
import axios from 'axios';

interface IngestedDoc {
  id: string;
  filename: string;
  chunks: number;
  pages?: number;
  status: string;
  timestamp: Date;
  size?: number;
  type?: string;
}

// Upload API
const uploadApi = {
  uploadFile: (file: File, options?: { chunk_size?: number; chunk_overlap?: number }) => {
    const formData = new FormData();
    formData.append('file', file);
    if (options?.chunk_size) formData.append('chunk_size', options.chunk_size.toString());
    if (options?.chunk_overlap) formData.append('chunk_overlap', options.chunk_overlap.toString());
    formData.append('preserve_pages', 'true');
    
    return axios.post('http://localhost:8000/api/v1/upload/file', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },
  getSupportedTypes: () => axios.get('http://localhost:8000/api/v1/upload/supported-types')
};

interface UploadConfig {
  chunkSize: number;
  chunkOverlap: number;
}

export default function DocumentsPage() {
  const [content, setContent] = useState('');
  const [filename, setFilename] = useState('');
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [documents, setDocuments] = useState<IngestedDoc[]>([]);
  const [result, setResult] = useState<{ success: boolean; message: string } | null>(null);
  const [activeTab, setActiveTab] = useState<'text' | 'file' | 'url'>('file');
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploadProgress, setUploadProgress] = useState<Record<string, number>>({});
  const [showConfig, setShowConfig] = useState(false);
  const [config, setConfig] = useState<UploadConfig>({ chunkSize: 1000, chunkOverlap: 200 });
  const [previewContent, setPreviewContent] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const files = Array.from(e.dataTransfer.files);
    const validExtensions = ['.pdf', '.docx', '.doc', '.txt', '.md', '.xlsx', '.xls', '.csv', '.json'];
    const validFiles = files.filter(f => 
      validExtensions.some(ext => f.name.toLowerCase().endsWith(ext))
    );
    
    setSelectedFiles(prev => [...prev, ...validFiles]);
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files);
      setSelectedFiles(prev => [...prev, ...files]);
    }
  };

  const removeFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const readFileContent = async (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => resolve(e.target?.result as string);
      reader.onerror = reject;
      reader.readAsText(file);
    });
  };

  const handleIngestFiles = async () => {
    if (selectedFiles.length === 0) return;

    setLoading(true);
    setResult(null);
    const newDocs: IngestedDoc[] = [];
    let successCount = 0;
    let failCount = 0;

    for (const file of selectedFiles) {
      try {
        setUploadProgress(prev => ({ ...prev, [file.name]: 10 }));
        
        // Use the new file upload API for PDF, DOCX, etc.
        const isParseable = ['.pdf', '.docx', '.doc', '.xlsx', '.xls'].some(
          ext => file.name.toLowerCase().endsWith(ext)
        );
        
        if (isParseable) {
          // Use file upload API with page extraction
          setUploadProgress(prev => ({ ...prev, [file.name]: 30 }));
          
          const response = await uploadApi.uploadFile(file, {
            chunk_size: config.chunkSize,
            chunk_overlap: config.chunkOverlap
          });
          
          setUploadProgress(prev => ({ ...prev, [file.name]: 100 }));
          
          newDocs.push({
            id: response.data.document_id,
            filename: response.data.filename,
            chunks: response.data.chunks_created,
            pages: response.data.total_pages,
            status: response.data.status,
            timestamp: new Date(),
            size: file.size,
            type: response.data.file_type
          });
        } else {
          // Text-based files: read and ingest directly
          const content = await readFileContent(file);
          setUploadProgress(prev => ({ ...prev, [file.name]: 50 }));
          
          const response = await ragApi.ingest(content, file.name, {
            source: 'file_upload',
            original_size: file.size,
            file_type: file.type,
            chunk_size: config.chunkSize,
            chunk_overlap: config.chunkOverlap
          });

          setUploadProgress(prev => ({ ...prev, [file.name]: 100 }));

          newDocs.push({
            id: response.data.doc_id,
            filename: response.data.filename,
            chunks: response.data.chunks,
            status: response.data.status,
            timestamp: new Date(),
            size: file.size,
            type: file.type
          });
        }
        
        successCount++;
      } catch (error: any) {
        console.error(`Failed to ingest ${file.name}:`, error);
        failCount++;
        setUploadProgress(prev => ({ ...prev, [file.name]: -1 }));
      }
    }

    setDocuments(prev => [...newDocs, ...prev]);
    setSelectedFiles([]);
    setUploadProgress({});
    
    if (successCount > 0 && failCount === 0) {
      setResult({ success: true, message: `Successfully ingested ${successCount} file(s)` });
    } else if (successCount > 0 && failCount > 0) {
      setResult({ success: true, message: `Ingested ${successCount} file(s), ${failCount} failed` });
    } else {
      setResult({ success: false, message: 'Failed to ingest files' });
    }
    
    setLoading(false);
  };

  const handleIngestText = async () => {
    if (!content.trim()) return;

    setLoading(true);
    setResult(null);

    try {
      const response = await ragApi.ingest(
        content,
        filename || `document_${Date.now()}.txt`,
        { 
          source: 'manual_input',
          chunk_size: config.chunkSize,
          chunk_overlap: config.chunkOverlap
        }
      );

      const newDoc: IngestedDoc = {
        id: response.data.doc_id,
        filename: response.data.filename,
        chunks: response.data.chunks,
        status: response.data.status,
        timestamp: new Date()
      };

      setDocuments(prev => [newDoc, ...prev]);
      setResult({ success: true, message: `Successfully ingested "${newDoc.filename}" (${newDoc.chunks} chunks)` });
      setContent('');
      setFilename('');
    } catch (error) {
      console.error('Failed to ingest:', error);
      setResult({ success: false, message: 'Failed to ingest document. Please try again.' });
    } finally {
      setLoading(false);
    }
  };

  const handleIngestUrl = async () => {
    if (!url.trim()) return;

    setLoading(true);
    setResult(null);

    try {
      // For now, show a message that URL fetching would require backend support
      setResult({ 
        success: false, 
        message: 'URL ingestion requires backend fetch support. Paste the content directly instead.' 
      });
    } catch (error) {
      setResult({ success: false, message: 'Failed to fetch URL' });
    } finally {
      setLoading(false);
    }
  };

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return '';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getFileIcon = (filename: string) => {
    const lower = filename.toLowerCase();
    if (lower.endsWith('.pdf')) return <BookOpen size={20} color="#ef4444" />;
    if (lower.endsWith('.docx') || lower.endsWith('.doc')) return <FileText size={20} color="#3b82f6" />;
    if (lower.endsWith('.xlsx') || lower.endsWith('.xls')) return <FileSpreadsheet size={20} color="#22c55e" />;
    if (lower.endsWith('.md') || lower.endsWith('.markdown')) return <FileType size={20} color="var(--accent-secondary)" />;
    if (lower.endsWith('.json')) return <FileText size={20} color="var(--accent-warning)" />;
    if (lower.endsWith('.csv')) return <FileSpreadsheet size={20} color="var(--accent-tertiary)" />;
    return <File size={20} color="var(--accent-primary)" />;
  };

  const filteredDocuments = documents.filter(doc =>
    doc.filename.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const sampleDocuments = [
    {
      title: 'AI & Machine Learning',
      icon: '🤖',
      content: `Artificial Intelligence (AI) is a branch of computer science focused on creating intelligent machines that can perform tasks typically requiring human intelligence.

Machine Learning is a subset of AI that enables systems to learn and improve from experience without being explicitly programmed. It uses algorithms to analyze data, learn from it, and make predictions.

Deep Learning is a type of machine learning based on artificial neural networks with multiple layers. These networks can learn hierarchical representations of data, making them powerful for complex tasks like image recognition and natural language processing.

Neural Networks are computing systems inspired by biological neural networks. They consist of layers of interconnected nodes (neurons) that process information using mathematical functions.

Key Applications:
- Natural Language Processing (NLP) for understanding human language
- Computer Vision for interpreting visual information  
- Recommendation Systems for personalized suggestions
- Autonomous Vehicles for self-driving cars
- Medical Diagnosis for disease detection`
    },
    {
      title: 'Python Programming',
      icon: '🐍',
      content: `Python is a high-level, interpreted programming language known for its simplicity and readability. Created by Guido van Rossum in 1991, Python has become one of the most popular programming languages.

Key Features:
- Easy to learn syntax with emphasis on readability
- Dynamic typing and automatic memory management
- Supports multiple paradigms: procedural, object-oriented, functional
- Extensive standard library ("batteries included")
- Large ecosystem of third-party packages via PyPI

Popular Frameworks:
- Django: Full-stack web framework for rapid development
- Flask: Lightweight microframework for web applications
- FastAPI: Modern async API framework with automatic documentation
- PyTorch: Deep learning framework by Meta
- TensorFlow: Machine learning platform by Google
- Pandas: Data analysis and manipulation library
- NumPy: Scientific computing with arrays

Best Practices:
- Follow PEP 8 style guide
- Use virtual environments for project isolation
- Write docstrings for documentation
- Implement unit tests with pytest`
    },
    {
      title: 'Cloud Computing',
      icon: '☁️',
      content: `Cloud Computing is the delivery of computing services over the internet, including servers, storage, databases, networking, software, and analytics.

Service Models:
- IaaS (Infrastructure as a Service): Virtual machines, storage, networks
- PaaS (Platform as a Service): Development platforms, databases
- SaaS (Software as a Service): Ready-to-use applications

Major Cloud Providers:
- Amazon Web Services (AWS): Market leader with 200+ services
- Microsoft Azure: Strong enterprise integration
- Google Cloud Platform (GCP): Leading in AI/ML services

Key Benefits:
- Scalability: Scale resources up or down as needed
- Cost Efficiency: Pay only for what you use
- Reliability: Built-in redundancy and disaster recovery
- Global Reach: Deploy applications worldwide
- Security: Enterprise-grade security features

Popular Services:
- Compute: EC2, Azure VMs, Compute Engine
- Storage: S3, Blob Storage, Cloud Storage
- Databases: RDS, Cosmos DB, Cloud SQL
- Serverless: Lambda, Azure Functions, Cloud Functions`
    }
  ];

  return (
    <>
      <header className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 className="page-title">Document Ingestion</h1>
            <p className="page-subtitle">Upload and index documents for RAG retrieval</p>
          </div>
          <button 
            className="btn btn-secondary"
            onClick={() => setShowConfig(!showConfig)}
          >
            <Settings size={18} />
            Settings
          </button>
        </div>
      </header>

      <div className="page-content">
        {/* Config Panel */}
        {showConfig && (
          <div className="card" style={{ marginBottom: 24 }}>
            <div className="card-header">
              <h2 className="card-title">Chunking Configuration</h2>
              <button 
                className="btn btn-secondary btn-icon"
                style={{ width: 32, height: 32 }}
                onClick={() => setShowConfig(false)}
              >
                <X size={16} />
              </button>
            </div>
            <div className="grid-2">
              <div>
                <label style={{ display: 'block', marginBottom: 8, fontSize: 14, fontWeight: 500 }}>
                  Chunk Size (characters)
                </label>
                <input
                  type="number"
                  value={config.chunkSize}
                  onChange={(e) => setConfig(prev => ({ ...prev, chunkSize: parseInt(e.target.value) || 1000 }))}
                  min={100}
                  max={5000}
                />
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
                  Larger chunks = more context, smaller = more precise retrieval
                </div>
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: 8, fontSize: 14, fontWeight: 500 }}>
                  Chunk Overlap (characters)
                </label>
                <input
                  type="number"
                  value={config.chunkOverlap}
                  onChange={(e) => setConfig(prev => ({ ...prev, chunkOverlap: parseInt(e.target.value) || 200 }))}
                  min={0}
                  max={1000}
                />
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
                  Overlap helps maintain context between chunks
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="grid-2">
          {/* Upload Section */}
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">
                <Upload size={20} style={{ marginRight: 8 }} />
                Upload Documents
              </h2>
            </div>

            {/* Tabs */}
            <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
              {[
                { id: 'file', label: 'File Upload', icon: <FolderOpen size={16} /> },
                { id: 'text', label: 'Paste Text', icon: <FileText size={16} /> },
                { id: 'url', label: 'From URL', icon: <Link size={16} /> }
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as 'text' | 'file' | 'url')}
                  style={{
                    flex: 1,
                    padding: '10px 16px',
                    background: activeTab === tab.id 
                      ? 'linear-gradient(135deg, rgba(0, 212, 255, 0.15), rgba(124, 58, 237, 0.1))'
                      : 'var(--bg-tertiary)',
                    border: activeTab === tab.id ? '1px solid var(--border-glow)' : '1px solid var(--border-color)',
                    borderRadius: 'var(--radius-md)',
                    color: activeTab === tab.id ? 'var(--accent-primary)' : 'var(--text-secondary)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 8,
                    fontSize: 13,
                    fontWeight: 500,
                    transition: 'all 0.2s ease'
                  }}
                >
                  {tab.icon}
                  {tab.label}
                </button>
              ))}
            </div>

            {/* File Upload Tab */}
            {activeTab === 'file' && (
              <>
                <div
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                  style={{
                    border: `2px dashed ${isDragging ? 'var(--accent-primary)' : 'var(--border-color)'}`,
                    borderRadius: 'var(--radius-lg)',
                    padding: 40,
                    textAlign: 'center',
                    cursor: 'pointer',
                    background: isDragging ? 'rgba(0, 212, 255, 0.05)' : 'var(--bg-tertiary)',
                    transition: 'all 0.2s ease',
                    marginBottom: 16
                  }}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    accept=".pdf,.docx,.doc,.xlsx,.xls,.txt,.md,.json,.csv"
                    onChange={handleFileSelect}
                    style={{ display: 'none' }}
                  />
                  <Upload 
                    size={48} 
                    color={isDragging ? 'var(--accent-primary)' : 'var(--text-muted)'} 
                    style={{ marginBottom: 16 }}
                  />
                  <div style={{ fontWeight: 600, marginBottom: 8 }}>
                    {isDragging ? 'Drop files here' : 'Drag & drop files here'}
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                    or click to browse
                  </div>
                  <div style={{ 
                    fontSize: 12, 
                    color: 'var(--accent-primary)', 
                    marginTop: 8,
                    display: 'flex',
                    gap: 8,
                    flexWrap: 'wrap',
                    justifyContent: 'center'
                  }}>
                    <span style={{ background: 'rgba(239, 68, 68, 0.2)', padding: '2px 8px', borderRadius: 4 }}>PDF</span>
                    <span style={{ background: 'rgba(59, 130, 246, 0.2)', padding: '2px 8px', borderRadius: 4 }}>DOCX</span>
                    <span style={{ background: 'rgba(34, 197, 94, 0.2)', padding: '2px 8px', borderRadius: 4 }}>XLSX</span>
                    <span style={{ background: 'rgba(124, 58, 237, 0.2)', padding: '2px 8px', borderRadius: 4 }}>TXT</span>
                    <span style={{ background: 'rgba(245, 158, 11, 0.2)', padding: '2px 8px', borderRadius: 4 }}>MD</span>
                  </div>
                </div>

                {/* Selected Files */}
                {selectedFiles.length > 0 && (
                  <div style={{ marginBottom: 16 }}>
                    <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 8 }}>
                      Selected Files ({selectedFiles.length})
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 200, overflowY: 'auto' }}>
                      {selectedFiles.map((file, index) => (
                        <div
                          key={index}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            padding: 12,
                            background: 'var(--bg-tertiary)',
                            borderRadius: 'var(--radius-md)',
                            border: '1px solid var(--border-color)'
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                            {getFileIcon(file.name)}
                            <div>
                              <div style={{ fontWeight: 500, fontSize: 14 }}>{file.name}</div>
                              <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                                {formatFileSize(file.size)}
                              </div>
                            </div>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            {uploadProgress[file.name] !== undefined && (
                              uploadProgress[file.name] === -1 ? (
                                <span className="tag error">Failed</span>
                              ) : uploadProgress[file.name] === 100 ? (
                                <span className="tag success">Done</span>
                              ) : (
                                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                  <Loader2 size={16} className="spinner" />
                                  <span style={{ fontSize: 12 }}>{uploadProgress[file.name]}%</span>
                                </div>
                              )
                            )}
                            <button
                              onClick={() => removeFile(index)}
                              style={{
                                background: 'none',
                                border: 'none',
                                cursor: 'pointer',
                                padding: 4,
                                color: 'var(--text-muted)'
                              }}
                            >
                              <X size={16} />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <button
                  className="btn btn-primary"
                  onClick={handleIngestFiles}
                  disabled={loading || selectedFiles.length === 0}
                  style={{ width: '100%' }}
                >
                  {loading ? (
                    <>
                      <div className="spinner" />
                      Ingesting...
                    </>
                  ) : (
                    <>
                      <Upload size={18} />
                      Ingest {selectedFiles.length} File{selectedFiles.length !== 1 ? 's' : ''}
                    </>
                  )}
                </button>
              </>
            )}

            {/* Text Tab */}
            {activeTab === 'text' && (
              <>
                <div style={{ marginBottom: 16 }}>
                  <label style={{ display: 'block', marginBottom: 8, fontSize: 14, fontWeight: 500 }}>
                    Filename (optional)
                  </label>
                  <input
                    type="text"
                    value={filename}
                    onChange={(e) => setFilename(e.target.value)}
                    placeholder="my_document.txt"
                  />
                </div>

                <div style={{ marginBottom: 16 }}>
                  <label style={{ display: 'block', marginBottom: 8, fontSize: 14, fontWeight: 500 }}>
                    Content
                  </label>
                  <textarea
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    placeholder="Paste your document content here..."
                    style={{ minHeight: 200 }}
                  />
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
                    {content.length} characters
                  </div>
                </div>

                <button
                  className="btn btn-primary"
                  onClick={handleIngestText}
                  disabled={loading || !content.trim()}
                  style={{ width: '100%' }}
                >
                  {loading ? (
                    <>
                      <div className="spinner" />
                      Ingesting...
                    </>
                  ) : (
                    <>
                      <Upload size={18} />
                      Ingest Document
                    </>
                  )}
                </button>
              </>
            )}

            {/* URL Tab */}
            {activeTab === 'url' && (
              <>
                <div style={{ marginBottom: 16 }}>
                  <label style={{ display: 'block', marginBottom: 8, fontSize: 14, fontWeight: 500 }}>
                    URL
                  </label>
                  <input
                    type="url"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="https://example.com/document.txt"
                  />
                </div>

                <button
                  className="btn btn-primary"
                  onClick={handleIngestUrl}
                  disabled={loading || !url.trim()}
                  style={{ width: '100%' }}
                >
                  {loading ? (
                    <>
                      <div className="spinner" />
                      Fetching...
                    </>
                  ) : (
                    <>
                      <Link size={18} />
                      Fetch & Ingest
                    </>
                  )}
                </button>

                <div style={{ 
                  marginTop: 16, 
                  padding: 12, 
                  background: 'rgba(245, 158, 11, 0.1)',
                  borderRadius: 'var(--radius-md)',
                  fontSize: 13,
                  color: 'var(--accent-warning)'
                }}>
                  💡 Tip: For now, copy the content from the URL and paste it in the "Paste Text" tab.
                </div>
              </>
            )}

            {/* Result Message */}
            {result && (
              <div
                style={{
                  marginTop: 16,
                  padding: 12,
                  borderRadius: 'var(--radius-md)',
                  background: result.success ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                  border: `1px solid ${result.success ? 'var(--accent-tertiary)' : 'var(--accent-danger)'}`,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  fontSize: 14
                }}
              >
                {result.success ? (
                  <CheckCircle size={18} color="var(--accent-tertiary)" />
                ) : (
                  <AlertCircle size={18} color="var(--accent-danger)" />
                )}
                {result.message}
              </div>
            )}
          </div>

          {/* Sample Documents */}
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">
                <FileText size={20} style={{ marginRight: 8 }} />
                Quick Add Samples
              </h2>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {sampleDocuments.map((doc, index) => (
                <div
                  key={index}
                  style={{
                    padding: 16,
                    background: 'var(--bg-tertiary)',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-color)',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease'
                  }}
                  onClick={() => {
                    setContent(doc.content);
                    setFilename(`${doc.title.toLowerCase().replace(/\s+/g, '_')}.txt`);
                    setActiveTab('text');
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = 'var(--accent-primary)';
                    e.currentTarget.style.transform = 'translateY(-2px)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = 'var(--border-color)';
                    e.currentTarget.style.transform = 'translateY(0)';
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                    <span style={{ fontSize: 24 }}>{doc.icon}</span>
                    <div style={{ fontWeight: 600 }}>{doc.title}</div>
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 12 }}>
                    {doc.content.slice(0, 120)}...
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span className="tag info">Click to use</span>
                    <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                      {doc.content.length} chars
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Document Library */}
        {documents.length > 0 && (
          <div className="card" style={{ marginTop: 24 }}>
            <div className="card-header">
              <h2 className="card-title">Document Library ({documents.length})</h2>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{ position: 'relative' }}>
                  <Search size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search documents..."
                    style={{ paddingLeft: 36, width: 200 }}
                  />
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {filteredDocuments.map((doc) => (
                <div
                  key={doc.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: 16,
                    background: 'var(--bg-tertiary)',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-color)'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                    {getFileIcon(doc.filename)}
                    <div>
                      <div style={{ fontWeight: 600 }}>{doc.filename}</div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)', display: 'flex', gap: 16 }}>
                        {doc.pages && <span style={{ color: 'var(--accent-primary)' }}>📄 {doc.pages} pages</span>}
                        <span>{doc.chunks} chunks</span>
                        {doc.size && <span>{formatFileSize(doc.size)}</span>}
                        <span>{doc.timestamp.toLocaleString()}</span>
                      </div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span className={`tag ${doc.status === 'completed' ? 'success' : 'warning'}`}>
                      {doc.status}
                    </span>
                    <button
                      className="btn btn-secondary btn-icon"
                      style={{ width: 32, height: 32 }}
                      title="Preview"
                    >
                      <Eye size={14} />
                    </button>
                    <button
                      className="btn btn-secondary btn-icon"
                      style={{ width: 32, height: 32 }}
                      title="Delete"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Preview Modal */}
        {previewContent && (
          <div
            style={{
              position: 'fixed',
              inset: 0,
              background: 'rgba(0,0,0,0.8)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 1000
            }}
            onClick={() => setPreviewContent(null)}
          >
            <div
              className="card"
              style={{ width: '80%', maxWidth: 800, maxHeight: '80vh', overflow: 'auto' }}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="card-header">
                <h2 className="card-title">Document Preview</h2>
                <button className="btn btn-secondary btn-icon" onClick={() => setPreviewContent(null)}>
                  <X size={18} />
                </button>
              </div>
              <pre style={{ whiteSpace: 'pre-wrap', fontSize: 13 }}>{previewContent}</pre>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
