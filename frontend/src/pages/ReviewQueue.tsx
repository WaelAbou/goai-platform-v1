import { useEffect, useState } from 'react'
import { 
  Search, 
  Filter, 
  CheckCircle, 
  XCircle, 
  Eye,
  ChevronDown,
  Zap,
  FileText,
  Plane,
  Fuel,
  Truck,
  Leaf,
  Lock,
  Trash2
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'

interface ReviewItem {
  id: string
  document_type: string
  category: string
  source: string
  filename: string
  uploaded_by: string
  uploaded_at: string
  confidence: number
  confidence_level: string
  extracted_data: Record<string, any>
  calculated_co2e_kg: number | null
  status: string
}

const categoryIcons: Record<string, any> = {
  energy: Zap,
  travel: Plane,
  fleet: Fuel,
  shipping: Truck,
  default: FileText
}

export default function ReviewQueue() {
  const { user, permissions, hasPermission } = useAuth()
  const [items, setItems] = useState<ReviewItem[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState({ status: 'pending', confidence: '', category: '' })
  const [selectedItem, setSelectedItem] = useState<ReviewItem | null>(null)

  const fetchQueue = () => {
    const params = new URLSearchParams()
    if (filter.status) params.append('status', filter.status)
    if (filter.confidence) params.append('confidence', filter.confidence)
    if (filter.category) params.append('category', filter.category)
    
    fetch(`/api/v1/review/queue?${params}`)
      .then(res => res.json())
      .then(data => {
        setItems(data.items || [])
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }

  useEffect(() => {
    fetchQueue()
  }, [filter])

  const handleApprove = async (id: string) => {
    if (!hasPermission('canApprove')) return
    
    await fetch(`/api/v1/review/queue/${id}/approve?user=${user?.email}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    })
    fetchQueue()
  }

  const handleReject = async (id: string) => {
    if (!hasPermission('canReject')) return
    
    const reason = prompt('Reason for rejection:')
    if (!reason) return
    
    await fetch(`/api/v1/review/queue/${id}/reject?user=${user?.email}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason })
    })
    fetchQueue()
  }

  const handleClearRejected = async () => {
    if (!hasPermission('canApprove')) return
    
    const rejectedItems = items.filter(i => i.status === 'rejected')
    if (rejectedItems.length === 0) {
      alert('No rejected items to clear')
      return
    }
    
    const confirmed = confirm(`Are you sure you want to permanently delete ${rejectedItems.length} rejected item(s)?`)
    if (!confirmed) return
    
    // Delete all rejected items
    await fetch(`/api/v1/review/queue/bulk-delete?user=${user?.email}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        item_ids: rejectedItems.map(i => i.id),
        reason: 'Bulk clear rejected items'
      })
    })
    fetchQueue()
  }

  const handleClearApproved = async () => {
    if (!hasPermission('canApprove')) return
    
    const approvedItems = items.filter(i => i.status === 'approved' || i.status === 'auto_approved')
    if (approvedItems.length === 0) {
      alert('No approved items to clear')
      return
    }
    
    const confirmed = confirm(`Are you sure you want to permanently delete ${approvedItems.length} approved item(s)?`)
    if (!confirmed) return
    
    await fetch(`/api/v1/review/queue/bulk-delete?user=${user?.email}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        item_ids: approvedItems.map(i => i.id),
        reason: 'Bulk clear approved items'
      })
    })
    fetchQueue()
  }

  const handleDelete = async (id: string) => {
    if (!hasPermission('canApprove')) return
    
    const confirmed = confirm('Are you sure you want to permanently delete this item?')
    if (!confirmed) return
    
    const reason = prompt('Reason for deletion (optional):') || 'Manual deletion'
    
    await fetch(`/api/v1/review/queue/${id}?user=${user?.email}&reason=${encodeURIComponent(reason)}`, {
      method: 'DELETE'
    })
    fetchQueue()
  }

  const handleBulkApprove = async () => {
    if (!hasPermission('canBulkApprove')) return
    
    const highConfidence = items.filter(i => i.status === 'pending' && i.confidence >= 0.9)
    if (highConfidence.length === 0) {
      alert('No high confidence items to approve')
      return
    }
    
    await fetch(`/api/v1/review/queue/bulk-approve?user=${user?.email}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        item_ids: highConfidence.map(i => i.id),
        min_confidence: 0.9
      })
    })
    fetchQueue()
  }

  const formatDocType = (type: string) => 
    type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())

  const formatEmissions = (kg: number) => 
    kg >= 1000 ? `${(kg / 1000).toFixed(2)}t` : `${kg.toFixed(0)} kg`

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Review Queue</h1>
          <p className="text-slate-400">
            {hasPermission('canApprove') 
              ? 'Review and approve sustainability documents'
              : 'View pending documents (read-only)'
            }
          </p>
        </div>
        {!hasPermission('canBulkApprove') && (
          <div className="flex items-center gap-2 px-4 py-2 bg-slate-700 text-slate-400 rounded-xl cursor-not-allowed">
            <Lock className="w-5 h-5" />
            <span className="text-sm">Supervisor access required</span>
          </div>
        )}
      </div>

      {/* Permission Notice */}
      {!hasPermission('canApprove') && (
        <div className="p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-xl flex items-center gap-3">
          <Lock className="w-5 h-5 text-yellow-500" />
          <div>
            <p className="text-yellow-500 font-medium">View-Only Mode</p>
            <p className="text-sm text-yellow-500/70">
              Your current role ({permissions.label}) can view but not approve/reject documents.
            </p>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      {hasPermission('canApprove') && (
        <div className="flex flex-wrap gap-3">
          <button 
            onClick={handleBulkApprove}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-500 text-white rounded-xl hover:bg-emerald-600 transition-colors"
          >
            <CheckCircle className="w-5 h-5" />
            Bulk Approve High Confidence
          </button>
          <button 
            onClick={handleClearRejected}
            className="flex items-center gap-2 px-4 py-2 bg-red-500/20 text-red-500 border border-red-500/30 rounded-xl hover:bg-red-500 hover:text-white transition-colors"
          >
            <Trash2 className="w-5 h-5" />
            Clear Rejected
          </button>
          <button 
            onClick={handleClearApproved}
            className="flex items-center gap-2 px-4 py-2 bg-slate-700 text-slate-300 rounded-xl hover:bg-slate-600 transition-colors"
          >
            <Trash2 className="w-5 h-5" />
            Clear Approved
          </button>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-4">
        <select
          value={filter.status}
          onChange={(e) => setFilter({ ...filter, status: e.target.value })}
          className="px-4 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white focus:outline-none focus:border-emerald-500"
        >
          <option value="">All Status</option>
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
          <option value="auto_approved">Auto-Approved</option>
          <option value="rejected">Rejected</option>
        </select>

        <select
          value={filter.confidence}
          onChange={(e) => setFilter({ ...filter, confidence: e.target.value })}
          className="px-4 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white focus:outline-none focus:border-emerald-500"
        >
          <option value="">All Confidence</option>
          <option value="high">🟢 High (&gt;90%)</option>
          <option value="medium">🟡 Medium (70-90%)</option>
          <option value="low">🔴 Low (&lt;70%)</option>
        </select>

        <select
          value={filter.category}
          onChange={(e) => setFilter({ ...filter, category: e.target.value })}
          className="px-4 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white focus:outline-none focus:border-emerald-500"
        >
          <option value="">All Categories</option>
          <option value="energy">⚡ Energy</option>
          <option value="travel">✈️ Travel</option>
          <option value="fleet">🚗 Fleet</option>
          <option value="shipping">📦 Shipping</option>
        </select>

        <button 
          onClick={fetchQueue}
          className="px-4 py-2 bg-slate-700 text-white rounded-xl hover:bg-slate-600 transition-colors"
        >
          🔄 Refresh
        </button>
      </div>

      {/* Queue Table */}
      <div className="bg-slate-800 rounded-2xl border border-slate-700 overflow-hidden">
        {/* Table Header */}
        <div className="grid grid-cols-7 gap-4 p-4 bg-slate-700/50 text-sm font-medium text-slate-400 uppercase tracking-wider">
          <div>Confidence</div>
          <div className="col-span-2">Document</div>
          <div>Category</div>
          <div>Emissions</div>
          <div>Uploaded</div>
          <div>Actions</div>
        </div>

        {/* Table Body */}
        {loading ? (
          <div className="p-8 text-center text-slate-400">
            <div className="animate-spin w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full mx-auto mb-4" />
            Loading...
          </div>
        ) : items.length === 0 ? (
          <div className="p-8 text-center text-slate-400">
            <Leaf className="w-12 h-12 mx-auto mb-4 opacity-50" />
            No items to review
          </div>
        ) : (
          items.map((item) => {
            const Icon = categoryIcons[item.category] || categoryIcons.default
            const confidenceColor = 
              item.confidence >= 0.9 ? 'bg-emerald-500' :
              item.confidence >= 0.7 ? 'bg-yellow-500' : 'bg-red-500'
            
            return (
              <div 
                key={item.id} 
                className="grid grid-cols-7 gap-4 p-4 border-t border-slate-700 hover:bg-slate-700/30 transition-colors items-center"
              >
                <div className="flex items-center gap-2">
                  <span className={`w-3 h-3 rounded-full ${confidenceColor}`} />
                  <span className="text-white">{Math.round(item.confidence * 100)}%</span>
                </div>
                
                <div className="col-span-2">
                  <p className="font-medium text-white">{formatDocType(item.document_type)}</p>
                  <p className="text-sm text-slate-400">{item.filename}</p>
                </div>
                
                <div>
                  <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm bg-slate-700">
                    <Icon className="w-4 h-4" />
                    {item.category}
                  </span>
                </div>
                
                <div className="text-emerald-500 font-medium">
                  {item.calculated_co2e_kg ? formatEmissions(item.calculated_co2e_kg) : '-'}
                </div>
                
                <div className="text-slate-400 text-sm">
                  {new Date(item.uploaded_at).toLocaleDateString()}
                </div>
                
                <div className="flex gap-2">
                  {item.status === 'pending' ? (
                    hasPermission('canApprove') ? (
                      <>
                        {item.confidence >= 0.9 ? (
                          <button 
                            onClick={() => handleApprove(item.id)}
                            className="p-2 bg-emerald-500/20 text-emerald-500 rounded-lg hover:bg-emerald-500 hover:text-white transition-colors"
                            title="Approve"
                          >
                            <CheckCircle className="w-4 h-4" />
                          </button>
                        ) : (
                          <button 
                            onClick={() => setSelectedItem(item)}
                            className="p-2 bg-yellow-500/20 text-yellow-500 rounded-lg hover:bg-yellow-500 hover:text-white transition-colors"
                            title="Review & Edit"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                        )}
                        <button 
                          onClick={() => handleReject(item.id)}
                          className="p-2 bg-red-500/20 text-red-500 rounded-lg hover:bg-red-500 hover:text-white transition-colors"
                          title="Reject"
                        >
                          <XCircle className="w-4 h-4" />
                        </button>
                        <button 
                          onClick={() => handleDelete(item.id)}
                          className="p-2 bg-slate-700 text-slate-400 rounded-lg hover:bg-red-600 hover:text-white transition-colors"
                          title="Delete"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </>
                    ) : (
                      <button 
                        onClick={() => setSelectedItem(item)}
                        className="p-2 bg-slate-700 text-slate-400 rounded-lg hover:bg-slate-600 transition-colors"
                        title="View Details"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                    )
                  ) : (
                    <div className="flex items-center gap-2">
                      <span className={`px-3 py-1 rounded-full text-sm ${
                        item.status === 'approved' || item.status === 'auto_approved' 
                          ? 'bg-emerald-500/20 text-emerald-500' 
                          : 'bg-red-500/20 text-red-500'
                      }`}>
                        {item.status.replace('_', ' ')}
                      </span>
                      {hasPermission('canApprove') && (
                        <button 
                          onClick={() => handleDelete(item.id)}
                          className="p-1.5 text-slate-500 hover:text-red-500 transition-colors"
                          title="Delete"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )
          })
        )}
      </div>

      {/* Review Modal */}
      {selectedItem && (
        <ReviewModal 
          item={selectedItem} 
          onClose={() => setSelectedItem(null)}
          onApprove={() => {
            handleApprove(selectedItem.id)
            setSelectedItem(null)
          }}
          onReject={() => {
            handleReject(selectedItem.id)
            setSelectedItem(null)
          }}
          canApprove={hasPermission('canApprove')}
          canEdit={hasPermission('canEditExtracted')}
        />
      )}
    </div>
  )
}

function ReviewModal({ item, onClose, onApprove, onReject, canApprove, canEdit }: {
  item: ReviewItem
  onClose: () => void
  onApprove: () => void
  onReject: () => void
  canApprove: boolean
  canEdit: boolean
}) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <div 
        className="bg-slate-800 rounded-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden animate-slide-up"
        onClick={e => e.stopPropagation()}
      >
        <div className="grid grid-cols-2 h-full">
          {/* Left: Raw Text */}
          <div className="p-6 bg-slate-900 border-r border-slate-700 overflow-auto">
            <h3 className="text-lg font-semibold text-white mb-4">📄 Original Document</h3>
            <pre className="text-sm text-slate-300 whitespace-pre-wrap font-mono bg-slate-800 p-4 rounded-xl">
              {item.extracted_data?.raw_text || JSON.stringify(item.extracted_data, null, 2)}
            </pre>
          </div>

          {/* Right: Extracted Data */}
          <div className="p-6 overflow-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">📋 Extracted Data</h3>
              <button onClick={onClose} className="text-slate-400 hover:text-white">✕</button>
            </div>

            <div className="space-y-4">
              {Object.entries(item.extracted_data).map(([key, value]) => (
                key !== 'raw_text' && (
                  <div key={key}>
                    <label className="text-sm text-slate-400 block mb-1">
                      {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </label>
                    <input 
                      type="text"
                      defaultValue={String(value || '')}
                      disabled={!canEdit}
                      className={`w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-xl text-white focus:outline-none focus:border-emerald-500 ${!canEdit ? 'opacity-60 cursor-not-allowed' : ''}`}
                    />
                  </div>
                )
              ))}

              {item.calculated_co2e_kg && (
                <div className="p-4 bg-emerald-500/20 rounded-xl">
                  <p className="text-emerald-500 font-medium">
                    Calculated Emissions: {item.calculated_co2e_kg.toFixed(2)} kg CO₂e
                  </p>
                </div>
              )}

              {!canEdit && (
                <div className="p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-xl text-sm text-yellow-500">
                  <Lock className="w-4 h-4 inline mr-2" />
                  You don't have permission to edit extracted values
                </div>
              )}
            </div>

            <div className="flex gap-4 mt-6 pt-6 border-t border-slate-700">
              {canApprove ? (
                <>
                  <button 
                    onClick={onReject}
                    className="flex-1 py-3 bg-red-500 text-white rounded-xl hover:bg-red-600 transition-colors"
                  >
                    ❌ Reject
                  </button>
                  <button 
                    onClick={onApprove}
                    className="flex-1 py-3 bg-emerald-500 text-white rounded-xl hover:bg-emerald-600 transition-colors"
                  >
                    ✅ Approve
                  </button>
                </>
              ) : (
                <button 
                  onClick={onClose}
                  className="flex-1 py-3 bg-slate-700 text-white rounded-xl hover:bg-slate-600 transition-colors"
                >
                  Close
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
