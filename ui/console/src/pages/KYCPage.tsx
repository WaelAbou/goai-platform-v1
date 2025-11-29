import React, { useState, useEffect, useRef } from 'react';
import { 
  UserCheck, FileText, AlertTriangle, CheckCircle, 
  XCircle, Clock, Shield, Search, Plus, Eye,
  ChevronDown, ChevronUp, RefreshCw, Upload, Camera, Scan
} from 'lucide-react';
import { useToast } from '../components/Toast';

interface DocumentInput {
  document_type: string;
  document_number: string;
  issuing_country: string;
  issue_date: string;
  expiry_date: string;
  content: string;
}

interface CustomerInput {
  first_name: string;
  last_name: string;
  date_of_birth: string;
  nationality: string;
  email: string;
  phone: string;
  address: string;
  occupation: string;
  source_of_funds: string;
}

interface KYCCase {
  id: string;
  customer_id: string;
  status: string;
  risk_level: string;
  overall_score: number;
  created_at: string;
  request_data: {
    customer: CustomerInput;
  };
  response_data: {
    summary: string;
    recommendation: string;
    risk_assessment: {
      risk_factors: string[];
    };
  };
}

const DOCUMENT_TYPES = [
  { value: 'passport', label: 'Passport', icon: '🛂' },
  { value: 'drivers_license', label: "Driver's License", icon: '🚗' },
  { value: 'national_id', label: 'National ID', icon: '🆔' },
  { value: 'proof_of_address', label: 'Proof of Address', icon: '🏠' },
  { value: 'utility_bill', label: 'Utility Bill', icon: '💡' },
  { value: 'bank_statement', label: 'Bank Statement', icon: '🏦' },
];

const RISK_COLORS = {
  low: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  medium: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  high: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  critical: 'bg-red-500/20 text-red-400 border-red-500/30',
};

const STATUS_COLORS = {
  pending: 'bg-gray-500/20 text-gray-400',
  approved: 'bg-emerald-500/20 text-emerald-400',
  rejected: 'bg-red-500/20 text-red-400',
  manual_review: 'bg-amber-500/20 text-amber-400',
  escalated: 'bg-orange-500/20 text-orange-400',
};

export default function KYCPage() {
  const { showToast } = useToast();
  const [activeTab, setActiveTab] = useState<'verify' | 'cases' | 'stats'>('verify');
  const [loading, setLoading] = useState(false);
  const [cases, setCases] = useState<KYCCase[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [selectedCase, setSelectedCase] = useState<KYCCase | null>(null);
  const [result, setResult] = useState<any>(null);
  
  // Form state
  const [customer, setCustomer] = useState<CustomerInput>({
    first_name: '',
    last_name: '',
    date_of_birth: '',
    nationality: '',
    email: '',
    phone: '',
    address: '',
    occupation: '',
    source_of_funds: '',
  });
  
  const [documents, setDocuments] = useState<DocumentInput[]>([{
    document_type: 'passport',
    document_number: '',
    issuing_country: '',
    issue_date: '',
    expiry_date: '',
    content: '',
  }]);
  
  // OCR state
  const [ocrLoading, setOcrLoading] = useState<number | null>(null); // index of document being OCR'd
  const [ocrProviders, setOcrProviders] = useState<string[]>([]);
  const fileInputRefs = useRef<(HTMLInputElement | null)[]>([]);

  useEffect(() => {
    // Load available OCR providers
    fetch('/api/v1/ocr/providers')
      .then(res => res.json())
      .then(data => setOcrProviders(data.available_providers || []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (activeTab === 'cases') loadCases();
    if (activeTab === 'stats') loadStats();
  }, [activeTab]);

  const loadCases = async () => {
    try {
      const res = await fetch('/api/v1/kyc/cases');
      const data = await res.json();
      setCases(data.cases || []);
    } catch (error) {
      console.error('Failed to load cases:', error);
    }
  };

  const loadStats = async () => {
    try {
      const res = await fetch('/api/v1/kyc/stats');
      const data = await res.json();
      setStats(data);
    } catch (error) {
      console.error('Failed to load stats:', error);
    }
  };

  const handleVerify = async () => {
    if (!customer.first_name || !customer.last_name) {
      showToast('Please enter customer name', 'error');
      return;
    }
    
    if (!documents[0].content) {
      showToast('Please provide document content', 'error');
      return;
    }

    setLoading(true);
    setResult(null);
    
    try {
      const res = await fetch('/api/v1/kyc/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customer,
          documents,
          verification_type: 'standard',
          model: 'gpt-4o-mini'
        })
      });
      
      if (!res.ok) throw new Error('Verification failed');
      
      const data = await res.json();
      setResult(data);
      showToast('KYC verification completed', 'success');
      
    } catch (error) {
      showToast('Verification failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const addDocument = () => {
    setDocuments([...documents, {
      document_type: 'proof_of_address',
      document_number: '',
      issuing_country: '',
      issue_date: '',
      expiry_date: '',
      content: '',
    }]);
  };

  const removeDocument = (index: number) => {
    if (documents.length > 1) {
      setDocuments(documents.filter((_, i) => i !== index));
    }
  };

  const updateDocument = (index: number, field: string, value: string) => {
    const updated = [...documents];
    updated[index] = { ...updated[index], [field]: value };
    setDocuments(updated);
  };

  // OCR: Handle image upload and extract text
  const handleImageUpload = async (index: number, file: File) => {
    if (!file) return;
    
    // Check file type
    const validTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp', 'image/tiff'];
    if (!validTypes.includes(file.type)) {
      showToast('Please upload an image file (JPEG, PNG, GIF, WebP, BMP, or TIFF)', 'error');
      return;
    }
    
    // Check file size (max 20MB)
    if (file.size > 20 * 1024 * 1024) {
      showToast('File too large. Max 20MB.', 'error');
      return;
    }
    
    setOcrLoading(index);
    
    try {
      // Create FormData
      const formData = new FormData();
      formData.append('file', file);
      formData.append('document_type', documents[index].document_type);
      formData.append('extract_structured', 'true');
      
      const res = await fetch('/api/v1/ocr/extract/upload', {
        method: 'POST',
        body: formData,
      });
      
      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'OCR extraction failed');
      }
      
      const data = await res.json();
      
      // Update document content with extracted text
      updateDocument(index, 'content', data.text);
      
      // If structured data was extracted, try to fill in fields
      if (data.structured_data) {
        const sd = data.structured_data;
        if (sd.passport_number || sd.license_number || sd.id_number) {
          updateDocument(index, 'document_number', sd.passport_number || sd.license_number || sd.id_number || '');
        }
        if (sd.issuing_country || sd.issuing_state) {
          updateDocument(index, 'issuing_country', sd.issuing_country || sd.issuing_state || '');
        }
        if (sd.date_of_issue || sd.issue_date) {
          updateDocument(index, 'issue_date', sd.date_of_issue || sd.issue_date || '');
        }
        if (sd.date_of_expiry || sd.expiry_date) {
          updateDocument(index, 'expiry_date', sd.date_of_expiry || sd.expiry_date || '');
        }
        
        // Also update customer fields if this is an ID document
        if (sd.given_names || sd.full_name) {
          const names = (sd.given_names || sd.full_name || '').split(' ');
          if (names.length > 0 && !customer.first_name) {
            setCustomer(prev => ({ ...prev, first_name: names[0] }));
          }
        }
        if (sd.surname && !customer.last_name) {
          setCustomer(prev => ({ ...prev, last_name: sd.surname }));
        }
        if (sd.date_of_birth && !customer.date_of_birth) {
          setCustomer(prev => ({ ...prev, date_of_birth: sd.date_of_birth }));
        }
        if (sd.nationality && !customer.nationality) {
          setCustomer(prev => ({ ...prev, nationality: sd.nationality }));
        }
      }
      
      showToast(`Text extracted successfully (${data.confidence > 0.9 ? 'High' : 'Medium'} confidence, ${data.processing_time_ms}ms)`, 'success');
      
    } catch (error: any) {
      showToast(error.message || 'OCR extraction failed', 'error');
    } finally {
      setOcrLoading(null);
    }
  };

  const loadSampleData = () => {
    setCustomer({
      first_name: 'John',
      last_name: 'Smith',
      date_of_birth: '1985-06-15',
      nationality: 'United States',
      email: 'john.smith@email.com',
      phone: '+1-555-123-4567',
      address: '123 Main Street, New York, NY 10001',
      occupation: 'Software Engineer',
      source_of_funds: 'Employment Income',
    });
    setDocuments([{
      document_type: 'passport',
      document_number: 'US123456789',
      issuing_country: 'United States',
      issue_date: '2020-01-15',
      expiry_date: '2030-01-14',
      content: `PASSPORT
United States of America
      
Surname: SMITH
Given Names: JOHN
Nationality: AMERICAN
Date of Birth: 15 JUN 1985
Sex: M
Place of Birth: NEW YORK
Date of Issue: 15 JAN 2020
Date of Expiry: 14 JAN 2030
Passport No: US123456789

Machine Readable Zone:
P<USASMITH<<JOHN<<<<<<<<<<<<<<<<<<<<<<<<<<
US1234567899USA8506159M3001148<<<<<<<<<<<02`,
    }]);
    showToast('Sample data loaded', 'success');
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 
                          flex items-center justify-center shadow-lg shadow-violet-500/20">
            <UserCheck className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Customer KYC</h1>
            <p className="text-sm text-gray-400">Know Your Customer - AI-Powered Verification</p>
          </div>
        </div>
        
        {/* Tabs */}
        <div className="flex gap-2">
          {[
            { id: 'verify', label: 'New Verification', icon: Plus },
            { id: 'cases', label: 'Cases', icon: FileText },
            { id: 'stats', label: 'Statistics', icon: Shield },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-all ${
                activeTab === tab.id
                  ? 'bg-violet-500/20 text-violet-400 border border-violet-500/30'
                  : 'text-gray-400 hover:text-white hover:bg-white/5'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Verify Tab */}
      {activeTab === 'verify' && (
        <div className="grid grid-cols-2 gap-6">
          {/* Left: Form */}
          <div className="space-y-4">
            {/* Customer Info Card */}
            <div className="bg-gray-800/50 rounded-xl border border-gray-700/50 p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                  <UserCheck className="w-5 h-5 text-violet-400" />
                  Customer Information
                </h3>
                <button
                  onClick={loadSampleData}
                  className="text-xs px-3 py-1.5 rounded-lg bg-violet-500/20 text-violet-400 
                           hover:bg-violet-500/30 transition-all"
                >
                  Load Sample
                </button>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <input
                  type="text"
                  placeholder="First Name *"
                  value={customer.first_name}
                  onChange={e => setCustomer({...customer, first_name: e.target.value})}
                  className="bg-gray-900/50 border border-gray-700/50 rounded-lg px-4 py-2.5 
                           text-white placeholder-gray-500 focus:border-violet-500/50 focus:outline-none"
                />
                <input
                  type="text"
                  placeholder="Last Name *"
                  value={customer.last_name}
                  onChange={e => setCustomer({...customer, last_name: e.target.value})}
                  className="bg-gray-900/50 border border-gray-700/50 rounded-lg px-4 py-2.5 
                           text-white placeholder-gray-500 focus:border-violet-500/50 focus:outline-none"
                />
                <input
                  type="date"
                  placeholder="Date of Birth"
                  value={customer.date_of_birth}
                  onChange={e => setCustomer({...customer, date_of_birth: e.target.value})}
                  className="bg-gray-900/50 border border-gray-700/50 rounded-lg px-4 py-2.5 
                           text-white placeholder-gray-500 focus:border-violet-500/50 focus:outline-none"
                />
                <input
                  type="text"
                  placeholder="Nationality"
                  value={customer.nationality}
                  onChange={e => setCustomer({...customer, nationality: e.target.value})}
                  className="bg-gray-900/50 border border-gray-700/50 rounded-lg px-4 py-2.5 
                           text-white placeholder-gray-500 focus:border-violet-500/50 focus:outline-none"
                />
                <input
                  type="email"
                  placeholder="Email"
                  value={customer.email}
                  onChange={e => setCustomer({...customer, email: e.target.value})}
                  className="bg-gray-900/50 border border-gray-700/50 rounded-lg px-4 py-2.5 
                           text-white placeholder-gray-500 focus:border-violet-500/50 focus:outline-none"
                />
                <input
                  type="tel"
                  placeholder="Phone"
                  value={customer.phone}
                  onChange={e => setCustomer({...customer, phone: e.target.value})}
                  className="bg-gray-900/50 border border-gray-700/50 rounded-lg px-4 py-2.5 
                           text-white placeholder-gray-500 focus:border-violet-500/50 focus:outline-none"
                />
                <input
                  type="text"
                  placeholder="Address"
                  value={customer.address}
                  onChange={e => setCustomer({...customer, address: e.target.value})}
                  className="col-span-2 bg-gray-900/50 border border-gray-700/50 rounded-lg px-4 py-2.5 
                           text-white placeholder-gray-500 focus:border-violet-500/50 focus:outline-none"
                />
                <input
                  type="text"
                  placeholder="Occupation"
                  value={customer.occupation}
                  onChange={e => setCustomer({...customer, occupation: e.target.value})}
                  className="bg-gray-900/50 border border-gray-700/50 rounded-lg px-4 py-2.5 
                           text-white placeholder-gray-500 focus:border-violet-500/50 focus:outline-none"
                />
                <input
                  type="text"
                  placeholder="Source of Funds"
                  value={customer.source_of_funds}
                  onChange={e => setCustomer({...customer, source_of_funds: e.target.value})}
                  className="bg-gray-900/50 border border-gray-700/50 rounded-lg px-4 py-2.5 
                           text-white placeholder-gray-500 focus:border-violet-500/50 focus:outline-none"
                />
              </div>
            </div>

            {/* Documents */}
            {documents.map((doc, index) => (
              <div key={index} className="bg-gray-800/50 rounded-xl border border-gray-700/50 p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                    <FileText className="w-5 h-5 text-blue-400" />
                    Document {index + 1}
                  </h3>
                  {documents.length > 1 && (
                    <button
                      onClick={() => removeDocument(index)}
                      className="text-red-400 hover:text-red-300 text-sm"
                    >
                      Remove
                    </button>
                  )}
                </div>
                
                <div className="space-y-4">
                  <select
                    value={doc.document_type}
                    onChange={e => updateDocument(index, 'document_type', e.target.value)}
                    className="w-full bg-gray-900/50 border border-gray-700/50 rounded-lg px-4 py-2.5 
                             text-white focus:border-violet-500/50 focus:outline-none"
                  >
                    {DOCUMENT_TYPES.map(type => (
                      <option key={type.value} value={type.value}>
                        {type.icon} {type.label}
                      </option>
                    ))}
                  </select>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <input
                      type="text"
                      placeholder="Document Number"
                      value={doc.document_number}
                      onChange={e => updateDocument(index, 'document_number', e.target.value)}
                      className="bg-gray-900/50 border border-gray-700/50 rounded-lg px-4 py-2.5 
                               text-white placeholder-gray-500 focus:border-violet-500/50 focus:outline-none"
                    />
                    <input
                      type="text"
                      placeholder="Issuing Country"
                      value={doc.issuing_country}
                      onChange={e => updateDocument(index, 'issuing_country', e.target.value)}
                      className="bg-gray-900/50 border border-gray-700/50 rounded-lg px-4 py-2.5 
                               text-white placeholder-gray-500 focus:border-violet-500/50 focus:outline-none"
                    />
                    <input
                      type="date"
                      placeholder="Issue Date"
                      value={doc.issue_date}
                      onChange={e => updateDocument(index, 'issue_date', e.target.value)}
                      className="bg-gray-900/50 border border-gray-700/50 rounded-lg px-4 py-2.5 
                               text-white placeholder-gray-500 focus:border-violet-500/50 focus:outline-none"
                    />
                    <input
                      type="date"
                      placeholder="Expiry Date"
                      value={doc.expiry_date}
                      onChange={e => updateDocument(index, 'expiry_date', e.target.value)}
                      className="bg-gray-900/50 border border-gray-700/50 rounded-lg px-4 py-2.5 
                               text-white placeholder-gray-500 focus:border-violet-500/50 focus:outline-none"
                    />
                  </div>
                  
                  {/* OCR Upload Section */}
                  <div className="flex items-center gap-3 p-3 bg-gray-900/30 rounded-lg border border-dashed border-gray-600/50">
                    <input
                      type="file"
                      ref={el => fileInputRefs.current[index] = el}
                      onChange={e => {
                        const file = e.target.files?.[0];
                        if (file) handleImageUpload(index, file);
                        e.target.value = ''; // Reset input
                      }}
                      accept="image/*"
                      className="hidden"
                    />
                    <button
                      type="button"
                      onClick={() => fileInputRefs.current[index]?.click()}
                      disabled={ocrLoading === index}
                      className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-500/20 text-blue-400 
                               hover:bg-blue-500/30 border border-blue-500/30 transition-all disabled:opacity-50"
                    >
                      {ocrLoading === index ? (
                        <>
                          <RefreshCw className="w-4 h-4 animate-spin" />
                          Extracting...
                        </>
                      ) : (
                        <>
                          <Scan className="w-4 h-4" />
                          Upload & OCR
                        </>
                      )}
                    </button>
                    <div className="flex-1">
                      <p className="text-sm text-gray-400">
                        Upload ID photo for automatic text extraction
                      </p>
                      <p className="text-xs text-gray-500">
                        Supports: JPEG, PNG, WebP • Max 20MB
                        {ocrProviders.length > 0 && (
                          <span className="ml-2 text-emerald-400">
                            • OCR: {ocrProviders.includes('gpt4_vision') ? 'GPT-4V' : ocrProviders[0]}
                          </span>
                        )}
                      </p>
                    </div>
                  </div>

                  <textarea
                    placeholder="Document content will appear here after OCR, or paste text manually *"
                    value={doc.content}
                    onChange={e => updateDocument(index, 'content', e.target.value)}
                    rows={6}
                    className="w-full bg-gray-900/50 border border-gray-700/50 rounded-lg px-4 py-3 
                             text-white placeholder-gray-500 focus:border-violet-500/50 focus:outline-none 
                             font-mono text-sm"
                  />
                </div>
              </div>
            ))}

            {/* Action Buttons */}
            <div className="flex gap-4">
              <button
                onClick={addDocument}
                className="flex-1 py-3 rounded-xl bg-gray-700/50 text-gray-300 
                         hover:bg-gray-700 transition-all flex items-center justify-center gap-2"
              >
                <Plus className="w-4 h-4" />
                Add Document
              </button>
              <button
                onClick={handleVerify}
                disabled={loading}
                className="flex-1 py-3 rounded-xl bg-gradient-to-r from-violet-500 to-purple-600 
                         text-white font-medium hover:from-violet-600 hover:to-purple-700 
                         disabled:opacity-50 transition-all flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Verifying...
                  </>
                ) : (
                  <>
                    <Shield className="w-4 h-4" />
                    Run KYC Verification
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Right: Results */}
          <div className="space-y-4">
            {result ? (
              <>
                {/* Status Card */}
                <div className={`rounded-xl border p-6 ${
                  result.status === 'approved' ? 'bg-emerald-500/10 border-emerald-500/30' :
                  result.status === 'rejected' ? 'bg-red-500/10 border-red-500/30' :
                  result.status === 'escalated' ? 'bg-orange-500/10 border-orange-500/30' :
                  'bg-amber-500/10 border-amber-500/30'
                }`}>
                  <div className="flex items-center gap-4 mb-4">
                    {result.status === 'approved' ? (
                      <CheckCircle className="w-12 h-12 text-emerald-400" />
                    ) : result.status === 'rejected' ? (
                      <XCircle className="w-12 h-12 text-red-400" />
                    ) : result.status === 'escalated' ? (
                      <AlertTriangle className="w-12 h-12 text-orange-400" />
                    ) : (
                      <Clock className="w-12 h-12 text-amber-400" />
                    )}
                    <div>
                      <p className="text-2xl font-bold text-white capitalize">{result.status.replace('_', ' ')}</p>
                      <p className="text-sm text-gray-400">Verification ID: {result.verification_id}</p>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-3 gap-4 mt-4">
                    <div className="bg-black/20 rounded-lg p-3 text-center">
                      <p className="text-3xl font-bold text-white">{result.overall_score}</p>
                      <p className="text-xs text-gray-400">Overall Score</p>
                    </div>
                    <div className="bg-black/20 rounded-lg p-3 text-center">
                      <span className={`px-2 py-1 rounded text-sm font-medium ${RISK_COLORS[result.risk_assessment.risk_level as keyof typeof RISK_COLORS]}`}>
                        {result.risk_assessment.risk_level.toUpperCase()}
                      </span>
                      <p className="text-xs text-gray-400 mt-1">Risk Level</p>
                    </div>
                    <div className="bg-black/20 rounded-lg p-3 text-center">
                      <p className="text-2xl font-bold text-white">{result.processing_time_ms}ms</p>
                      <p className="text-xs text-gray-400">Processing Time</p>
                    </div>
                  </div>
                </div>

                {/* Recommendation */}
                <div className="bg-gray-800/50 rounded-xl border border-gray-700/50 p-6">
                  <h3 className="text-lg font-semibold text-white mb-3">📋 Recommendation</h3>
                  <p className="text-gray-300">{result.recommendation}</p>
                </div>

                {/* Summary */}
                <div className="bg-gray-800/50 rounded-xl border border-gray-700/50 p-6">
                  <h3 className="text-lg font-semibold text-white mb-3">📝 Verification Summary</h3>
                  <div className="text-gray-300 whitespace-pre-wrap text-sm">{result.summary}</div>
                </div>

                {/* Risk Factors */}
                {result.risk_assessment.risk_factors.length > 0 && (
                  <div className="bg-gray-800/50 rounded-xl border border-gray-700/50 p-6">
                    <h3 className="text-lg font-semibold text-white mb-3">⚠️ Risk Factors</h3>
                    <ul className="space-y-2">
                      {result.risk_assessment.risk_factors.map((factor: string, i: number) => (
                        <li key={i} className="flex items-center gap-2 text-gray-300">
                          <AlertTriangle className="w-4 h-4 text-amber-400" />
                          {factor}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Required Actions */}
                {result.required_actions.length > 0 && (
                  <div className="bg-gray-800/50 rounded-xl border border-gray-700/50 p-6">
                    <h3 className="text-lg font-semibold text-white mb-3">📌 Required Actions</h3>
                    <ul className="space-y-2">
                      {result.required_actions.map((action: string, i: number) => (
                        <li key={i} className="flex items-center gap-2 text-gray-300">
                          <span className="w-6 h-6 rounded-full bg-violet-500/20 text-violet-400 
                                         flex items-center justify-center text-xs font-bold">
                            {i + 1}
                          </span>
                          {action}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </>
            ) : (
              <div className="h-full flex items-center justify-center">
                <div className="text-center text-gray-500">
                  <Shield className="w-16 h-16 mx-auto mb-4 opacity-20" />
                  <p>Enter customer details and run verification</p>
                  <p className="text-sm mt-2">Results will appear here</p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Cases Tab */}
      {activeTab === 'cases' && (
        <div className="bg-gray-800/50 rounded-xl border border-gray-700/50 overflow-hidden">
          <div className="p-4 border-b border-gray-700/50 flex items-center justify-between">
            <h3 className="font-semibold text-white">KYC Cases</h3>
            <button
              onClick={loadCases}
              className="text-gray-400 hover:text-white transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
          
          {cases.length === 0 ? (
            <div className="p-12 text-center text-gray-500">
              <FileText className="w-12 h-12 mx-auto mb-3 opacity-20" />
              <p>No KYC cases yet</p>
              <p className="text-sm">Run a verification to create your first case</p>
            </div>
          ) : (
            <table className="w-full">
              <thead className="bg-gray-900/50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Customer</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Risk</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Score</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Date</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700/50">
                {cases.map(c => (
                  <tr key={c.id} className="hover:bg-gray-700/30 transition-colors">
                    <td className="px-4 py-3">
                      <p className="text-white font-medium">
                        {c.request_data.customer.first_name} {c.request_data.customer.last_name}
                      </p>
                      <p className="text-xs text-gray-500">{c.id}</p>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${STATUS_COLORS[c.status as keyof typeof STATUS_COLORS]}`}>
                        {c.status.replace('_', ' ').toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded text-xs font-medium border ${RISK_COLORS[c.risk_level as keyof typeof RISK_COLORS]}`}>
                        {c.risk_level.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-white font-mono">{c.overall_score}</span>
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-sm">
                      {new Date(c.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => setSelectedCase(c)}
                        className="text-violet-400 hover:text-violet-300 transition-colors"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Stats Tab */}
      {activeTab === 'stats' && stats && (
        <div className="grid grid-cols-4 gap-6">
          <div className="bg-gray-800/50 rounded-xl border border-gray-700/50 p-6">
            <p className="text-4xl font-bold text-white">{stats.total_cases}</p>
            <p className="text-gray-400">Total Cases</p>
          </div>
          <div className="bg-gray-800/50 rounded-xl border border-gray-700/50 p-6">
            <p className="text-4xl font-bold text-emerald-400">{stats.approval_rate}%</p>
            <p className="text-gray-400">Approval Rate</p>
          </div>
          <div className="bg-gray-800/50 rounded-xl border border-gray-700/50 p-6">
            <p className="text-4xl font-bold text-violet-400">{stats.average_score}</p>
            <p className="text-gray-400">Avg Score</p>
          </div>
          <div className="bg-gray-800/50 rounded-xl border border-gray-700/50 p-6">
            <p className="text-4xl font-bold text-amber-400">{stats.by_status?.manual_review || 0}</p>
            <p className="text-gray-400">Pending Review</p>
          </div>

          {/* Status Breakdown */}
          <div className="col-span-2 bg-gray-800/50 rounded-xl border border-gray-700/50 p-6">
            <h3 className="font-semibold text-white mb-4">By Status</h3>
            <div className="space-y-3">
              {Object.entries(stats.by_status || {}).map(([status, count]) => (
                <div key={status} className="flex items-center justify-between">
                  <span className={`px-2 py-1 rounded text-xs font-medium ${STATUS_COLORS[status as keyof typeof STATUS_COLORS]}`}>
                    {status.replace('_', ' ').toUpperCase()}
                  </span>
                  <span className="text-white font-mono">{count as number}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Risk Breakdown */}
          <div className="col-span-2 bg-gray-800/50 rounded-xl border border-gray-700/50 p-6">
            <h3 className="font-semibold text-white mb-4">By Risk Level</h3>
            <div className="space-y-3">
              {Object.entries(stats.by_risk_level || {}).map(([risk, count]) => (
                <div key={risk} className="flex items-center justify-between">
                  <span className={`px-2 py-1 rounded text-xs font-medium border ${RISK_COLORS[risk as keyof typeof RISK_COLORS]}`}>
                    {risk.toUpperCase()}
                  </span>
                  <span className="text-white font-mono">{count as number}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Case Detail Modal */}
      {selectedCase && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4"
             onClick={() => setSelectedCase(null)}>
          <div className="bg-gray-800 rounded-xl border border-gray-700 max-w-2xl w-full max-h-[80vh] overflow-y-auto"
               onClick={e => e.stopPropagation()}>
            <div className="p-6 border-b border-gray-700 flex items-center justify-between">
              <h3 className="text-xl font-bold text-white">Case Details</h3>
              <button onClick={() => setSelectedCase(null)} className="text-gray-400 hover:text-white">
                ✕
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-gray-400 text-sm">Customer</p>
                  <p className="text-white font-medium">
                    {selectedCase.request_data.customer.first_name} {selectedCase.request_data.customer.last_name}
                  </p>
                </div>
                <div>
                  <p className="text-gray-400 text-sm">Status</p>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${STATUS_COLORS[selectedCase.status as keyof typeof STATUS_COLORS]}`}>
                    {selectedCase.status.replace('_', ' ').toUpperCase()}
                  </span>
                </div>
                <div>
                  <p className="text-gray-400 text-sm">Risk Level</p>
                  <span className={`px-2 py-1 rounded text-xs font-medium border ${RISK_COLORS[selectedCase.risk_level as keyof typeof RISK_COLORS]}`}>
                    {selectedCase.risk_level.toUpperCase()}
                  </span>
                </div>
                <div>
                  <p className="text-gray-400 text-sm">Score</p>
                  <p className="text-white font-mono">{selectedCase.overall_score}/100</p>
                </div>
              </div>
              
              <div>
                <p className="text-gray-400 text-sm mb-2">Summary</p>
                <div className="bg-gray-900/50 rounded-lg p-4 text-gray-300 text-sm whitespace-pre-wrap">
                  {selectedCase.response_data.summary}
                </div>
              </div>
              
              <div>
                <p className="text-gray-400 text-sm mb-2">Recommendation</p>
                <p className="text-white">{selectedCase.response_data.recommendation}</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

