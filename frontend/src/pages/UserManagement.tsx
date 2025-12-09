import { useState } from 'react'
import { 
  Users, 
  Plus,
  Search,
  MoreVertical,
  Shield,
  Mail,
  Building,
  Check,
  X
} from 'lucide-react'

interface UserData {
  id: string
  name: string
  email: string
  role: 'admin' | 'supervisor' | 'user'
  department: string
  status: 'active' | 'inactive' | 'pending'
  lastActive: string
  documentsSubmitted: number
}

const MOCK_USERS: UserData[] = [
  {
    id: '1',
    name: 'Sarah Chen',
    email: 'sarah.chen@company.com',
    role: 'admin',
    department: 'IT Administration',
    status: 'active',
    lastActive: '2024-01-20T14:30:00Z',
    documentsSubmitted: 0
  },
  {
    id: '2',
    name: 'Michael Torres',
    email: 'michael.torres@company.com',
    role: 'supervisor',
    department: 'Sustainability',
    status: 'active',
    lastActive: '2024-01-20T12:15:00Z',
    documentsSubmitted: 12
  },
  {
    id: '3',
    name: 'Emily Johnson',
    email: 'emily.johnson@company.com',
    role: 'user',
    department: 'Operations',
    status: 'active',
    lastActive: '2024-01-20T10:00:00Z',
    documentsSubmitted: 45
  },
  {
    id: '4',
    name: 'David Kim',
    email: 'david.kim@company.com',
    role: 'user',
    department: 'Finance',
    status: 'active',
    lastActive: '2024-01-19T16:45:00Z',
    documentsSubmitted: 23
  },
  {
    id: '5',
    name: 'Jessica Martinez',
    email: 'jessica.martinez@company.com',
    role: 'supervisor',
    department: 'Facilities',
    status: 'pending',
    lastActive: '',
    documentsSubmitted: 0
  },
]

export default function UserManagement() {
  const [users, setUsers] = useState<UserData[]>(MOCK_USERS)
  const [search, setSearch] = useState('')
  const [showAddModal, setShowAddModal] = useState(false)

  const roleColors = {
    admin: 'bg-red-500/20 text-red-500 border-red-500/50',
    supervisor: 'bg-yellow-500/20 text-yellow-500 border-yellow-500/50',
    user: 'bg-blue-500/20 text-blue-500 border-blue-500/50',
  }

  const roleIcons = {
    admin: '👑',
    supervisor: '🛡️',
    user: '👤',
  }

  const statusColors = {
    active: 'bg-emerald-500',
    inactive: 'bg-slate-500',
    pending: 'bg-yellow-500',
  }

  const filteredUsers = users.filter(u => 
    u.name.toLowerCase().includes(search.toLowerCase()) ||
    u.email.toLowerCase().includes(search.toLowerCase()) ||
    u.department.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">User Management</h1>
          <p className="text-slate-400">Manage users and their permissions</p>
        </div>
        <button 
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-emerald-500 text-white rounded-xl hover:bg-emerald-600 transition-colors"
        >
          <Plus className="w-5 h-5" />
          Add User
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-slate-700">
              <Users className="w-5 h-5 text-slate-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{users.length}</p>
              <p className="text-sm text-slate-400">Total Users</p>
            </div>
          </div>
        </div>
        <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-red-500/20">
              <span className="text-lg">👑</span>
            </div>
            <div>
              <p className="text-2xl font-bold text-white">
                {users.filter(u => u.role === 'admin').length}
              </p>
              <p className="text-sm text-slate-400">Admins</p>
            </div>
          </div>
        </div>
        <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-yellow-500/20">
              <span className="text-lg">🛡️</span>
            </div>
            <div>
              <p className="text-2xl font-bold text-white">
                {users.filter(u => u.role === 'supervisor').length}
              </p>
              <p className="text-sm text-slate-400">Supervisors</p>
            </div>
          </div>
        </div>
        <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-blue-500/20">
              <span className="text-lg">👤</span>
            </div>
            <div>
              <p className="text-2xl font-bold text-white">
                {users.filter(u => u.role === 'user').length}
              </p>
              <p className="text-sm text-slate-400">Users</p>
            </div>
          </div>
        </div>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
        <input
          type="text"
          placeholder="Search users..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-10 pr-4 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white placeholder-slate-400 focus:outline-none focus:border-emerald-500"
        />
      </div>

      {/* Users Table */}
      <div className="bg-slate-800 rounded-2xl border border-slate-700 overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-700/50">
            <tr>
              <th className="px-6 py-3 text-left text-sm font-medium text-slate-400 uppercase">User</th>
              <th className="px-6 py-3 text-left text-sm font-medium text-slate-400 uppercase">Role</th>
              <th className="px-6 py-3 text-left text-sm font-medium text-slate-400 uppercase">Department</th>
              <th className="px-6 py-3 text-left text-sm font-medium text-slate-400 uppercase">Status</th>
              <th className="px-6 py-3 text-left text-sm font-medium text-slate-400 uppercase">Activity</th>
              <th className="px-6 py-3 text-left text-sm font-medium text-slate-400 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700">
            {filteredUsers.map((user) => (
              <tr key={user.id} className="hover:bg-slate-700/30 transition-colors">
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-slate-700 rounded-full flex items-center justify-center">
                      <span className="text-sm font-medium text-white">
                        {user.name.split(' ').map(n => n[0]).join('')}
                      </span>
                    </div>
                    <div>
                      <p className="font-medium text-white">{user.name}</p>
                      <p className="text-sm text-slate-400">{user.email}</p>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm border ${roleColors[user.role]}`}>
                    <span>{roleIcons[user.role]}</span>
                    <span className="capitalize">{user.role}</span>
                  </span>
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-2 text-slate-300">
                    <Building className="w-4 h-4 text-slate-500" />
                    {user.department}
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${statusColors[user.status]}`} />
                    <span className="text-slate-300 capitalize">{user.status}</span>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="text-sm">
                    <p className="text-slate-300">{user.documentsSubmitted} docs</p>
                    {user.lastActive && (
                      <p className="text-slate-500">
                        Last: {new Date(user.lastActive).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-2">
                    <button className="p-2 hover:bg-slate-700 rounded-lg transition-colors" title="Edit">
                      <Shield className="w-4 h-4 text-slate-400" />
                    </button>
                    <button className="p-2 hover:bg-slate-700 rounded-lg transition-colors" title="Email">
                      <Mail className="w-4 h-4 text-slate-400" />
                    </button>
                    <button className="p-2 hover:bg-slate-700 rounded-lg transition-colors" title="More">
                      <MoreVertical className="w-4 h-4 text-slate-400" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Role Permissions Legend */}
      <div className="bg-slate-800 rounded-2xl p-6 border border-slate-700">
        <h3 className="text-lg font-semibold text-white mb-4">Role Permissions</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <RoleCard
            role="admin"
            icon="👑"
            label="Administrator"
            permissions={['Full system access', 'User management', 'Settings configuration', 'All approvals', 'API access']}
          />
          <RoleCard
            role="supervisor"
            icon="🛡️"
            label="Supervisor"
            permissions={['Review & approve documents', 'Bulk operations', 'View all departments', 'Export data', 'Audit log access']}
          />
          <RoleCard
            role="user"
            icon="👤"
            label="User"
            permissions={['Upload documents', 'View own submissions', 'Track status', 'Basic dashboard']}
          />
        </div>
      </div>
    </div>
  )
}

function RoleCard({ role, icon, label, permissions }: {
  role: 'admin' | 'supervisor' | 'user'
  icon: string
  label: string
  permissions: string[]
}) {
  const colors = {
    admin: 'border-red-500/30 bg-red-500/5',
    supervisor: 'border-yellow-500/30 bg-yellow-500/5',
    user: 'border-blue-500/30 bg-blue-500/5',
  }

  return (
    <div className={`p-4 rounded-xl border ${colors[role]}`}>
      <div className="flex items-center gap-2 mb-3">
        <span className="text-2xl">{icon}</span>
        <span className="font-medium text-white">{label}</span>
      </div>
      <ul className="space-y-2">
        {permissions.map((perm, i) => (
          <li key={i} className="flex items-center gap-2 text-sm text-slate-400">
            <Check className="w-4 h-4 text-emerald-500" />
            {perm}
          </li>
        ))}
      </ul>
    </div>
  )
}

