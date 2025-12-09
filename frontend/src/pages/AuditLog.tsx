import { useEffect, useState } from 'react'
import { 
  History, 
  Filter,
  Download,
  CheckCircle,
  XCircle,
  Upload,
  Edit,
  Trash,
  User,
  Settings
} from 'lucide-react'

interface AuditEntry {
  id: string
  action: string
  user: string
  user_role: 'admin' | 'supervisor' | 'user'
  target: string
  details: string
  timestamp: string
  ip_address: string
}

const actionIcons: Record<string, any> = {
  approve: CheckCircle,
  reject: XCircle,
  upload: Upload,
  edit: Edit,
  delete: Trash,
  login: User,
  settings: Settings,
}

const actionColors: Record<string, string> = {
  approve: 'text-emerald-500 bg-emerald-500/20',
  reject: 'text-red-500 bg-red-500/20',
  upload: 'text-blue-500 bg-blue-500/20',
  edit: 'text-yellow-500 bg-yellow-500/20',
  delete: 'text-red-500 bg-red-500/20',
  login: 'text-purple-500 bg-purple-500/20',
  settings: 'text-slate-400 bg-slate-500/20',
}

export default function AuditLog() {
  const [entries, setEntries] = useState<AuditEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState({ action: '', user: '' })

  useEffect(() => {
    // Simulated audit log data
    setTimeout(() => {
      setEntries([
        {
          id: '1',
          action: 'approve',
          user: 'Michael Torres',
          user_role: 'supervisor',
          target: 'utility_bill_jan_2024.pdf',
          details: 'Auto-approved (95% confidence)',
          timestamp: '2024-01-20T14:30:00Z',
          ip_address: '192.168.1.100'
        },
        {
          id: '2',
          action: 'reject',
          user: 'Sarah Chen',
          user_role: 'admin',
          target: 'unclear_receipt.jpg',
          details: 'Rejected: Image quality too low for extraction',
          timestamp: '2024-01-20T13:45:00Z',
          ip_address: '192.168.1.101'
        },
        {
          id: '3',
          action: 'upload',
          user: 'Emily Johnson',
          user_role: 'user',
          target: 'flight_receipt_NYC.pdf',
          details: 'New document uploaded via web interface',
          timestamp: '2024-01-20T10:15:00Z',
          ip_address: '192.168.1.105'
        },
        {
          id: '4',
          action: 'edit',
          user: 'Michael Torres',
          user_role: 'supervisor',
          target: 'utility_bill_dec_2023.pdf',
          details: 'Modified extracted value: kwh 500 → 520',
          timestamp: '2024-01-19T16:20:00Z',
          ip_address: '192.168.1.100'
        },
        {
          id: '5',
          action: 'settings',
          user: 'Sarah Chen',
          user_role: 'admin',
          target: 'Auto-approve threshold',
          details: 'Changed from 90% to 95%',
          timestamp: '2024-01-19T09:00:00Z',
          ip_address: '192.168.1.101'
        },
        {
          id: '6',
          action: 'login',
          user: 'Sarah Chen',
          user_role: 'admin',
          target: 'System',
          details: 'Successful login via SSO',
          timestamp: '2024-01-19T08:55:00Z',
          ip_address: '192.168.1.101'
        },
      ])
      setLoading(false)
    }, 500)
  }, [])

  const roleColors = {
    admin: 'text-red-500',
    supervisor: 'text-yellow-500',
    user: 'text-blue-500',
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Audit Log</h1>
          <p className="text-slate-400">Track all system activity and changes</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-slate-700 text-white rounded-xl hover:bg-slate-600 transition-colors">
          <Download className="w-5 h-5" />
          Export Log
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4">
        <select
          value={filter.action}
          onChange={(e) => setFilter({ ...filter, action: e.target.value })}
          className="px-4 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white focus:outline-none focus:border-emerald-500"
        >
          <option value="">All Actions</option>
          <option value="approve">✅ Approvals</option>
          <option value="reject">❌ Rejections</option>
          <option value="upload">📤 Uploads</option>
          <option value="edit">✏️ Edits</option>
          <option value="settings">⚙️ Settings</option>
          <option value="login">🔐 Logins</option>
        </select>

        <input
          type="text"
          placeholder="Filter by user..."
          value={filter.user}
          onChange={(e) => setFilter({ ...filter, user: e.target.value })}
          className="px-4 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white placeholder-slate-400 focus:outline-none focus:border-emerald-500"
        />

        <input
          type="date"
          className="px-4 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white focus:outline-none focus:border-emerald-500"
        />
      </div>

      {/* Audit Log Table */}
      <div className="bg-slate-800 rounded-2xl border border-slate-700 overflow-hidden">
        {loading ? (
          <div className="p-8 text-center">
            <div className="animate-spin w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full mx-auto" />
          </div>
        ) : (
          <div className="divide-y divide-slate-700">
            {entries.map((entry) => {
              const Icon = actionIcons[entry.action] || History
              const colorClass = actionColors[entry.action] || 'text-slate-400 bg-slate-500/20'
              
              return (
                <div key={entry.id} className="p-4 hover:bg-slate-700/30 transition-colors">
                  <div className="flex items-start gap-4">
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${colorClass}`}>
                      <Icon className="w-5 h-5" />
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={`font-medium ${roleColors[entry.user_role]}`}>
                          {entry.user}
                        </span>
                        <span className="text-slate-400">•</span>
                        <span className="text-white capitalize">{entry.action}</span>
                        <span className="text-slate-400">•</span>
                        <span className="text-slate-300 truncate">{entry.target}</span>
                      </div>
                      <p className="text-sm text-slate-400 mt-1">{entry.details}</p>
                    </div>

                    <div className="text-right text-sm">
                      <p className="text-slate-300">
                        {new Date(entry.timestamp).toLocaleTimeString()}
                      </p>
                      <p className="text-slate-500">
                        {new Date(entry.timestamp).toLocaleDateString()}
                      </p>
                      <p className="text-slate-600 text-xs mt-1">
                        {entry.ip_address}
                      </p>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <p className="text-slate-400 text-sm">Showing 6 of 248 entries</p>
        <div className="flex gap-2">
          <button className="px-4 py-2 bg-slate-800 text-slate-400 rounded-xl hover:bg-slate-700 transition-colors">
            Previous
          </button>
          <button className="px-4 py-2 bg-emerald-500 text-white rounded-xl hover:bg-emerald-600 transition-colors">
            Next
          </button>
        </div>
      </div>
    </div>
  )
}

