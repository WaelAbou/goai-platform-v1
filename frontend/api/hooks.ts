/**
 * Emerald Flow - Sustainability Platform Frontend
 * React Query Hooks for API calls
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';
import type {
  ReviewQueueResponse,
  ReviewStats,
  SmartProcessRequest,
  ChatRequest,
  EmailTestRequest,
} from './types';

// ==================== Query Keys ====================

export const queryKeys = {
  // Review
  reviewQueue: (filters?: Record<string, any>) => ['review', 'queue', filters],
  reviewItem: (id: string) => ['review', 'item', id],
  reviewStats: ['review', 'stats'],
  auditLog: (params?: Record<string, any>) => ['review', 'audit', params],
  
  // Smart Ingestion
  documentTypes: ['smart', 'documentTypes'],
  
  // Templates
  templates: ['templates', 'list'],
  template: (id: string) => ['templates', id],
  
  // Sustainability
  companies: ['sustainability', 'companies'],
  company: (id: string) => ['sustainability', 'company', id],
  locations: (companyId?: string) => ['sustainability', 'locations', companyId],
  footprints: (companyId?: string, year?: number) => ['sustainability', 'footprints', companyId, year],
  esgScores: (companyId?: string) => ['sustainability', 'esgScores', companyId],
  dbStats: ['sustainability', 'dbStats'],
  
  // Import
  importTemplates: ['import', 'templates'],
  emissionFactors: ['import', 'emissionFactors'],
  
  // Email
  emailConfig: ['email', 'config'],
  
  // RAG
  ragStats: ['rag', 'stats'],
  
  // Health
  health: ['health'],
};

// ==================== Review Queue Hooks ====================

export function useReviewQueue(filters?: {
  status?: string;
  confidence?: string;
  category?: string;
  company_id?: string;
  limit?: number;
  offset?: number;
}) {
  return useQuery({
    queryKey: queryKeys.reviewQueue(filters),
    queryFn: () => apiClient.getReviewQueue(filters),
    refetchInterval: 30000, // Auto-refresh every 30s
  });
}

export function useReviewItem(id: string) {
  return useQuery({
    queryKey: queryKeys.reviewItem(id),
    queryFn: () => apiClient.getReviewItem(id),
    enabled: !!id,
  });
}

export function useReviewStats() {
  return useQuery({
    queryKey: queryKeys.reviewStats,
    queryFn: () => apiClient.getReviewStats(),
    refetchInterval: 15000, // Auto-refresh every 15s
  });
}

export function useAuditLog(params?: { item_id?: string; user?: string; limit?: number }) {
  return useQuery({
    queryKey: queryKeys.auditLog(params),
    queryFn: () => apiClient.getAuditLog(params),
  });
}

export function useApproveItem() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data?: { approved_data?: Record<string, any>; notes?: string } }) =>
      apiClient.approveItem(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review'] });
    },
  });
}

export function useRejectItem() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      apiClient.rejectItem(id, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review'] });
    },
  });
}

export function useBulkApprove() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ itemIds, minConfidence }: { itemIds: string[]; minConfidence?: number }) =>
      apiClient.bulkApprove(itemIds, minConfidence),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review'] });
    },
  });
}

export function useSubmitDocument() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: apiClient.submitDocument.bind(apiClient),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review'] });
    },
  });
}

// ==================== Smart Ingestion Hooks ====================

export function useDocumentTypes() {
  return useQuery({
    queryKey: queryKeys.documentTypes,
    queryFn: () => apiClient.getDocumentTypes(),
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });
}

export function useSmartProcess() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: SmartProcessRequest) => apiClient.smartProcess(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review'] });
    },
  });
}

export function useSmartProcessAuto() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: SmartProcessRequest) => apiClient.smartProcessAuto(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review'] });
      queryClient.invalidateQueries({ queryKey: ['templates'] });
    },
  });
}

export function useUploadImage() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ file, companyId }: { file: File; companyId?: string }) =>
      apiClient.uploadImage(file, companyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review'] });
    },
  });
}

// ==================== Template Hooks ====================

export function useTemplates() {
  return useQuery({
    queryKey: queryKeys.templates,
    queryFn: () => apiClient.getTemplates(),
  });
}

export function useTemplate(id: string) {
  return useQuery({
    queryKey: queryKeys.template(id),
    queryFn: () => apiClient.getTemplate(id),
    enabled: !!id,
  });
}

export function useGenerateTemplate() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ documentText, hintType }: { documentText: string; hintType?: string }) =>
      apiClient.generateTemplate(documentText, hintType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['templates'] });
    },
  });
}

// ==================== Sustainability Data Hooks ====================

export function useChat() {
  return useMutation({
    mutationFn: (data: ChatRequest) => apiClient.chat(data),
  });
}

export function useCalculateCarbonFootprint() {
  return useMutation({
    mutationFn: ({ activity, details }: { activity: string; details: Record<string, any> }) =>
      apiClient.calculateCarbonFootprint(activity, details),
  });
}

export function useCalculateESGScore() {
  return useMutation({
    mutationFn: (companyData: Record<string, number>) =>
      apiClient.calculateESGScore(companyData),
  });
}

export function useRecommendations() {
  return useMutation({
    mutationFn: ({ industry, focusArea }: { industry: string; focusArea?: string }) =>
      apiClient.getRecommendations(industry, focusArea),
  });
}

// ==================== Database Hooks ====================

export function useCompanies() {
  return useQuery({
    queryKey: queryKeys.companies,
    queryFn: () => apiClient.getCompanies(),
  });
}

export function useCompany(id: string) {
  return useQuery({
    queryKey: queryKeys.company(id),
    queryFn: () => apiClient.getCompany(id),
    enabled: !!id,
  });
}

export function useLocations(companyId?: string) {
  return useQuery({
    queryKey: queryKeys.locations(companyId),
    queryFn: () => apiClient.getLocations(companyId),
  });
}

export function useFootprints(companyId?: string, year?: number) {
  return useQuery({
    queryKey: queryKeys.footprints(companyId, year),
    queryFn: () => apiClient.getFootprints(companyId, year),
  });
}

export function useESGScores(companyId?: string) {
  return useQuery({
    queryKey: queryKeys.esgScores(companyId),
    queryFn: () => apiClient.getESGScores(companyId),
  });
}

export function useDatabaseStats() {
  return useQuery({
    queryKey: queryKeys.dbStats,
    queryFn: () => apiClient.getDatabaseStats(),
  });
}

// ==================== Import Hooks ====================

export function useImportTemplates() {
  return useQuery({
    queryKey: queryKeys.importTemplates,
    queryFn: () => apiClient.getImportTemplates(),
  });
}

export function useEmissionFactors() {
  return useQuery({
    queryKey: queryKeys.emissionFactors,
    queryFn: () => apiClient.getEmissionFactors(),
    staleTime: 60 * 60 * 1000, // Cache for 1 hour
  });
}

export function useImportCSV() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ category, file, companyId }: { category: string; file: File; companyId: string }) =>
      apiClient.importCSV(category, file, companyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sustainability'] });
    },
  });
}

// ==================== Email Hooks ====================

export function useEmailConfig() {
  return useQuery({
    queryKey: queryKeys.emailConfig,
    queryFn: () => apiClient.getEmailConfig(),
  });
}

export function useTestEmail() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: EmailTestRequest) => apiClient.testEmail(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review'] });
    },
  });
}

// ==================== RAG Hooks ====================

export function useSearchKnowledgeBase() {
  return useMutation({
    mutationFn: ({ query, topK }: { query: string; topK?: number }) =>
      apiClient.searchKnowledgeBase(query, topK),
  });
}

export function useRAGStats() {
  return useQuery({
    queryKey: queryKeys.ragStats,
    queryFn: () => apiClient.getRAGStats(),
  });
}

// ==================== Health Hooks ====================

export function useHealthCheck() {
  return useQuery({
    queryKey: queryKeys.health,
    queryFn: () => apiClient.healthCheck(),
    refetchInterval: 60000, // Check every minute
    retry: 3,
  });
}

