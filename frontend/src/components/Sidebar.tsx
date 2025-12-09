import { Link, useLocation } from 'react-router-dom'
import { 
  LayoutDashboard, 
  FileSearch, 
  Upload, 
  BarChart3, 
  Settings, 
  ChevronLeft,
  Leaf,
  LogOut,
  Users,
  History,
  FileText,
  Shield
} from 'lucide-react'
import { useAuth, ROLE_PERMISSIONS } from '../context/AuthContext'

interface SidebarProps {
  open: boolean
  setOpen: (open: boolean) => void
}

interface MenuItem {
  icon: any
  label: string
  path: string
  requiredPermission?: keyof typeof ROLE_PERMISSIONS['admin']
  badge?: number
}

export default function Sidebar({ open, setOpen }: SidebarProps) {
  const location = useLocation()
  const { user, permissions, logout, hasPermission } = useAuth()

  // Define menu items with permission requirements
  const menuItems: MenuItem[] = [
    { icon: LayoutDashboard, label: 'Dashboard', path: '/' },
    { icon: FileSearch, label: 'Review Queue', path: '/review', requiredPermission: 'canApprove' },
    { icon: FileText, label: 'My Submissions', path: '/submissions' },
    { icon: Upload, label: 'Upload', path: '/upload' },
    { icon: BarChart3, label: 'Analytics', path: '/analytics', requiredPermission: 'canExportData' },
    { icon: History, label: 'Audit Log', path: '/audit', requiredPermission: 'canViewAuditLog' },
    { icon: Users, label: 'User Management', path: '/users', requiredPermission: 'canManageUsers' },
    { icon: Settings, label: 'Settings', path: '/settings', requiredPermission: 'canAccessSettings' },
  ]

  // Filter menu items based on permissions
  const visibleMenuItems = menuItems.filter(item => {
    if (!item.requiredPermission) return true
    return hasPermission(item.requiredPermission)
  })

  const roleColors = {
    admin: 'bg-red-500',
    supervisor: 'bg-yellow-500',
    user: 'bg-blue-500',
  }

  const roleIcons = {
    admin: '👑',
    supervisor: '🛡️',
    user: '👤',
  }

  return (
    <aside className={`fixed left-0 top-0 h-screen bg-slate-800 border-r border-slate-700 transition-all duration-300 z-50 ${open ? 'w-64' : 'w-20'}`}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-slate-700">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-emerald-500/20 rounded-xl flex items-center justify-center">
            <Leaf className="w-6 h-6 text-emerald-500" />
          </div>
          {open && (
            <div className="animate-fade-in">
              <h1 className="font-bold text-lg text-white">Emerald Flow</h1>
              <p className="text-xs text-slate-400">Sustainability Platform</p>
            </div>
          )}
        </div>
        <button 
          onClick={() => setOpen(!open)}
          className="p-2 rounded-lg hover:bg-slate-700 transition-colors"
        >
          <ChevronLeft className={`w-5 h-5 text-slate-400 transition-transform ${!open ? 'rotate-180' : ''}`} />
        </button>
      </div>

      {/* Navigation */}
      <nav className="p-4 space-y-2">
        {visibleMenuItems.map((item) => {
          const isActive = location.pathname === item.path
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${
                isActive 
                  ? 'bg-emerald-500/20 text-emerald-500' 
                  : 'text-slate-400 hover:bg-slate-700 hover:text-white'
              }`}
            >
              <item.icon className="w-5 h-5 flex-shrink-0" />
              {open && (
                <span className="animate-fade-in flex-1">{item.label}</span>
              )}
              {open && item.badge && (
                <span className="px-2 py-0.5 bg-red-500 text-white text-xs rounded-full">
                  {item.badge}
                </span>
              )}
            </Link>
          )
        })}
      </nav>

      {/* Permission Info (collapsed view) */}
      {!open && user && (
        <div className="absolute bottom-20 left-0 right-0 flex justify-center">
          <div className={`w-3 h-3 rounded-full ${roleColors[user.role]}`} title={permissions.label} />
        </div>
      )}

      {/* User Section */}
      <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-slate-700">
        {user ? (
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-full flex items-center justify-center text-lg ${
              user.role === 'admin' ? 'bg-red-500/20' :
              user.role === 'supervisor' ? 'bg-yellow-500/20' : 'bg-blue-500/20'
            }`}>
              {roleIcons[user.role]}
            </div>
            {open && (
              <div className="flex-1 animate-fade-in">
                <p className="text-sm font-medium text-white">{user.name}</p>
                <div className="flex items-center gap-2">
                  <span className={`inline-block w-2 h-2 rounded-full ${roleColors[user.role]}`} />
                  <p className="text-xs text-slate-400">{permissions.label}</p>
                </div>
              </div>
            )}
            {open && (
              <button 
                onClick={logout}
                className="p-2 rounded-lg hover:bg-slate-700 transition-colors"
                title="Logout"
              >
                <LogOut className="w-4 h-4 text-slate-400" />
              </button>
            )}
          </div>
        ) : (
          <Link 
            to="/login"
            className="flex items-center justify-center gap-2 px-4 py-2 bg-emerald-500 text-white rounded-xl hover:bg-emerald-600 transition-colors"
          >
            <Shield className="w-4 h-4" />
            {open && <span>Login</span>}
          </Link>
        )}
      </div>
    </aside>
  )
}
