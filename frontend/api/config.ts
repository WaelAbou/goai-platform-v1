/**
 * Emerald Flow - Sustainability Platform Frontend
 * API Configuration
 */

export const API_CONFIG = {
  baseUrl: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  version: 'v1',
  endpoints: {
    // Review Dashboard
    review: {
      queue: '/api/v1/review/queue',
      stats: '/api/v1/review/stats',
      item: (id: string) => `/api/v1/review/queue/${id}`,
      approve: (id: string) => `/api/v1/review/queue/${id}/approve`,
      reject: (id: string) => `/api/v1/review/queue/${id}/reject`,
      bulkApprove: '/api/v1/review/queue/bulk-approve',
      submit: '/api/v1/review/submit',
      auditLog: '/api/v1/review/audit-log',
    },
    
    // Smart Ingestion
    smart: {
      process: '/api/v1/sustainability/smart/process',
      processAuto: '/api/v1/sustainability/smart/process-auto',
      processImage: '/api/v1/sustainability/smart/process-image',
      classify: '/api/v1/sustainability/smart/classify',
      documentTypes: '/api/v1/sustainability/smart/document-types',
    },
    
    // Auto Templates
    templates: {
      list: '/api/v1/sustainability/templates/auto',
      get: (id: string) => `/api/v1/sustainability/templates/auto/${id}`,
      generate: '/api/v1/sustainability/templates/auto/generate',
      extract: (id: string) => `/api/v1/sustainability/templates/auto/${id}/extract`,
    },
    
    // Email Integration
    email: {
      config: '/api/v1/email/config',
      test: '/api/v1/email/test',
      simulate: '/api/v1/email/simulate',
    },
    
    // Sustainability Data
    sustainability: {
      chat: '/api/v1/sustainability/chat',
      carbonFootprint: '/api/v1/sustainability/carbon-footprint',
      esgScore: '/api/v1/sustainability/esg-score',
      recommendations: '/api/v1/sustainability/recommendations',
      standards: '/api/v1/sustainability/standards',
      
      // Database
      db: {
        companies: '/api/v1/sustainability/db/companies',
        company: (id: string) => `/api/v1/sustainability/db/companies/${id}`,
        locations: '/api/v1/sustainability/db/locations',
        footprints: '/api/v1/sustainability/db/footprints',
        esgScores: '/api/v1/sustainability/db/esg-scores',
        reductionPlans: '/api/v1/sustainability/db/reduction-plans',
        benchmarks: '/api/v1/sustainability/db/benchmarks',
        stats: '/api/v1/sustainability/db/stats',
      },
      
      // Data Import
      import: {
        templates: '/api/v1/sustainability/import/templates',
        template: (category: string) => `/api/v1/sustainability/import/templates/${category}`,
        csv: (category: string) => `/api/v1/sustainability/import/${category}/csv`,
        emissionFactors: '/api/v1/sustainability/import/emission-factors',
      },
      
      // RAG Knowledge Base
      rag: {
        ingest: '/api/v1/sustainability/rag/ingest',
        search: '/api/v1/sustainability/rag/search',
        stats: '/api/v1/sustainability/rag/stats',
      },
    },
    
    // Health Check
    health: '/health',
  },
};

export default API_CONFIG;

