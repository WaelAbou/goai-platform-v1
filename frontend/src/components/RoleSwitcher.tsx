import { useState } from 'react'
import { useAuth, UserRole, ROLE_PERMISSIONS, DEMO_USERS } from '../context/AuthContext'
import { Shield, ChevronDown, Check } from 'lucide-react'

export default function RoleSwitcher() {
  const { user, switchRole } = useAuth()
  const [open, setOpen] = useState(false)

  if (!user) return null

  const roles: UserRole[] = ['admin', 'supervisor', 'user']

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

  return (
    <div className="relative">
      {/* Demo Mode Banner */}
      <button
        onClick={() => setOpen(!open)}
        className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-sm font-medium transition-all ${roleColors[user.role]}`}
      >
        <span>{roleIcons[user.role]}</span>
        <span>{ROLE_PERMISSIONS[user.role].label}</span>
        <ChevronDown className={`w-4 h-4 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown */}
      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full mt-2 w-72 bg-slate-800 border border-slate-700 rounded-xl shadow-xl z-50 overflow-hidden animate-slide-up">
            <div className="p-3 border-b border-slate-700 bg-slate-700/50">
              <p className="text-xs text-slate-400 uppercase tracking-wider">🎭 Demo Mode - Switch Role</p>
            </div>
            
            {roles.map((role) => {
              const isActive = user.role === role
              const demoUser = DEMO_USERS[role]
              const perms = ROLE_PERMISSIONS[role]
              
              return (
                <button
                  key={role}
                  onClick={() => {
                    switchRole(role)
                    setOpen(false)
                  }}
                  className={`w-full p-4 text-left hover:bg-slate-700/50 transition-colors ${isActive ? 'bg-slate-700/30' : ''}`}
                >
                  <div className="flex items-start gap-3">
                    <span className="text-2xl">{roleIcons[role]}</span>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-white">{demoUser.name}</span>
                        {isActive && <Check className="w-4 h-4 text-emerald-500" />}
                      </div>
                      <span className={`inline-block mt-1 px-2 py-0.5 rounded text-xs ${roleColors[role]}`}>
                        {perms.label}
                      </span>
                      <p className="text-xs text-slate-400 mt-1">{demoUser.department}</p>
                      
                      {/* Permission highlights */}
                      <div className="flex flex-wrap gap-1 mt-2">
                        {perms.canApprove && <PermBadge>Approve</PermBadge>}
                        {perms.canBulkApprove && <PermBadge>Bulk</PermBadge>}
                        {perms.canAccessSettings && <PermBadge>Settings</PermBadge>}
                        {perms.canManageUsers && <PermBadge>Users</PermBadge>}
                        {!perms.canApprove && <PermBadge disabled>View Only</PermBadge>}
                      </div>
                    </div>
                  </div>
                </button>
              )
            })}
            
            <div className="p-3 border-t border-slate-700 bg-slate-900/50">
              <p className="text-xs text-slate-500 text-center">
                Switch roles to preview different permission levels
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

function PermBadge({ children, disabled }: { children: React.ReactNode; disabled?: boolean }) {
  return (
    <span className={`px-1.5 py-0.5 rounded text-[10px] ${
      disabled ? 'bg-slate-600 text-slate-400' : 'bg-emerald-500/20 text-emerald-500'
    }`}>
      {children}
    </span>
  )
}

