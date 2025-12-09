import { useEffect, useState } from 'react'
import { 
  FileText, 
  Clock, 
  CheckCircle, 
  XCircle,
  Eye,
  Plus
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'

interface Submission {
  id: string
  document_type: string
  filename: string
  status: 'pending' | 'approved' | 'rejected'
  submitted_at: string
  calculated_co2e_kg: number | null
  reviewer?: string
  reviewed_at?: string
}

export default function Submissions() {
  const { user } = useAuth()
  const [submissions, setSubmissions] = useState<Submission[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Simulated data - in real app would filter by user
    setTimeout(() => {
      setSubmissions([
        {
          id: '1',
          document_type: 'utility_bill',
          filename: 'jan_2024_electric.pdf',
          status: 'approved',
          submitted_at: '2024-01-15T10:30:00Z',
          calculated_co2e_kg: 245.5,
          reviewer: 'Michael Torres',
          reviewed_at: '2024-01-15T14:20:00Z'
        },
        {
          id: '2',
          document_type: 'flight_receipt',
          filename: 'NYC_trip_receipt.pdf',
          status: 'pending',
          submitted_at: '2024-01-20T09:15:00Z',
          calculated_co2e_kg: 890.2,
        },
        {
          id: '3',
          document_type: 'fuel_receipt',
          filename: 'company_car_jan.jpg',
          status: 'rejected',
          submitted_at: '2024-01-18T16:45:00Z',
          calculated_co2e_kg: null,
          reviewer: 'Michael Torres',
          reviewed_at: '2024-01-19T11:30:00Z'
        },
      ])
      setLoading(false)
    }, 500)
  }, [])

  const statusConfig = {
    pending: { icon: Clock, color: 'text-yellow-500 bg-yellow-500/20', label: 'Pending Review' },
    approved: { icon: CheckCircle, color: 'text-emerald-500 bg-emerald-500/20', label: 'Approved' },
    rejected: { icon: XCircle, color: 'text-red-500 bg-red-500/20', label: 'Rejected' },
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">My Submissions</h1>
          <p className="text-slate-400">Track your submitted documents</p>
        </div>
        <a 
          href="/upload"
          className="flex items-center gap-2 px-4 py-2 bg-emerald-500 text-white rounded-xl hover:bg-emerald-600 transition-colors"
        >
          <Plus className="w-5 h-5" />
          New Submission
        </a>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard
          label="Pending"
          value={submissions.filter(s => s.status === 'pending').length}
          icon={<Clock className="w-5 h-5" />}
          color="yellow"
        />
        <StatCard
          label="Approved"
          value={submissions.filter(s => s.status === 'approved').length}
          icon={<CheckCircle className="w-5 h-5" />}
          color="emerald"
        />
        <StatCard
          label="Rejected"
          value={submissions.filter(s => s.status === 'rejected').length}
          icon={<XCircle className="w-5 h-5" />}
          color="red"
        />
      </div>

      {/* Submissions List */}
      <div className="bg-slate-800 rounded-2xl border border-slate-700 overflow-hidden">
        <div className="p-6 border-b border-slate-700">
          <h3 className="text-lg font-semibold text-white">Recent Submissions</h3>
        </div>

        {loading ? (
          <div className="p-8 text-center">
            <div className="animate-spin w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full mx-auto" />
          </div>
        ) : submissions.length === 0 ? (
          <div className="p-8 text-center text-slate-400">
            <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>No submissions yet</p>
            <a href="/upload" className="text-emerald-500 hover:underline">Upload your first document</a>
          </div>
        ) : (
          <div className="divide-y divide-slate-700">
            {submissions.map((sub) => {
              const status = statusConfig[sub.status]
              const StatusIcon = status.icon
              
              return (
                <div key={sub.id} className="p-4 hover:bg-slate-700/30 transition-colors">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 bg-slate-700 rounded-xl flex items-center justify-center">
                      <FileText className="w-5 h-5 text-slate-400" />
                    </div>
                    
                    <div className="flex-1">
                      <p className="font-medium text-white">{sub.filename}</p>
                      <p className="text-sm text-slate-400">
                        {sub.document_type.replace(/_/g, ' ')} • Submitted {new Date(sub.submitted_at).toLocaleDateString()}
                      </p>
                    </div>

                    {sub.calculated_co2e_kg && (
                      <div className="text-right">
                        <p className="text-emerald-500 font-medium">
                          {sub.calculated_co2e_kg.toFixed(0)} kg
                        </p>
                        <p className="text-xs text-slate-400">CO₂e</p>
                      </div>
                    )}

                    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg ${status.color}`}>
                      <StatusIcon className="w-4 h-4" />
                      <span className="text-sm font-medium">{status.label}</span>
                    </div>

                    <button className="p-2 hover:bg-slate-700 rounded-lg transition-colors">
                      <Eye className="w-4 h-4 text-slate-400" />
                    </button>
                  </div>

                  {sub.reviewer && (
                    <div className="mt-2 ml-14 text-xs text-slate-500">
                      Reviewed by {sub.reviewer} on {new Date(sub.reviewed_at!).toLocaleDateString()}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

function StatCard({ label, value, icon, color }: {
  label: string
  value: number
  icon: React.ReactNode
  color: 'yellow' | 'emerald' | 'red'
}) {
  const colors = {
    yellow: 'bg-yellow-500/20 text-yellow-500',
    emerald: 'bg-emerald-500/20 text-emerald-500',
    red: 'bg-red-500/20 text-red-500',
  }

  return (
    <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
      <div className="flex items-center gap-3">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${colors[color]}`}>
          {icon}
        </div>
        <div>
          <p className="text-2xl font-bold text-white">{value}</p>
          <p className="text-sm text-slate-400">{label}</p>
        </div>
      </div>
    </div>
  )
}

