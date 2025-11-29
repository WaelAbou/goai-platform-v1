import { useState, useEffect } from 'react';
import {
  MessageSquare,
  Upload,
  Database,
  Sparkles,
  Settings,
  Activity,
  Brain,
  Search,
  Bot,
  BookOpen,
  Shield,
  History,
  Users,
  Sun,
  Moon,
  Wrench,
  GitBranch,
  LogOut,
  User,
  Ticket,
  UserCheck
} from 'lucide-react';
import ChatPage from './pages/ChatPage';
import DocumentsPage from './pages/DocumentsPage';
import SQLPage from './pages/SQLPage';
import SentimentPage from './pages/SentimentPage';
import DashboardPage from './pages/DashboardPage';
import SettingsPage from './pages/SettingsPage';
import AgentsPage from './pages/AgentsPage';
import PromptsPage from './pages/PromptsPage';
import AuthPage from './pages/AuthPage';
import HistoryPage from './pages/HistoryPage';
import MultiAgentPage from './pages/MultiAgentPage';
import MemoryPage from './pages/MemoryPage';
import ToolsPage from './pages/ToolsPage';
import ValidatorPage from './pages/ValidatorPage';
import SearchPage from './pages/SearchPage';
import WorkflowsPage from './pages/WorkflowsPage';
import EBCTicketsPage from './pages/EBCTicketsPage';
import KYCPage from './pages/KYCPage';
import { ToastProvider } from './components/Toast';
import { ThemeProvider, useTheme } from './components/ThemeProvider';
import { AuthProvider, useAuth } from './components/AuthContext';
import { healthApi } from './api/client';
import './index.css';

type Page = 'dashboard' | 'chat' | 'documents' | 'sql' | 'sentiment' | 'settings' | 'agents' | 'prompts' | 'auth' | 'history' | 'multi-agent' | 'memory' | 'tools' | 'validator' | 'search' | 'workflows' | 'ebc-tickets' | 'kyc';

interface NavItem {
  id: Page;
  label: string;
  icon: React.ReactNode;
}

function AppContent() {
  const [currentPage, setCurrentPage] = useState<Page>('dashboard');
  const [isConnected, setIsConnected] = useState(false);
  const { theme, toggleTheme } = useTheme();
  const { user, isAuthenticated, logout } = useAuth();

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const checkHealth = async () => {
    try {
      await healthApi.check();
      setIsConnected(true);
    } catch {
      setIsConnected(false);
    }
  };

  const navItems: NavItem[] = [
    { id: 'dashboard', label: 'Dashboard', icon: <Activity size={20} /> },
    { id: 'chat', label: 'RAG Chat', icon: <MessageSquare size={20} /> },
    { id: 'search', label: 'Search', icon: <Search size={20} /> },
    { id: 'history', label: 'History', icon: <History size={20} /> },
    { id: 'memory', label: 'Memory', icon: <Brain size={20} /> },
    { id: 'agents', label: 'AI Agents', icon: <Bot size={20} /> },
    { id: 'tools', label: 'Tools', icon: <Wrench size={20} /> },
    { id: 'multi-agent', label: 'Multi-Agent', icon: <Users size={20} /> },
    { id: 'workflows', label: 'Workflows', icon: <GitBranch size={20} /> },
    { id: 'prompts', label: 'Prompts', icon: <BookOpen size={20} /> },
    { id: 'documents', label: 'Documents', icon: <Upload size={20} /> },
    { id: 'validator', label: 'Validator', icon: <Shield size={20} /> },
    { id: 'sql', label: 'SQL Agent', icon: <Database size={20} /> },
    { id: 'sentiment', label: 'Sentiment', icon: <Sparkles size={20} /> },
    { id: 'ebc-tickets', label: 'EBC Tickets', icon: <Ticket size={20} /> },
    { id: 'kyc', label: 'Customer KYC', icon: <UserCheck size={20} /> },
  ];

  const renderPage = () => {
    switch (currentPage) {
      case 'dashboard':
        return <DashboardPage />;
      case 'chat':
        return <ChatPage />;
      case 'history':
        return <HistoryPage />;
      case 'memory':
        return <MemoryPage />;
      case 'agents':
        return <AgentsPage />;
      case 'multi-agent':
        return <MultiAgentPage />;
      case 'prompts':
        return <PromptsPage />;
      case 'documents':
        return <DocumentsPage />;
      case 'sql':
        return <SQLPage />;
      case 'sentiment':
        return <SentimentPage />;
      case 'settings':
        return <SettingsPage />;
      case 'auth':
        return <AuthPage />;
      case 'tools':
        return <ToolsPage />;
      case 'validator':
        return <ValidatorPage />;
      case 'search':
        return <SearchPage />;
      case 'workflows':
        return <WorkflowsPage />;
      case 'ebc-tickets':
        return <EBCTicketsPage />;
      case 'kyc':
        return <KYCPage />;
      default:
        return <DashboardPage />;
    }
  };

  return (
    <ToastProvider>
    <div className="app-layout">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="logo">
            <div className="logo-icon">
              <Brain size={24} />
            </div>
            <div>
              <div className="logo-text">GoAI</div>
              <div className="logo-version">Sovereign Platform v1</div>
            </div>
          </div>
        </div>

        <nav className="nav-section">
          <div className="nav-section-title">Main</div>
          {navItems.map((item) => (
            <div
              key={item.id}
              className={`nav-item ${currentPage === item.id ? 'active' : ''}`}
              onClick={() => setCurrentPage(item.id)}
            >
              {item.icon}
              <span>{item.label}</span>
            </div>
          ))}
        </nav>

        <nav className="nav-section">
          <div className="nav-section-title">System</div>
          <div 
            className={`nav-item ${currentPage === 'auth' ? 'active' : ''}`}
            onClick={() => setCurrentPage('auth')}
          >
            <Shield size={20} />
            <span>Auth</span>
          </div>
          <div 
            className={`nav-item ${currentPage === 'settings' ? 'active' : ''}`}
            onClick={() => setCurrentPage('settings')}
          >
            <Settings size={20} />
            <span>Settings</span>
          </div>
        </nav>

        <div className="sidebar-footer">
          {/* User Info */}
          {isAuthenticated && user ? (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              padding: '10px 12px',
              marginBottom: 12,
              background: 'var(--bg-tertiary)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-color)'
            }}>
              <div style={{
                width: 32,
                height: 32,
                borderRadius: '50%',
                background: 'linear-gradient(135deg, #00d4ff 0%, #7c3aed 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'white',
                fontWeight: 600,
                fontSize: 12
              }}>
                {user.username.slice(0, 2).toUpperCase()}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {user.username}
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {user.email}
                </div>
              </div>
              <button
                onClick={logout}
                title="Logout"
                style={{
                  padding: 6,
                  background: 'transparent',
                  border: 'none',
                  cursor: 'pointer',
                  color: 'var(--text-muted)',
                  borderRadius: 'var(--radius-sm)'
                }}
              >
                <LogOut size={16} />
              </button>
            </div>
          ) : (
            <button
              onClick={() => setCurrentPage('auth')}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 8,
                width: '100%',
                padding: '10px 16px',
                marginBottom: 12,
                background: 'linear-gradient(135deg, #00d4ff 0%, #7c3aed 100%)',
                border: 'none',
                borderRadius: 'var(--radius-md)',
                color: 'white',
                cursor: 'pointer',
                fontSize: 13,
                fontWeight: 600
              }}
            >
              <User size={16} />
              Sign In
            </button>
          )}
          
          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8,
              width: '100%',
              padding: '10px 16px',
              marginBottom: 12,
              background: 'var(--bg-tertiary)',
              border: '1px solid var(--border-color)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              fontSize: 13,
              transition: 'all 0.2s ease'
            }}
            title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          >
            {theme === 'dark' ? (
              <>
                <Sun size={16} />
                <span>Light Mode</span>
              </>
            ) : (
              <>
                <Moon size={16} />
                <span>Dark Mode</span>
              </>
            )}
          </button>
          
          <div className="status-indicator">
            <div className={`status-dot ${isConnected ? '' : 'error'}`} 
                 style={{ background: isConnected ? '#10b981' : '#ef4444' }} />
            <span>{isConnected ? 'API Connected' : 'Disconnected'}</span>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        {renderPage()}
      </main>
    </div>
    </ToastProvider>
  );
}

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
