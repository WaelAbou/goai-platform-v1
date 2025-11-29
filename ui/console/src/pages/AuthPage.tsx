import { useState, useEffect } from 'react';
import {
  LogIn,
  UserPlus,
  Mail,
  Lock,
  User,
  Eye,
  EyeOff,
  Key,
  Shield,
  Loader2,
  CheckCircle,
  AlertCircle,
  Copy,
  Trash2,
  Plus,
  Clock,
  Activity
} from 'lucide-react';

interface UserData {
  id: string;
  email: string;
  username: string;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
  last_login?: string;
}

interface APIKeyData {
  id: string;
  name: string;
  prefix: string;
  created_at: string;
  last_used?: string;
  expires_at?: string;
  is_active: boolean;
  scopes: string[];
}

const API_BASE = 'http://localhost:8000/api/v1';

export default function AuthPage() {
  const [activeTab, setActiveTab] = useState<'login' | 'register'>('login');
  const [user, setUser] = useState<UserData | null>(null);
  const [apiKeys, setApiKeys] = useState<APIKeyData[]>([]);
  const [loading, setLoading] = useState(true);
  const [authLoading, setAuthLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  // Form states
  const [showPassword, setShowPassword] = useState(false);
  const [loginForm, setLoginForm] = useState({ username: '', password: '' });
  const [registerForm, setRegisterForm] = useState({ email: '', username: '', password: '', confirmPassword: '' });
  
  // API Key modal
  const [showKeyModal, setShowKeyModal] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [newKeyScopes, setNewKeyScopes] = useState<string[]>(['read', 'write']);
  const [createdKey, setCreatedKey] = useState<string | null>(null);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const token = localStorage.getItem('auth_token');
      if (token) {
        const res = await fetch(`${API_BASE}/auth/me`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setUser(data);
          fetchApiKeys(token);
        } else {
          localStorage.removeItem('auth_token');
        }
      }
    } catch (error) {
      console.error('Auth check failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchApiKeys = async (token: string) => {
    try {
      const res = await fetch(`${API_BASE}/auth/api-keys`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setApiKeys(data);
      }
    } catch (error) {
      console.error('Failed to fetch API keys:', error);
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setAuthLoading(true);
    
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(loginForm)
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || 'Login failed');
      }
      
      localStorage.setItem('auth_token', data.access_token);
      setSuccess('Login successful!');
      checkAuth();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setAuthLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    
    if (registerForm.password !== registerForm.confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    
    if (registerForm.password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }
    
    setAuthLoading(true);
    
    try {
      const res = await fetch(`${API_BASE}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: registerForm.email,
          username: registerForm.username,
          password: registerForm.password
        })
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || 'Registration failed');
      }
      
      setSuccess('Account created! Please log in.');
      setActiveTab('login');
      setLoginForm({ username: registerForm.username, password: '' });
    } catch (err: any) {
      setError(err.message);
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('auth_token');
    setUser(null);
    setApiKeys([]);
    setSuccess('Logged out successfully');
  };

  const createApiKey = async () => {
    const token = localStorage.getItem('auth_token');
    if (!token || !newKeyName) return;
    
    try {
      const res = await fetch(`${API_BASE}/auth/api-keys`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          name: newKeyName,
          scopes: newKeyScopes,
          expires_in_days: 365
        })
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to create API key');
      }
      
      setCreatedKey(data.key);
      fetchApiKeys(token);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const revokeApiKey = async (keyId: string) => {
    if (!confirm('Are you sure you want to revoke this API key?')) return;
    
    const token = localStorage.getItem('auth_token');
    if (!token) return;
    
    try {
      await fetch(`${API_BASE}/auth/api-keys/${keyId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      setApiKeys(prev => prev.filter(k => k.id !== keyId));
      setSuccess('API key revoked');
    } catch (error) {
      console.error('Failed to revoke key:', error);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setSuccess('Copied to clipboard!');
    setTimeout(() => setSuccess(''), 2000);
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>
        <Loader2 size={32} className="spin" style={{ color: 'var(--accent-primary)' }} />
      </div>
    );
  }

  // Logged in view
  if (user) {
    return (
      <>
        <header className="page-header">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h1 className="page-title">Account</h1>
              <p className="page-subtitle">Manage your account and API keys</p>
            </div>
            <button className="btn btn-secondary" onClick={handleLogout}>
              <LogIn size={18} />
              Logout
            </button>
          </div>
        </header>

        <div className="page-content">
          {success && (
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: 8, 
              padding: '12px 16px', 
              background: 'rgba(16, 185, 129, 0.15)', 
              borderRadius: 'var(--radius-md)', 
              marginBottom: 24,
              color: '#10b981'
            }}>
              <CheckCircle size={18} />
              {success}
            </div>
          )}

          <div className="grid-2">
            {/* User Info */}
            <div className="card">
              <div className="card-header">
                <h2 className="card-title">
                  <User size={20} style={{ marginRight: 8 }} />
                  Profile
                </h2>
              </div>
              
              <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 24 }}>
                <div style={{
                  width: 64,
                  height: 64,
                  borderRadius: '50%',
                  background: 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 24,
                  fontWeight: 600,
                  color: 'white'
                }}>
                  {user.username.charAt(0).toUpperCase()}
                </div>
                <div>
                  <h3 style={{ margin: 0, marginBottom: 4 }}>{user.username}</h3>
                  <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: 13 }}>{user.email}</p>
                </div>
              </div>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 16px', background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-sm)' }}>
                  <span>Status</span>
                  <span className={`tag ${user.is_active ? 'success' : 'error'}`}>
                    {user.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 16px', background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-sm)' }}>
                  <span>Role</span>
                  <span className={`tag ${user.is_admin ? 'warning' : ''}`}>
                    {user.is_admin ? 'Admin' : 'User'}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 16px', background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-sm)' }}>
                  <span>Created</span>
                  <span style={{ color: 'var(--text-secondary)' }}>
                    {new Date(user.created_at).toLocaleDateString()}
                  </span>
                </div>
                {user.last_login && (
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 16px', background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-sm)' }}>
                    <span>Last Login</span>
                    <span style={{ color: 'var(--text-secondary)' }}>
                      {new Date(user.last_login).toLocaleString()}
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* API Keys */}
            <div className="card">
              <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h2 className="card-title">
                  <Key size={20} style={{ marginRight: 8 }} />
                  API Keys
                </h2>
                <button 
                  className="btn btn-primary btn-sm"
                  onClick={() => {
                    setShowKeyModal(true);
                    setNewKeyName('');
                    setCreatedKey(null);
                  }}
                >
                  <Plus size={16} />
                  New Key
                </button>
              </div>
              
              {apiKeys.length === 0 ? (
                <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
                  <Key size={40} style={{ opacity: 0.3, marginBottom: 12 }} />
                  <p>No API keys yet</p>
                  <p style={{ fontSize: 13 }}>Create an API key to access the API programmatically</p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {apiKeys.map(key => (
                    <div key={key.id} style={{
                      padding: 16,
                      background: 'var(--bg-tertiary)',
                      borderRadius: 'var(--radius-md)',
                      border: key.is_active ? '1px solid var(--border-color)' : '1px solid #ef4444'
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                        <div>
                          <span style={{ fontWeight: 600 }}>{key.name}</span>
                          <span style={{ marginLeft: 8, fontSize: 12, color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                            {key.prefix}...
                          </span>
                        </div>
                        <button
                          className="btn btn-sm"
                          onClick={() => revokeApiKey(key.id)}
                          style={{ padding: 4, background: 'transparent', border: 'none', color: '#ef4444' }}
                          title="Revoke key"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                      <div style={{ display: 'flex', gap: 16, fontSize: 12, color: 'var(--text-muted)' }}>
                        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                          <Clock size={12} />
                          Created {new Date(key.created_at).toLocaleDateString()}
                        </span>
                        {key.last_used && (
                          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                            <Activity size={12} />
                            Used {new Date(key.last_used).toLocaleDateString()}
                          </span>
                        )}
                      </div>
                      <div style={{ marginTop: 8, display: 'flex', gap: 6 }}>
                        {key.scopes.map(scope => (
                          <span key={scope} style={{ fontSize: 10, background: 'var(--bg-hover)', padding: '2px 6px', borderRadius: 4 }}>
                            {scope}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Create API Key Modal */}
        {showKeyModal && (
          <div 
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: 'rgba(0,0,0,0.7)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 1000
            }}
            onClick={() => setShowKeyModal(false)}
          >
            <div 
              className="card"
              style={{ width: 450 }}
              onClick={e => e.stopPropagation()}
            >
              <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-color)' }}>
                <h3 style={{ margin: 0 }}>Create API Key</h3>
              </div>
              
              <div style={{ padding: 20 }}>
                {createdKey ? (
                  <div>
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      padding: 12,
                      background: 'rgba(245, 158, 11, 0.15)',
                      borderRadius: 'var(--radius-sm)',
                      marginBottom: 16,
                      color: '#f59e0b'
                    }}>
                      <AlertCircle size={18} />
                      Save this key now! It will not be shown again.
                    </div>
                    
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      padding: 12,
                      background: 'var(--bg-tertiary)',
                      borderRadius: 'var(--radius-sm)',
                      fontFamily: 'monospace',
                      fontSize: 13
                    }}>
                      <span style={{ flex: 1, wordBreak: 'break-all' }}>{createdKey}</span>
                      <button
                        className="btn btn-sm btn-secondary"
                        onClick={() => copyToClipboard(createdKey)}
                      >
                        <Copy size={14} />
                      </button>
                    </div>
                    
                    <button
                      className="btn btn-primary"
                      onClick={() => setShowKeyModal(false)}
                      style={{ width: '100%', marginTop: 16 }}
                    >
                      Done
                    </button>
                  </div>
                ) : (
                  <>
                    <div style={{ marginBottom: 16 }}>
                      <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>Key Name</label>
                      <input
                        type="text"
                        placeholder="My Integration"
                        value={newKeyName}
                        onChange={(e) => setNewKeyName(e.target.value)}
                        style={{ width: '100%' }}
                      />
                    </div>
                    
                    <div style={{ marginBottom: 16 }}>
                      <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>Permissions</label>
                      <div style={{ display: 'flex', gap: 12 }}>
                        {['read', 'write', 'admin'].map(scope => (
                          <label key={scope} style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
                            <input
                              type="checkbox"
                              checked={newKeyScopes.includes(scope)}
                              onChange={(e) => {
                                if (e.target.checked) {
                                  setNewKeyScopes(prev => [...prev, scope]);
                                } else {
                                  setNewKeyScopes(prev => prev.filter(s => s !== scope));
                                }
                              }}
                            />
                            <span style={{ textTransform: 'capitalize' }}>{scope}</span>
                          </label>
                        ))}
                      </div>
                    </div>
                    
                    <div style={{ display: 'flex', gap: 12 }}>
                      <button className="btn btn-secondary" onClick={() => setShowKeyModal(false)} style={{ flex: 1 }}>
                        Cancel
                      </button>
                      <button 
                        className="btn btn-primary" 
                        onClick={createApiKey}
                        disabled={!newKeyName}
                        style={{ flex: 1 }}
                      >
                        Create Key
                      </button>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
        )}

        <style>{`
          @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
          }
          .spin {
            animation: spin 1s linear infinite;
          }
          .tag.warning {
            background: rgba(245, 158, 11, 0.2);
            color: #f59e0b;
          }
        `}</style>
      </>
    );
  }

  // Login/Register view
  return (
    <>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        background: 'linear-gradient(135deg, var(--bg-primary) 0%, var(--bg-secondary) 100%)'
      }}>
        <div className="card" style={{ width: 420, padding: 0, overflow: 'hidden' }}>
          {/* Header with gradient */}
          <div style={{
            padding: '32px 24px',
            background: 'linear-gradient(135deg, rgba(0, 212, 255, 0.15), rgba(124, 58, 237, 0.1))',
            textAlign: 'center',
            borderBottom: '1px solid var(--border-color)'
          }}>
            <div style={{
              width: 56,
              height: 56,
              borderRadius: '50%',
              background: 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 16px'
            }}>
              <Shield size={28} color="white" />
            </div>
            <h2 style={{ margin: 0, marginBottom: 4 }}>GoAI Platform</h2>
            <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: 13 }}>
              {activeTab === 'login' ? 'Sign in to your account' : 'Create a new account'}
            </p>
          </div>

          {/* Tabs */}
          <div style={{ display: 'flex', borderBottom: '1px solid var(--border-color)' }}>
            <button
              onClick={() => { setActiveTab('login'); setError(''); }}
              style={{
                flex: 1,
                padding: '14px 0',
                background: 'transparent',
                border: 'none',
                borderBottom: activeTab === 'login' ? '2px solid var(--accent-primary)' : '2px solid transparent',
                color: activeTab === 'login' ? 'var(--accent-primary)' : 'var(--text-muted)',
                fontWeight: 500,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 8
              }}
            >
              <LogIn size={16} />
              Login
            </button>
            <button
              onClick={() => { setActiveTab('register'); setError(''); }}
              style={{
                flex: 1,
                padding: '14px 0',
                background: 'transparent',
                border: 'none',
                borderBottom: activeTab === 'register' ? '2px solid var(--accent-primary)' : '2px solid transparent',
                color: activeTab === 'register' ? 'var(--accent-primary)' : 'var(--text-muted)',
                fontWeight: 500,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 8
              }}
            >
              <UserPlus size={16} />
              Register
            </button>
          </div>

          {/* Forms */}
          <div style={{ padding: 24 }}>
            {error && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '12px 16px',
                background: 'rgba(239, 68, 68, 0.15)',
                borderRadius: 'var(--radius-sm)',
                marginBottom: 16,
                color: '#ef4444',
                fontSize: 13
              }}>
                <AlertCircle size={16} />
                {error}
              </div>
            )}

            {success && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '12px 16px',
                background: 'rgba(16, 185, 129, 0.15)',
                borderRadius: 'var(--radius-sm)',
                marginBottom: 16,
                color: '#10b981',
                fontSize: 13
              }}>
                <CheckCircle size={16} />
                {success}
              </div>
            )}

            {activeTab === 'login' ? (
              <form onSubmit={handleLogin}>
                <div style={{ marginBottom: 16 }}>
                  <label style={{ display: 'block', marginBottom: 8, fontWeight: 500, fontSize: 13 }}>
                    Username or Email
                  </label>
                  <div style={{ position: 'relative' }}>
                    <User size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                    <input
                      type="text"
                      placeholder="johndoe"
                      value={loginForm.username}
                      onChange={(e) => setLoginForm(prev => ({ ...prev, username: e.target.value }))}
                      style={{ paddingLeft: 38, width: '100%' }}
                      required
                    />
                  </div>
                </div>
                
                <div style={{ marginBottom: 24 }}>
                  <label style={{ display: 'block', marginBottom: 8, fontWeight: 500, fontSize: 13 }}>
                    Password
                  </label>
                  <div style={{ position: 'relative' }}>
                    <Lock size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                    <input
                      type={showPassword ? 'text' : 'password'}
                      placeholder="••••••••"
                      value={loginForm.password}
                      onChange={(e) => setLoginForm(prev => ({ ...prev, password: e.target.value }))}
                      style={{ paddingLeft: 38, paddingRight: 40, width: '100%' }}
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      style={{ position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)', background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}
                    >
                      {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>
                
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={authLoading}
                  style={{ width: '100%' }}
                >
                  {authLoading ? (
                    <>
                      <Loader2 size={18} className="spin" />
                      Signing in...
                    </>
                  ) : (
                    <>
                      <LogIn size={18} />
                      Sign In
                    </>
                  )}
                </button>
              </form>
            ) : (
              <form onSubmit={handleRegister}>
                <div style={{ marginBottom: 16 }}>
                  <label style={{ display: 'block', marginBottom: 8, fontWeight: 500, fontSize: 13 }}>
                    Email
                  </label>
                  <div style={{ position: 'relative' }}>
                    <Mail size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                    <input
                      type="email"
                      placeholder="john@example.com"
                      value={registerForm.email}
                      onChange={(e) => setRegisterForm(prev => ({ ...prev, email: e.target.value }))}
                      style={{ paddingLeft: 38, width: '100%' }}
                      required
                    />
                  </div>
                </div>
                
                <div style={{ marginBottom: 16 }}>
                  <label style={{ display: 'block', marginBottom: 8, fontWeight: 500, fontSize: 13 }}>
                    Username
                  </label>
                  <div style={{ position: 'relative' }}>
                    <User size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                    <input
                      type="text"
                      placeholder="johndoe"
                      value={registerForm.username}
                      onChange={(e) => setRegisterForm(prev => ({ ...prev, username: e.target.value }))}
                      style={{ paddingLeft: 38, width: '100%' }}
                      required
                    />
                  </div>
                </div>
                
                <div style={{ marginBottom: 16 }}>
                  <label style={{ display: 'block', marginBottom: 8, fontWeight: 500, fontSize: 13 }}>
                    Password
                  </label>
                  <div style={{ position: 'relative' }}>
                    <Lock size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                    <input
                      type={showPassword ? 'text' : 'password'}
                      placeholder="Min 8 characters"
                      value={registerForm.password}
                      onChange={(e) => setRegisterForm(prev => ({ ...prev, password: e.target.value }))}
                      style={{ paddingLeft: 38, paddingRight: 40, width: '100%' }}
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      style={{ position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)', background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}
                    >
                      {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>
                
                <div style={{ marginBottom: 24 }}>
                  <label style={{ display: 'block', marginBottom: 8, fontWeight: 500, fontSize: 13 }}>
                    Confirm Password
                  </label>
                  <div style={{ position: 'relative' }}>
                    <Lock size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                    <input
                      type={showPassword ? 'text' : 'password'}
                      placeholder="Repeat password"
                      value={registerForm.confirmPassword}
                      onChange={(e) => setRegisterForm(prev => ({ ...prev, confirmPassword: e.target.value }))}
                      style={{ paddingLeft: 38, width: '100%' }}
                      required
                    />
                  </div>
                </div>
                
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={authLoading}
                  style={{ width: '100%' }}
                >
                  {authLoading ? (
                    <>
                      <Loader2 size={18} className="spin" />
                      Creating account...
                    </>
                  ) : (
                    <>
                      <UserPlus size={18} />
                      Create Account
                    </>
                  )}
                </button>
              </form>
            )}
          </div>
        </div>
      </div>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .spin {
          animation: spin 1s linear infinite;
        }
      `}</style>
    </>
  );
}

