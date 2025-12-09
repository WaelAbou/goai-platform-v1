/**
 * Emerald Flow - Sustainability Platform Frontend
 * TypeScript Type Definitions (matching backend API)
 */

// ==================== Review Queue Types ====================

export type ReviewStatus = 'pending' | 'approved' | 'rejected' | 'auto_approved' | 'exported';
export type ConfidenceLevel = 'high' | 'medium' | 'low' | 'unknown';
export type DocumentCategory = 'energy' | 'travel' | 'fleet' | 'shipping' | 'waste' | 'carbon_offset' | 'esg_report' | 'other';

export interface ReviewItem {
  id: string;
  document_type: string;
  category: DocumentCategory;
  source: 'email' | 'sharepoint' | 'upload' | 'api' | 'mobile';
  filename: string;
  uploaded_by: string;
  uploaded_at: string;
  confidence: number;
  confidence_level: ConfidenceLevel;
  extracted_data: Record<string, any>;
  raw_text: string;
  calculated_co2e_kg: number | null;
  status: ReviewStatus;
  reviewed_by: string | null;
  reviewed_at: string | null;
  approved_data: Record<string, any> | null;
  changes_made: boolean;
  rejection_reason: string | null;
  notes: string | null;
  company_id: string | null;
  location_id: string | null;
  period_start: string | null;
  period_end: string | null;
  is_flagged: boolean;
  flag_reason: string | null;
  is_anomaly: boolean;
  anomaly_details: string | null;
}

export interface ReviewQueueResponse {
  items: ReviewItem[];
  count: number;
  filters: {
    status: string | null;
    confidence: string | null;
    category: string | null;
    company_id: string | null;
  };
  pagination: {
    limit: number;
    offset: number;
  };
}

export interface ReviewStats {
  queue_summary: {
    pending: number;
    approved: number;
    auto_approved: number;
    rejected: number;
    total: number;
  };
  pending_by_confidence: Record<string, number>;
  by_category: Record<string, number>;
  emissions: {
    approved_kg: number;
    approved_tonnes: number;
    pending_kg: number;
    pending_tonnes: number;
  };
  activity: {
    daily_uploads: Array<{ date: string; count: number }>;
    auto_approve_rate: number;
  };
}

export interface AuditLogEntry {
  id: string;
  timestamp: string;
  user: string;
  action: 'created' | 'viewed' | 'approved' | 'rejected' | 'edited' | 'exported';
  review_item_id: string;
  details: Record<string, any>;
  ip_address: string | null;
}

// ==================== Smart Ingestion Types ====================

export type SustainabilityDocumentType =
  | 'utility_bill_electric'
  | 'utility_bill_gas'
  | 'utility_bill_water'
  | 'flight_receipt'
  | 'car_rental_receipt'
  | 'hotel_receipt'
  | 'fuel_receipt'
  | 'shipping_invoice'
  | 'esg_report'
  | 'expense_report'
  | 'unknown';

export interface SmartProcessRequest {
  text_content?: string;
  image_base64?: string;
  force_type?: SustainabilityDocumentType;
  company_id?: string;
}

export interface SmartProcessResponse {
  status: 'success' | 'error';
  document_type: SustainabilityDocumentType;
  suggested_template: string;
  confidence: number;
  extracted_data: Record<string, any>;
  calculated_co2e_kg: number | null;
  calculated_co2e_tonnes?: number;
  emission_equivalents?: {
    trees_needed: number;
    car_km: number;
  };
  company_id?: string;
}

export interface DocumentTypeInfo {
  type: string;
  name: string;
  template: string;
}

// ==================== Auto Template Types ====================

export interface FieldDefinition {
  name: string;
  description: string;
  data_type: 'string' | 'number' | 'date' | 'boolean' | 'array';
  required: boolean;
  emission_factor_key: string | null;
  unit: string | null;
  validation_pattern: string | null;
  example: string | null;
}

export interface GeneratedTemplate {
  template_id: string;
  name: string;
  description: string;
  document_indicators: string[];
  category: string;
  scope: 'scope_1' | 'scope_2' | 'scope_3' | 'multiple';
  fields: FieldDefinition[];
  extraction_prompt: string;
  emission_calculation: {
    formula: string;
    primary_field: string;
    factor_type: string;
    multiplier: number;
  };
  created_at: string;
  created_by: string;
  version: number;
  usage_count: number;
  accuracy_score: number;
}

export interface TemplateListItem {
  template_id: string;
  name: string;
  description: string;
  category: string;
  scope: string;
  fields_count: number;
  usage_count: number;
  created_at: string;
}

// ==================== Sustainability Data Types ====================

export interface Company {
  id: string;
  name: string;
  industry: string;
  sub_industry?: string;
  employees: number;
  revenue_usd: number;
  fiscal_year: number;
  created_at: string;
}

export interface Location {
  id: string;
  company_id: string;
  name: string;
  type: 'headquarters' | 'regional' | 'warehouse' | 'data_center';
  address: string;
  city: string;
  country: string;
  employees: number;
  sqft: number;
  renewable_energy_percent: number;
}

export interface CarbonFootprint {
  id: string;
  company_id: string;
  year: number;
  scope_1_kg: number;
  scope_2_kg: number;
  scope_3_kg: number;
  total_kg: number;
  methodology: string;
  verification_status: 'self_reported' | 'third_party_verified' | 'audited';
  breakdown: Record<string, any>;
  created_at: string;
}

export interface ESGScore {
  id: string;
  company_id: string;
  assessment_date: string;
  environmental_score: number;
  social_score: number;
  governance_score: number;
  overall_score: number;
  rating: 'A+' | 'A' | 'B+' | 'B' | 'C+' | 'C' | 'D' | 'F';
  industry_percentile: number;
  strengths: string[];
  weaknesses: string[];
}

export interface ReductionPlan {
  id: string;
  company_id: string;
  target_year: number;
  initiatives: Array<{
    name: string;
    description: string;
    target_reduction_percent: number;
    estimated_reduction_kg: number;
    timeline_months: number;
    status: 'planned' | 'in_progress' | 'completed';
  }>;
  projected_results: {
    current_emissions_kg: number;
    projected_emissions_kg: number;
    total_reduction_kg: number;
    reduction_percent: number;
  };
}

// ==================== Chat & Recommendations ====================

export interface ChatRequest {
  message: string;
  context?: Record<string, any>;
  model?: string;
  temperature?: number;
}

export interface ChatResponse {
  response: string;
  status: 'success' | 'error';
  rag_context?: string[];
}

export interface CarbonFootprintRequest {
  activity: string;
  details: Record<string, any>;
}

export interface ESGScoreRequest {
  company_data: {
    renewable_energy_percent: number;
    waste_recycled_percent: number;
    employee_diversity_score: number;
    board_independence_percent: number;
    [key: string]: number;
  };
}

export interface RecommendationsRequest {
  industry: string;
  focus_area?: string;
  company_size?: 'small' | 'medium' | 'large' | 'enterprise';
}

// ==================== Email Integration Types ====================

export interface EmailTestRequest {
  email_body: string;
  from_address?: string;
  subject?: string;
  company_id?: string;
}

export interface EmailTestResponse {
  status: 'success' | 'partial' | 'failed';
  items_created: number;
  items: Array<{
    item_id: string;
    filename: string;
    document_type: string;
    confidence: number;
    status: string;
    co2e_kg: number | null;
  }>;
  errors: string[] | null;
  confirmation_email: {
    to: string;
    subject: string;
    body: string;
  };
}

// ==================== User & Auth Types ====================

export type UserRole = 'admin' | 'supervisor' | 'user';

export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  company_id: string;
  is_active: boolean;
  created_at: string;
  last_login: string | null;
}

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

// ==================== API Response Wrappers ====================

export interface ApiResponse<T> {
  data: T;
  status: 'success' | 'error';
  message?: string;
}

export interface ApiError {
  detail: string;
  status_code: number;
}

// ==================== Dashboard Types ====================

export interface DashboardMetrics {
  documentsProcessed: number;
  documentsToday: number;
  totalEmissions: number;
  autoApproveRate: number;
  pendingReview: number;
  recentActivity: Array<{
    id: string;
    action: string;
    user: string;
    timestamp: string;
  }>;
}

export interface ChartDataPoint {
  date: string;
  value: number;
  label?: string;
}

export interface CategoryBreakdown {
  category: string;
  count: number;
  emissions: number;
  percentage: number;
}

