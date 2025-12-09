import { createContext, useContext, useState, ReactNode } from 'react'

export type UserRole = 'admin' | 'supervisor' | 'user'

export interface User {
  id: string
  name: string
  email: string
  role: UserRole
  avatar?: string
  department?: string
}

// Role-based permissions
export const ROLE_PERMISSIONS = {
  admin: {
    label: 'Administrator',
    color: 'red',
    canApprove: true,
    canReject: true,
    canBulkApprove: true,
    canEditExtracted: true,
    canAccessSettings: true,
    canManageUsers: true,
    canViewAllDepartments: true,
    canExportData: true,
    canConfigureAutoApprove: true,
    canAccessAPI: true,
    canViewAuditLog: true,
  },
  supervisor: {
    label: 'Supervisor',
    color: 'yellow',
    canApprove: true,
    canReject: true,
    canBulkApprove: true,
    canEditExtracted: true,
    canAccessSettings: false,
    canManageUsers: false,
    canViewAllDepartments: true,
    canExportData: true,
    canConfigureAutoApprove: false,
    canAccessAPI: false,
    canViewAuditLog: true,
  },
  user: {
    label: 'User',
    color: 'blue',
    canApprove: false,
    canReject: false,
    canBulkApprove: false,
    canEditExtracted: false,
    canAccessSettings: false,
    canManageUsers: false,
    canViewAllDepartments: false,
    canExportData: false,
    canConfigureAutoApprove: false,
    canAccessAPI: false,
    canViewAuditLog: false,
  },
} as const

// Demo users for each role
export const DEMO_USERS: Record<UserRole, User> = {
  admin: {
    id: 'admin-001',
    name: 'Sarah Chen',
    email: 'sarah.chen@company.com',
    role: 'admin',
    department: 'IT Administration',
  },
  supervisor: {
    id: 'super-001',
    name: 'Michael Torres',
    email: 'michael.torres@company.com',
    role: 'supervisor',
    department: 'Sustainability',
  },
  user: {
    id: 'user-001',
    name: 'Emily Johnson',
    email: 'emily.johnson@company.com',
    role: 'user',
    department: 'Operations',
  },
}

interface AuthContextType {
  user: User | null
  permissions: typeof ROLE_PERMISSIONS[UserRole]
  login: (role: UserRole) => void
  logout: () => void
  switchRole: (role: UserRole) => void
  hasPermission: (permission: keyof typeof ROLE_PERMISSIONS[UserRole]) => boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(DEMO_USERS.admin)

  const permissions = user ? ROLE_PERMISSIONS[user.role] : ROLE_PERMISSIONS.user

  const login = (role: UserRole) => {
    setUser(DEMO_USERS[role])
  }

  const logout = () => {
    setUser(null)
  }

  const switchRole = (role: UserRole) => {
    setUser(DEMO_USERS[role])
  }

  const hasPermission = (permission: keyof typeof ROLE_PERMISSIONS[UserRole]) => {
    return permissions[permission] as boolean
  }

  return (
    <AuthContext.Provider value={{ user, permissions, login, logout, switchRole, hasPermission }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

