import { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth, ROLE_PERMISSIONS } from '../context/AuthContext'
import { ShieldX } from 'lucide-react'

interface ProtectedRouteProps {
  children: ReactNode
  permission: keyof typeof ROLE_PERMISSIONS['admin']
}

export default function ProtectedRoute({ children, permission }: ProtectedRouteProps) {
  const { user, hasPermission, permissions } = useAuth()

  // Not logged in
  if (!user) {
    return <Navigate to="/" replace />
  }

  // No permission
  if (!hasPermission(permission)) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] animate-fade-in">
        <div className="w-20 h-20 bg-red-500/20 rounded-full flex items-center justify-center mb-6">
          <ShieldX className="w-10 h-10 text-red-500" />
        </div>
        <h1 className="text-2xl font-bold text-white mb-2">Access Denied</h1>
        <p className="text-slate-400 text-center max-w-md mb-6">
          Your current role ({permissions.label}) doesn't have permission to access this page.
        </p>
        <div className="p-4 bg-slate-800 rounded-xl border border-slate-700 text-sm">
          <p className="text-slate-400 mb-2">Required permission:</p>
          <code className="text-emerald-500">{permission}</code>
        </div>
        <a 
          href="/"
          className="mt-6 px-6 py-3 bg-emerald-500 text-white rounded-xl hover:bg-emerald-600 transition-colors"
        >
          Return to Dashboard
        </a>
      </div>
    )
  }

  return <>{children}</>
}

