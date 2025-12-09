/**
 * Emerald Flow - Sustainability Platform Frontend
 * API Client with React Query hooks
 */

import API_CONFIG from './config';
import type {
  ReviewItem,
  ReviewQueueResponse,
  ReviewStats,
  AuditLogEntry,
  SmartProcessRequest,
  SmartProcessResponse,
  DocumentTypeInfo,
  GeneratedTemplate,
  TemplateListItem,
  Company,
  Location,
  CarbonFootprint,
  ESGScore,
  ChatRequest,
  ChatResponse,
  EmailTestRequest,
  EmailTestResponse,
} from './types';

// ==================== Base Client ====================

class ApiClient {
  private baseUrl: string;

  constructor() {
    this.baseUrl = API_CONFIG.baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    
    const defaultHeaders: HeadersInit = {
      'Content-Type': 'application/json',
    };

    const response = await fetch(url, {
      ...options,
      headers: {
        ...defaultHeaders,
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // ==================== Review Queue ====================

  async getReviewQueue(params?: {
    status?: string;
    confidence?: string;
    category?: string;
    company_id?: string;
    limit?: number;
    offset?: number;
    sort_by?: string;
    sort_order?: string;
  }): Promise<ReviewQueueResponse> {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          searchParams.append(key, String(value));
        }
      });
    }
    const query = searchParams.toString();
    return this.request(`${API_CONFIG.endpoints.review.queue}${query ? `?${query}` : ''}`);
  }

  async getReviewItem(id: string): Promise<{ item: ReviewItem; audit_log: AuditLogEntry[] }> {
    return this.request(API_CONFIG.endpoints.review.item(id));
  }

  async getReviewStats(): Promise<ReviewStats> {
    return this.request(API_CONFIG.endpoints.review.stats);
  }

  async approveItem(id: string, data?: { approved_data?: Record<string, any>; notes?: string }): Promise<{ status: string; message: string }> {
    return this.request(API_CONFIG.endpoints.review.approve(id), {
      method: 'POST',
      body: JSON.stringify(data || {}),
    });
  }

  async rejectItem(id: string, reason: string): Promise<{ status: string; message: string }> {
    return this.request(API_CONFIG.endpoints.review.reject(id), {
      method: 'POST',
      body: JSON.stringify({ reason }),
    });
  }

  async bulkApprove(itemIds: string[], minConfidence = 0.9): Promise<{ approved: number; skipped: number }> {
    return this.request(API_CONFIG.endpoints.review.bulkApprove, {
      method: 'POST',
      body: JSON.stringify({ item_ids: itemIds, min_confidence: minConfidence }),
    });
  }

  async submitDocument(data: {
    text_content?: string;
    image_base64?: string;
    source?: string;
    filename?: string;
    uploaded_by?: string;
    company_id?: string;
  }): Promise<{ status: string; item_id: string; confidence: number }> {
    return this.request(API_CONFIG.endpoints.review.submit, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getAuditLog(params?: { item_id?: string; user?: string; limit?: number }): Promise<{ entries: AuditLogEntry[]; count: number }> {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) searchParams.append(key, String(value));
      });
    }
    return this.request(`${API_CONFIG.endpoints.review.auditLog}?${searchParams}`);
  }

  // ==================== Smart Ingestion ====================

  async smartProcess(data: SmartProcessRequest): Promise<SmartProcessResponse> {
    return this.request(API_CONFIG.endpoints.smart.process, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async smartProcessAuto(data: SmartProcessRequest): Promise<SmartProcessResponse & { processing_mode: string; template_id?: string }> {
    return this.request(API_CONFIG.endpoints.smart.processAuto, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async uploadImage(file: File, companyId?: string): Promise<SmartProcessResponse> {
    const formData = new FormData();
    formData.append('file', file);
    if (companyId) formData.append('company_id', companyId);

    const response = await fetch(`${this.baseUrl}${API_CONFIG.endpoints.smart.processImage}`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) throw new Error('Upload failed');
    return response.json();
  }

  async getDocumentTypes(): Promise<{ supported_types: DocumentTypeInfo[] }> {
    return this.request(API_CONFIG.endpoints.smart.documentTypes);
  }

  // ==================== Auto Templates ====================

  async getTemplates(): Promise<{ total_templates: number; templates: TemplateListItem[] }> {
    return this.request(API_CONFIG.endpoints.templates.list);
  }

  async getTemplate(id: string): Promise<{ template: GeneratedTemplate }> {
    return this.request(API_CONFIG.endpoints.templates.get(id));
  }

  async generateTemplate(documentText: string, hintType?: string): Promise<{ status: string; template: GeneratedTemplate }> {
    return this.request(API_CONFIG.endpoints.templates.generate, {
      method: 'POST',
      body: JSON.stringify({ document_text: documentText, hint_type: hintType }),
    });
  }

  // ==================== Sustainability Data ====================

  async chat(data: ChatRequest): Promise<ChatResponse> {
    return this.request(API_CONFIG.endpoints.sustainability.chat, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async calculateCarbonFootprint(activity: string, details: Record<string, any>): Promise<any> {
    return this.request(API_CONFIG.endpoints.sustainability.carbonFootprint, {
      method: 'POST',
      body: JSON.stringify({ activity, details }),
    });
  }

  async calculateESGScore(companyData: Record<string, number>): Promise<any> {
    return this.request(API_CONFIG.endpoints.sustainability.esgScore, {
      method: 'POST',
      body: JSON.stringify({ company_data: companyData }),
    });
  }

  async getRecommendations(industry: string, focusArea?: string): Promise<any> {
    return this.request(API_CONFIG.endpoints.sustainability.recommendations, {
      method: 'POST',
      body: JSON.stringify({ industry, focus_area: focusArea }),
    });
  }

  // ==================== Database Operations ====================

  async getCompanies(): Promise<Company[]> {
    return this.request(API_CONFIG.endpoints.sustainability.db.companies);
  }

  async getCompany(id: string): Promise<Company> {
    return this.request(API_CONFIG.endpoints.sustainability.db.company(id));
  }

  async getLocations(companyId?: string): Promise<Location[]> {
    const query = companyId ? `?company_id=${companyId}` : '';
    return this.request(`${API_CONFIG.endpoints.sustainability.db.locations}${query}`);
  }

  async getFootprints(companyId?: string, year?: number): Promise<CarbonFootprint[]> {
    const params = new URLSearchParams();
    if (companyId) params.append('company_id', companyId);
    if (year) params.append('year', String(year));
    return this.request(`${API_CONFIG.endpoints.sustainability.db.footprints}?${params}`);
  }

  async getESGScores(companyId?: string): Promise<ESGScore[]> {
    const query = companyId ? `?company_id=${companyId}` : '';
    return this.request(`${API_CONFIG.endpoints.sustainability.db.esgScores}${query}`);
  }

  async getDatabaseStats(): Promise<any> {
    return this.request(API_CONFIG.endpoints.sustainability.db.stats);
  }

  // ==================== Data Import ====================

  async getImportTemplates(): Promise<any> {
    return this.request(API_CONFIG.endpoints.sustainability.import.templates);
  }

  async downloadTemplate(category: string): Promise<Blob> {
    const response = await fetch(
      `${this.baseUrl}${API_CONFIG.endpoints.sustainability.import.template(category)}`
    );
    return response.blob();
  }

  async importCSV(category: string, file: File, companyId: string): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('company_id', companyId);

    const response = await fetch(
      `${this.baseUrl}${API_CONFIG.endpoints.sustainability.import.csv(category)}`,
      { method: 'POST', body: formData }
    );
    return response.json();
  }

  async getEmissionFactors(): Promise<any> {
    return this.request(API_CONFIG.endpoints.sustainability.import.emissionFactors);
  }

  // ==================== Email Integration ====================

  async testEmail(data: EmailTestRequest): Promise<EmailTestResponse> {
    return this.request(API_CONFIG.endpoints.email.test, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getEmailConfig(): Promise<any> {
    return this.request(API_CONFIG.endpoints.email.config);
  }

  // ==================== RAG Knowledge Base ====================

  async searchKnowledgeBase(query: string, topK = 5): Promise<any> {
    return this.request(API_CONFIG.endpoints.sustainability.rag.search, {
      method: 'POST',
      body: JSON.stringify({ query, top_k: topK }),
    });
  }

  async getRAGStats(): Promise<any> {
    return this.request(API_CONFIG.endpoints.sustainability.rag.stats);
  }

  // ==================== Health Check ====================

  async healthCheck(): Promise<{ status: string }> {
    return this.request(API_CONFIG.endpoints.health);
  }
}

// Export singleton instance
export const apiClient = new ApiClient();
export default apiClient;

