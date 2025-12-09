import { useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import Sidebar from './components/Sidebar'
import TopBar from './components/TopBar'
import Dashboard from './pages/Dashboard'
import ReviewQueue from './pages/ReviewQueue'
import Submissions from './pages/Submissions'
import Upload from './pages/Upload'
import Analytics from './pages/Analytics'
import AuditLog from './pages/AuditLog'
import UserManagement from './pages/UserManagement'
import Settings from './pages/Settings'
import ProtectedRoute from './components/ProtectedRoute'

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true)

  return (
    <AuthProvider>
      <BrowserRouter>
        <div className="flex h-screen bg-slate-900">
          <Sidebar open={sidebarOpen} setOpen={setSidebarOpen} />
          
          <main className={`flex-1 overflow-auto transition-all duration-300 ${sidebarOpen ? 'ml-64' : 'ml-20'}`}>
            <TopBar />
            <div className="p-6">
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/review" element={
                  <ProtectedRoute permission="canApprove">
                    <ReviewQueue />
                  </ProtectedRoute>
                } />
                <Route path="/submissions" element={<Submissions />} />
                <Route path="/upload" element={<Upload />} />
                <Route path="/analytics" element={
                  <ProtectedRoute permission="canExportData">
                    <Analytics />
                  </ProtectedRoute>
                } />
                <Route path="/audit" element={
                  <ProtectedRoute permission="canViewAuditLog">
                    <AuditLog />
                  </ProtectedRoute>
                } />
                <Route path="/users" element={
                  <ProtectedRoute permission="canManageUsers">
                    <UserManagement />
                  </ProtectedRoute>
                } />
                <Route path="/settings" element={
                  <ProtectedRoute permission="canAccessSettings">
                    <Settings />
                  </ProtectedRoute>
                } />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </div>
          </main>
        </div>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
