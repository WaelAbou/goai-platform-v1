import { useState, useCallback, useRef } from 'react'
import { 
  Upload as UploadIcon, 
  FileText, 
  CheckCircle,
  AlertCircle,
  Loader2,
  ImageIcon,
  FileUp
} from 'lucide-react'

interface ProcessResult {
  status: string
  document_type: string
  confidence: number
  extracted_data: Record<string, any>
  calculated_co2e_kg: number | null
  calculated_co2e_tonnes?: number
  company_id?: string
  emission_equivalents?: {
    trees_needed: number
    car_km: number
  }
}

export default function Upload() {
  const [dragOver, setDragOver] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [result, setResult] = useState<ProcessResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [textInput, setTextInput] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  
  // File input ref for programmatic clicking
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    
    const file = e.dataTransfer.files[0]
    if (file) {
      setSelectedFile(file)
      handleFile(file)
    }
  }, [])

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setSelectedFile(file)
      handleFile(file)
    }
  }

  const openFilePicker = () => {
    fileInputRef.current?.click()
  }

  const handleFile = async (file: File) => {
    setProcessing(true)
    setError(null)
    setResult(null)

    const formData = new FormData()
    formData.append('file', file)
    formData.append('company_id', 'xyz-corp-001')

    try {
      const res = await fetch('/api/v1/sustainability/smart/process-image', {
        method: 'POST',
        body: formData
      })
      const data = await res.json()
      
      if (!res.ok || data.detail || data.error) {
        setError(data.detail || data.error || 'Failed to process file')
      } else {
        setResult(data)
      }
    } catch (err) {
      setError('Failed to process file - server error')
    }
    setProcessing(false)
  }

  const handleTextSubmit = async () => {
    if (!textInput.trim()) return

    setProcessing(true)
    setError(null)
    setResult(null)

    try {
      const res = await fetch('/api/v1/sustainability/smart/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text_content: textInput,
          company_id: 'xyz-corp-001'
        })
      })
      const data = await res.json()
      
      if (!res.ok || data.detail || data.error) {
        setError(data.detail || data.error || 'Failed to process text')
      } else {
        setResult(data)
      }
    } catch (err) {
      setError('Failed to process text - server error')
    }
    setProcessing(false)
  }

  const formatDocType = (type: string) => 
    type ? type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) : 'Unknown'

  const handleAddToQueue = async () => {
    if (!result) return
    
    setProcessing(true)
    try {
      const res = await fetch('/api/v1/review/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text_content: textInput || 'Uploaded document',
          source: 'web_upload',
          filename: selectedFile?.name || `document_${Date.now()}.txt`,
          uploaded_by: 'dashboard_user',
          company_id: result.company_id || 'xyz-corp-001'
        })
      })
      
      if (res.ok) {
        alert('✅ Document added to review queue!')
        setResult(null)
        setTextInput('')
        setSelectedFile(null)
      } else {
        const data = await res.json()
        setError(data.detail || 'Failed to add to queue')
      }
    } catch (err) {
      setError('Failed to add to queue')
    }
    setProcessing(false)
  }

  const resetUpload = () => {
    setResult(null)
    setTextInput('')
    setSelectedFile(null)
    setError(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Upload Document</h1>
        <p className="text-slate-400">Upload sustainability documents for AI-powered extraction</p>
      </div>

      {/* Hidden File Input */}
      <input
        ref={fileInputRef}
        type="file"
        onChange={handleFileSelect}
        className="hidden"
        id="file-upload"
      />

      {/* Upload Zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-2xl p-12 text-center transition-all ${
          dragOver 
            ? 'border-emerald-500 bg-emerald-500/10' 
            : 'border-slate-600 hover:border-slate-500'
        }`}
      >
        <div className="space-y-4">
          <div className="w-16 h-16 bg-slate-700 rounded-2xl flex items-center justify-center mx-auto">
            {processing ? (
              <Loader2 className="w-8 h-8 text-emerald-500 animate-spin" />
            ) : (
              <UploadIcon className="w-8 h-8 text-slate-400" />
            )}
          </div>
          
          {selectedFile ? (
            <div>
              <p className="text-lg font-medium text-white">{selectedFile.name}</p>
              <p className="text-slate-400">{(selectedFile.size / 1024).toFixed(1)} KB</p>
            </div>
          ) : (
            <div>
              <p className="text-lg font-medium text-white">Drag & drop your document here</p>
              <p className="text-slate-400">or use the button below</p>
            </div>
          )}
          
          {/* Explicit Browse Button */}
          <button
            type="button"
            onClick={openFilePicker}
            disabled={processing}
            className="px-6 py-3 bg-emerald-500 text-white rounded-xl hover:bg-emerald-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center gap-2"
          >
            <FileUp className="w-5 h-5" />
            {processing ? 'Processing...' : 'Browse Files'}
          </button>
          
          <p className="text-sm text-slate-500">
            📄 PDF • 🖼️ PNG, JPG, GIF, WebP • 📝 TXT
          </p>
        </div>
      </div>

      {/* Or Divider */}
      <div className="flex items-center gap-4">
        <div className="flex-1 h-px bg-slate-700" />
        <span className="text-slate-500">or paste text</span>
        <div className="flex-1 h-px bg-slate-700" />
      </div>

      {/* Text Input */}
      <div className="space-y-4">
        <textarea
          value={textInput}
          onChange={(e) => setTextInput(e.target.value)}
          placeholder="Paste utility bill, receipt, or invoice text here...

Example:
Pacific Gas & Electric
Account: 1234567890
Service Address: 123 Main St, SF
Billing Period: January 2024
Usage: 500 kWh
Amount Due: $95.00"
          className="w-full h-48 px-4 py-3 bg-slate-800 border border-slate-700 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 resize-none"
        />
        <button
          onClick={handleTextSubmit}
          disabled={!textInput.trim() || processing}
          className="w-full py-3 bg-emerald-500 text-white rounded-xl hover:bg-emerald-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {processing ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Processing...
            </>
          ) : (
            <>
              <FileText className="w-5 h-5" />
              Process Text
            </>
          )}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-500/20 border border-red-500/50 rounded-xl flex items-center gap-3 text-red-500">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Result */}
      {result && result.status === 'success' && (
        <div className="bg-slate-800 rounded-2xl border border-slate-700 overflow-hidden animate-slide-up">
          <div className="p-6 border-b border-slate-700 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-emerald-500/20 rounded-xl flex items-center justify-center">
                <CheckCircle className="w-6 h-6 text-emerald-500" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white">
                  {formatDocType(result.document_type)}
                </h3>
                <p className="text-slate-400">
                  {Math.round((result.confidence || 0) * 100)}% confidence
                </p>
              </div>
            </div>
            {result.calculated_co2e_kg && result.calculated_co2e_kg > 0 && (
              <div className="text-right">
                <p className="text-2xl font-bold text-emerald-500">
                  {result.calculated_co2e_kg >= 1000 
                    ? `${(result.calculated_co2e_kg / 1000).toFixed(2)}t`
                    : `${result.calculated_co2e_kg.toFixed(1)} kg`
                  }
                </p>
                <p className="text-slate-400 text-sm">CO₂e</p>
              </div>
            )}
          </div>

          <div className="p-6 space-y-4">
            <h4 className="font-medium text-white">Extracted Data</h4>
            <ExtractedDataGrid data={result.extracted_data} />

            {result.emission_equivalents && (
              <div className="p-4 bg-emerald-500/10 rounded-xl">
                <h4 className="font-medium text-emerald-500 mb-2">Environmental Impact</h4>
                <div className="flex gap-6 text-slate-300">
                  <span>🌳 {result.emission_equivalents.trees_needed.toFixed(0)} trees needed to offset</span>
                  <span>🚗 Equivalent to {result.emission_equivalents.car_km.toFixed(0)} km driving</span>
                </div>
              </div>
            )}
          </div>

          <div className="p-6 border-t border-slate-700 flex gap-4">
            <button 
              onClick={resetUpload}
              className="flex-1 py-3 bg-slate-700 text-white rounded-xl hover:bg-slate-600 transition-colors"
            >
              Upload Another
            </button>
            <button 
              onClick={handleAddToQueue}
              disabled={processing}
              className="flex-1 py-3 bg-emerald-500 text-white rounded-xl hover:bg-emerald-600 transition-colors disabled:opacity-50"
            >
              {processing ? 'Adding...' : 'Add to Review Queue'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// Separate component to handle extracted data display
function ExtractedDataGrid({ data }: { data: any }) {
  // Normalize data - handle array or object
  let normalized: Record<string, any> = {};
  
  if (Array.isArray(data) && data.length > 0) {
    normalized = data[0];
  } else if (data && typeof data === 'object' && !Array.isArray(data)) {
    normalized = data;
  }
  
  // Filter out null/undefined values
  const entries = Object.entries(normalized).filter(
    ([key, value]) => value !== null && value !== undefined && key !== 'raw_text'
  );
  
  if (entries.length === 0) {
    return (
      <div className="p-4 bg-slate-700/30 rounded-lg">
        <p className="text-slate-400">No structured data extracted</p>
      </div>
    );
  }
  
  return (
    <div className="grid grid-cols-2 gap-4">
      {entries.map(([key, value]) => (
        <div key={key} className="p-3 bg-slate-700/50 rounded-lg">
          <p className="text-sm text-slate-400 capitalize">
            {key.replace(/_/g, ' ')}
          </p>
          <p className="text-white font-medium">
            {formatValue(value)}
          </p>
        </div>
      ))}
    </div>
  );
}

function formatValue(value: any): string {
  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No';
  }
  if (typeof value === 'object') {
    return JSON.stringify(value);
  }
  return String(value);
}
