import { Bell, Search, HelpCircle } from 'lucide-react'
import RoleSwitcher from './RoleSwitcher'
import { useAuth } from '../context/AuthContext'

export default function TopBar() {
  const { user, permissions } = useAuth()

  return (
    <div className="sticky top-0 z-40 bg-slate-900/80 backdrop-blur-lg border-b border-slate-800">
      <div className="flex items-center justify-between px-6 py-3">
        {/* Search */}
        <div className="flex items-center gap-4 flex-1 max-w-xl">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search documents, reports..."
              className="w-full pl-10 pr-4 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white placeholder-slate-400 focus:outline-none focus:border-emerald-500"
            />
          </div>
        </div>

        {/* Right Section */}
        <div className="flex items-center gap-4">
          {/* Permission indicator */}
          {user && (
            <div className="hidden md:flex items-center gap-2 text-xs text-slate-400">
              {permissions.canApprove && (
                <span className="px-2 py-1 bg-emerald-500/20 text-emerald-500 rounded">
                  ✓ Can Approve
                </span>
              )}
              {permissions.canAccessSettings && (
                <span className="px-2 py-1 bg-purple-500/20 text-purple-500 rounded">
                  ⚙️ Admin
                </span>
              )}
              {!permissions.canApprove && (
                <span className="px-2 py-1 bg-slate-700 text-slate-400 rounded">
                  👁️ View Only
                </span>
              )}
            </div>
          )}

          {/* Role Switcher (Demo) */}
          <RoleSwitcher />

          {/* Notifications */}
          <button className="relative p-2 hover:bg-slate-800 rounded-xl transition-colors">
            <Bell className="w-5 h-5 text-slate-400" />
            <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
          </button>

          {/* Help */}
          <button className="p-2 hover:bg-slate-800 rounded-xl transition-colors">
            <HelpCircle className="w-5 h-5 text-slate-400" />
          </button>
        </div>
      </div>
    </div>
  )
}

