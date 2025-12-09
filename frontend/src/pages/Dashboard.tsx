import { useEffect, useState } from 'react'
import { 
  FileText, 
  CheckCircle, 
  Leaf, 
  Zap,
  TrendingUp,
  Clock,
  AlertCircle
} from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'

interface Stats {
  queue_summary: {
    pending: number
    approved: number
    auto_approved: number
    rejected: number
    total: number
  }
  by_category: Record<string, number>
  emissions: {
    approved_kg: number
    approved_tonnes: number
  }
  activity: {
    daily_uploads: Array<{ date: string; count: number }>
    auto_approve_rate: number
  }
}

const COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6']

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/v1/review/stats')
      .then(res => res.json())
      .then(data => {
        setStats(data)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full" />
      </div>
    )
  }

  const categoryData = stats ? Object.entries(stats.by_category).map(([name, value]) => ({
    name: name.charAt(0).toUpperCase() + name.slice(1),
    value
  })) : []

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-slate-400">Welcome back! Here's your sustainability overview.</p>
        </div>
        <div className="flex items-center gap-2 px-4 py-2 bg-emerald-500/20 rounded-full">
          <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
          <span className="text-emerald-500 text-sm font-medium">System Online</span>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatsCard
          icon={<Clock className="w-6 h-6" />}
          label="Pending Review"
          value={stats?.queue_summary.pending || 0}
          color="yellow"
        />
        <StatsCard
          icon={<CheckCircle className="w-6 h-6" />}
          label="Approved Today"
          value={(stats?.queue_summary.approved || 0) + (stats?.queue_summary.auto_approved || 0)}
          color="emerald"
        />
        <StatsCard
          icon={<Leaf className="w-6 h-6" />}
          label="CO₂e Tracked"
          value={`${stats?.emissions.approved_tonnes.toFixed(1) || 0}t`}
          color="blue"
        />
        <StatsCard
          icon={<Zap className="w-6 h-6" />}
          label="Auto-Approve Rate"
          value={`${stats?.activity.auto_approve_rate || 0}%`}
          color="purple"
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Activity Chart */}
        <div className="lg:col-span-2 bg-slate-800 rounded-2xl p-6 border border-slate-700">
          <h3 className="text-lg font-semibold text-white mb-4">Document Activity</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={stats?.activity.daily_uploads || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="date" stroke="#94a3b8" fontSize={12} />
                <YAxis stroke="#94a3b8" fontSize={12} />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#1e293b', 
                    border: '1px solid #475569',
                    borderRadius: '8px'
                  }}
                />
                <Line 
                  type="monotone" 
                  dataKey="count" 
                  stroke="#10b981" 
                  strokeWidth={2}
                  dot={{ fill: '#10b981' }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Category Breakdown */}
        <div className="bg-slate-800 rounded-2xl p-6 border border-slate-700">
          <h3 className="text-lg font-semibold text-white mb-4">By Category</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={categoryData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {categoryData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#1e293b', 
                    border: '1px solid #475569',
                    borderRadius: '8px'
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex flex-wrap gap-2 mt-4">
            {categoryData.map((item, index) => (
              <div key={item.name} className="flex items-center gap-2 text-sm">
                <span 
                  className="w-3 h-3 rounded-full" 
                  style={{ backgroundColor: COLORS[index % COLORS.length] }}
                />
                <span className="text-slate-400">{item.name}: {item.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-slate-800 rounded-2xl p-6 border border-slate-700">
        <h3 className="text-lg font-semibold text-white mb-4">Quick Actions</h3>
        <div className="flex flex-wrap gap-4">
          <a href="/upload" className="flex items-center gap-2 px-6 py-3 bg-emerald-500 text-white rounded-xl hover:bg-emerald-600 transition-colors">
            <FileText className="w-5 h-5" />
            Upload Document
          </a>
          <a href="/review" className="flex items-center gap-2 px-6 py-3 bg-slate-700 text-white rounded-xl hover:bg-slate-600 transition-colors">
            <CheckCircle className="w-5 h-5" />
            Review Queue ({stats?.queue_summary.pending || 0})
          </a>
          <button className="flex items-center gap-2 px-6 py-3 bg-slate-700 text-white rounded-xl hover:bg-slate-600 transition-colors">
            <TrendingUp className="w-5 h-5" />
            Generate Report
          </button>
        </div>
      </div>
    </div>
  )
}

function StatsCard({ icon, label, value, color }: { 
  icon: React.ReactNode
  label: string
  value: string | number
  color: 'emerald' | 'blue' | 'yellow' | 'purple'
}) {
  const colorClasses = {
    emerald: 'bg-emerald-500/20 text-emerald-500',
    blue: 'bg-blue-500/20 text-blue-500',
    yellow: 'bg-yellow-500/20 text-yellow-500',
    purple: 'bg-purple-500/20 text-purple-500',
  }

  return (
    <div className="bg-slate-800 rounded-2xl p-6 border border-slate-700 animate-slide-up">
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${colorClasses[color]}`}>
        {icon}
      </div>
      <div className="mt-4">
        <p className="text-3xl font-bold text-white">{value}</p>
        <p className="text-slate-400 text-sm">{label}</p>
      </div>
    </div>
  )
}

