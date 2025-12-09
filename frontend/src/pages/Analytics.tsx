import { useEffect, useState } from 'react'
import { 
  TrendingUp, 
  TrendingDown, 
  Download,
  Calendar,
  Building,
  Leaf
} from 'lucide-react'
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, PieChart, Pie, Cell
} from 'recharts'

const COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6']

export default function Analytics() {
  const [stats, setStats] = useState<any>(null)
  const [dateRange, setDateRange] = useState('30d')

  useEffect(() => {
    fetch('/api/v1/review/stats')
      .then(res => res.json())
      .then(setStats)
  }, [])

  const categoryData = stats ? Object.entries(stats.by_category).map(([name, value]) => ({
    name: name.charAt(0).toUpperCase() + name.slice(1),
    value: value as number
  })) : []

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Analytics</h1>
          <p className="text-slate-400">Track your sustainability performance</p>
        </div>
        <div className="flex items-center gap-4">
          <select
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
            className="px-4 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white focus:outline-none focus:border-emerald-500"
          >
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
            <option value="90d">Last 90 days</option>
            <option value="1y">Last year</option>
          </select>
          <button className="flex items-center gap-2 px-4 py-2 bg-emerald-500 text-white rounded-xl hover:bg-emerald-600 transition-colors">
            <Download className="w-5 h-5" />
            Export Report
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <SummaryCard
          label="Total Emissions"
          value={`${stats?.emissions?.approved_tonnes?.toFixed(1) || 0}t`}
          subtext="CO₂e tracked"
          icon={<Leaf className="w-6 h-6" />}
          trend={-12}
          color="emerald"
        />
        <SummaryCard
          label="Documents Processed"
          value={stats?.queue_summary?.total || 0}
          subtext="This period"
          icon={<TrendingUp className="w-6 h-6" />}
          trend={24}
          color="blue"
        />
        <SummaryCard
          label="Auto-Approve Rate"
          value={`${stats?.activity?.auto_approve_rate || 0}%`}
          subtext="High confidence"
          icon={<TrendingUp className="w-6 h-6" />}
          trend={5}
          color="purple"
        />
        <SummaryCard
          label="Avg Processing"
          value="3.2s"
          subtext="Per document"
          icon={<TrendingDown className="w-6 h-6" />}
          trend={-18}
          color="yellow"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Emissions Over Time */}
        <div className="bg-slate-800 rounded-2xl p-6 border border-slate-700">
          <h3 className="text-lg font-semibold text-white mb-4">Emissions Over Time</h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={stats?.activity?.daily_uploads || []}>
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
          <h3 className="text-lg font-semibold text-white mb-4">Emissions by Category</h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={categoryData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={false} />
                <XAxis type="number" stroke="#94a3b8" fontSize={12} />
                <YAxis dataKey="name" type="category" stroke="#94a3b8" fontSize={12} width={80} />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#1e293b', 
                    border: '1px solid #475569',
                    borderRadius: '8px'
                  }}
                />
                <Bar dataKey="value" fill="#10b981" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Breakdown Table */}
      <div className="bg-slate-800 rounded-2xl border border-slate-700 overflow-hidden">
        <div className="p-6 border-b border-slate-700">
          <h3 className="text-lg font-semibold text-white">Detailed Breakdown</h3>
        </div>
        <table className="w-full">
          <thead className="bg-slate-700/50">
            <tr>
              <th className="px-6 py-3 text-left text-sm font-medium text-slate-400 uppercase">Category</th>
              <th className="px-6 py-3 text-left text-sm font-medium text-slate-400 uppercase">Documents</th>
              <th className="px-6 py-3 text-left text-sm font-medium text-slate-400 uppercase">CO₂e (kg)</th>
              <th className="px-6 py-3 text-left text-sm font-medium text-slate-400 uppercase">% of Total</th>
              <th className="px-6 py-3 text-left text-sm font-medium text-slate-400 uppercase">Trend</th>
            </tr>
          </thead>
          <tbody>
            {categoryData.map((cat, idx) => (
              <tr key={cat.name} className="border-t border-slate-700">
                <td className="px-6 py-4 text-white font-medium">{cat.name}</td>
                <td className="px-6 py-4 text-slate-300">{cat.value}</td>
                <td className="px-6 py-4 text-slate-300">
                  {(cat.value * 150).toLocaleString()}
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-2">
                    <div className="w-24 h-2 bg-slate-700 rounded-full overflow-hidden">
                      <div 
                        className="h-full rounded-full"
                        style={{ 
                          width: `${(cat.value / categoryData.reduce((a, b) => a + b.value, 0)) * 100}%`,
                          backgroundColor: COLORS[idx % COLORS.length]
                        }}
                      />
                    </div>
                    <span className="text-slate-400 text-sm">
                      {Math.round((cat.value / categoryData.reduce((a, b) => a + b.value, 0)) * 100)}%
                    </span>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <span className={`flex items-center gap-1 ${idx % 2 === 0 ? 'text-emerald-500' : 'text-red-500'}`}>
                    {idx % 2 === 0 ? <TrendingDown className="w-4 h-4" /> : <TrendingUp className="w-4 h-4" />}
                    {Math.abs(5 + idx * 3)}%
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function SummaryCard({ label, value, subtext, icon, trend, color }: {
  label: string
  value: string | number
  subtext: string
  icon: React.ReactNode
  trend: number
  color: 'emerald' | 'blue' | 'yellow' | 'purple'
}) {
  const colorClasses = {
    emerald: 'bg-emerald-500/20 text-emerald-500',
    blue: 'bg-blue-500/20 text-blue-500',
    yellow: 'bg-yellow-500/20 text-yellow-500',
    purple: 'bg-purple-500/20 text-purple-500',
  }

  return (
    <div className="bg-slate-800 rounded-2xl p-6 border border-slate-700">
      <div className="flex items-center justify-between mb-4">
        <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${colorClasses[color]}`}>
          {icon}
        </div>
        <span className={`flex items-center gap-1 text-sm ${trend > 0 ? 'text-emerald-500' : 'text-red-500'}`}>
          {trend > 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
          {Math.abs(trend)}%
        </span>
      </div>
      <p className="text-3xl font-bold text-white">{value}</p>
      <p className="text-slate-400 text-sm">{subtext}</p>
    </div>
  )
}

