import axios from 'axios';

const API_BASE = 'http://localhost:8000/api/v1';
const TOKEN_KEY = 'goai_auth_token';

export const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests automatically
api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 responses (expired token)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid - clear storage
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem('goai_auth_user');
      // Optionally redirect to login
      window.dispatchEvent(new CustomEvent('auth:logout'));
    }
    return Promise.reject(error);
  }
);

// Helper to get auth headers for fetch calls
export const getAuthHeaders = (): Record<string, string> => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
};

// RAG API
export const ragApi = {
  ingest: (content: string, filename: string, metadata?: Record<string, unknown>) =>
    api.post('/rag/ingest', { content, filename, metadata }),
  
  query: (query: string, options?: { mode?: string; top_k?: number; conversation_id?: string; model?: string }) =>
    api.post('/rag/query', { query, ...options }),
  
  ask: (query: string, top_k = 5) =>
    api.post(`/rag/ask?query=${encodeURIComponent(query)}&top_k=${top_k}`),
  
  createConversation: () =>
    api.post('/rag/conversation', {}),
  
  chat: (query: string, conversation_id: string, model?: string) =>
    api.post('/rag/chat', { query, conversation_id, model }),
  
  getStats: () =>
    api.get('/rag/stats'),
  
  getDocuments: (options?: { limit?: number; group_by_file?: boolean }) =>
    api.get('/rag/documents', { params: options }),
};

// LLM API
export const llmApi = {
  getProviders: () =>
    api.get('/llm/providers'),
  
  ollamaStatus: () =>
    api.get('/llm/ollama/status'),
  
  complete: (prompt: string, options?: { model?: string; provider?: string; max_tokens?: number }) =>
    api.post('/llm/complete', { prompt, ...options }),
  
  chat: (messages: Array<{ role: string; content: string }>, options?: { model?: string; provider?: string }) =>
    api.post('/llm/chat', { messages, ...options }),
  
  compare: (prompt: string, providers?: string[]) =>
    api.post(`/llm/compare?prompt=${encodeURIComponent(prompt)}`, { providers }),
};

// Sentiment API
export const sentimentApi = {
  analyze: (text: string, options?: { use_llm?: boolean; include_emotions?: boolean; model?: string }) =>
    api.post('/sentiment/analyze', { text, use_llm: true, ...options }),
  
  emotions: (text: string) =>
    api.post('/sentiment/emotions', { text }),
};

// SQL API
export const sqlApi = {
  query: (question: string, database?: string) =>
    api.post('/sql/query', { question, database }),
  
  registerSchema: (name: string, type: string, tables: Record<string, unknown>) =>
    api.post('/sql/schema/register', { name, type, tables }),
  
  listDatabases: () =>
    api.get('/sql/databases'),
};

// Validator API
export const validatorApi = {
  validate: (content: string) =>
    api.post('/validator/validate', { content, use_llm: true }),
  
  factCheck: (claim: string) =>
    api.post('/validator/fact-check', { claim }),
};

// Health API
export const healthApi = {
  check: () =>
    api.get('/health'),
  
  config: () =>
    axios.get('http://localhost:8000/config'),
};

// Memory API
export const memoryApi = {
  list: (options?: { memory_type?: string; category?: string; limit?: number }) =>
    api.get('/memory', { params: options }),
  
  create: (data: { content: string; memory_type?: string; category?: string; importance?: number }) =>
    api.post('/memory', data),
  
  get: (id: string) =>
    api.get(`/memory/${id}`),
  
  update: (id: string, data: { content?: string; category?: string; importance?: number }) =>
    api.put(`/memory/${id}`, data),
  
  delete: (id: string) =>
    api.delete(`/memory/${id}`),
  
  summary: () =>
    api.get('/memory/summary'),
  
  getContext: (options?: { max_tokens?: number; include_types?: string }) =>
    api.get('/memory/context', { params: options }),
  
  extract: (text: string, context?: string) =>
    api.post('/memory/extract', { text, conversation_context: context }),
};

