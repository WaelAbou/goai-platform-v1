import { useState } from 'react'
import { 
  Mail, 
  Database, 
  Shield, 
  Bell, 
  Sliders,
  Check,
  Copy,
  ExternalLink
} from 'lucide-react'

export default function Settings() {
  const [autoApproveThreshold, setAutoApproveThreshold] = useState(95)
  const [notifications, setNotifications] = useState({
    email: true,
    lowConfidence: true,
    dailyDigest: false,
    anomalies: true
  })

  return (
    <div className="max-w-4xl space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="text-slate-400">Configure your sustainability platform</p>
      </div>

      {/* Auto-Approve Settings */}
      <div className="bg-slate-800 rounded-2xl border border-slate-700 overflow-hidden">
        <div className="p-6 border-b border-slate-700">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-emerald-500/20 rounded-xl flex items-center justify-center">
              <Sliders className="w-5 h-5 text-emerald-500" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white">Auto-Approve Threshold</h3>
              <p className="text-slate-400 text-sm">Documents above this confidence will be auto-approved</p>
            </div>
          </div>
        </div>
        <div className="p-6">
          <div className="flex items-center gap-6">
            <input
              type="range"
              min="70"
              max="100"
              value={autoApproveThreshold}
              onChange={(e) => setAutoApproveThreshold(Number(e.target.value))}
              className="flex-1 h-2 bg-slate-700 rounded-full appearance-none cursor-pointer accent-emerald-500"
            />
            <span className="text-2xl font-bold text-emerald-500 w-20 text-right">
              {autoApproveThreshold}%
            </span>
          </div>
          <p className="text-slate-400 text-sm mt-4">
            Current setting: Documents with {autoApproveThreshold}%+ confidence will be auto-approved
          </p>
        </div>
      </div>

      {/* Email Integration */}
      <div className="bg-slate-800 rounded-2xl border border-slate-700 overflow-hidden">
        <div className="p-6 border-b border-slate-700">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-500/20 rounded-xl flex items-center justify-center">
              <Mail className="w-5 h-5 text-blue-500" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white">Email Integration</h3>
              <p className="text-slate-400 text-sm">Forward documents to process automatically</p>
            </div>
          </div>
        </div>
        <div className="p-6 space-y-4">
          <div className="flex items-center justify-between p-4 bg-slate-700/50 rounded-xl">
            <div>
              <p className="text-white font-medium">Forwarding Address</p>
              <p className="text-emerald-500 font-mono">sustainability@yourcompany.com</p>
            </div>
            <button className="p-2 hover:bg-slate-600 rounded-lg transition-colors">
              <Copy className="w-5 h-5 text-slate-400" />
            </button>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <WebhookCard
              provider="SendGrid"
              status="active"
              url="/api/v1/email/webhook/sendgrid"
            />
            <WebhookCard
              provider="Mailgun"
              status="inactive"
              url="/api/v1/email/webhook/mailgun"
            />
          </div>
          
          <a 
            href="/api/v1/email/"
            target="_blank"
            className="flex items-center gap-2 text-emerald-500 hover:underline"
          >
            <ExternalLink className="w-4 h-4" />
            Open Email Setup Guide
          </a>
        </div>
      </div>

      {/* Notifications */}
      <div className="bg-slate-800 rounded-2xl border border-slate-700 overflow-hidden">
        <div className="p-6 border-b border-slate-700">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-yellow-500/20 rounded-xl flex items-center justify-center">
              <Bell className="w-5 h-5 text-yellow-500" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white">Notifications</h3>
              <p className="text-slate-400 text-sm">Configure how you receive alerts</p>
            </div>
          </div>
        </div>
        <div className="p-6 space-y-4">
          <NotificationToggle
            label="Email Notifications"
            description="Receive updates via email"
            checked={notifications.email}
            onChange={(checked) => setNotifications({ ...notifications, email: checked })}
          />
          <NotificationToggle
            label="Low Confidence Alerts"
            description="Alert when documents need manual review"
            checked={notifications.lowConfidence}
            onChange={(checked) => setNotifications({ ...notifications, lowConfidence: checked })}
          />
          <NotificationToggle
            label="Daily Digest"
            description="Summary of daily activity"
            checked={notifications.dailyDigest}
            onChange={(checked) => setNotifications({ ...notifications, dailyDigest: checked })}
          />
          <NotificationToggle
            label="Anomaly Detection"
            description="Alert for unusual emissions data"
            checked={notifications.anomalies}
            onChange={(checked) => setNotifications({ ...notifications, anomalies: checked })}
          />
        </div>
      </div>

      {/* API Access */}
      <div className="bg-slate-800 rounded-2xl border border-slate-700 overflow-hidden">
        <div className="p-6 border-b border-slate-700">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-purple-500/20 rounded-xl flex items-center justify-center">
              <Database className="w-5 h-5 text-purple-500" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white">API Access</h3>
              <p className="text-slate-400 text-sm">Connect external systems</p>
            </div>
          </div>
        </div>
        <div className="p-6 space-y-4">
          <div className="p-4 bg-slate-700/50 rounded-xl">
            <p className="text-sm text-slate-400 mb-2">API Base URL</p>
            <code className="text-emerald-500 font-mono">http://localhost:8000/api/v1</code>
          </div>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <a href="/docs" target="_blank" className="p-4 bg-slate-700/50 rounded-xl hover:bg-slate-600/50 transition-colors">
              <p className="text-white font-medium">📚 API Documentation</p>
              <p className="text-slate-400">Swagger UI</p>
            </a>
            <a href="/api/v1/review/" target="_blank" className="p-4 bg-slate-700/50 rounded-xl hover:bg-slate-600/50 transition-colors">
              <p className="text-white font-medium">🖥️ Review Dashboard</p>
              <p className="text-slate-400">Built-in UI</p>
            </a>
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex justify-end">
        <button className="flex items-center gap-2 px-6 py-3 bg-emerald-500 text-white rounded-xl hover:bg-emerald-600 transition-colors">
          <Check className="w-5 h-5" />
          Save Settings
        </button>
      </div>
    </div>
  )
}

function WebhookCard({ provider, status, url }: { provider: string; status: 'active' | 'inactive'; url: string }) {
  return (
    <div className="p-4 bg-slate-700/50 rounded-xl">
      <div className="flex items-center justify-between mb-2">
        <span className="font-medium text-white">{provider}</span>
        <span className={`px-2 py-1 rounded-full text-xs ${
          status === 'active' ? 'bg-emerald-500/20 text-emerald-500' : 'bg-slate-600 text-slate-400'
        }`}>
          {status}
        </span>
      </div>
      <code className="text-xs text-slate-400">{url}</code>
    </div>
  )
}

function NotificationToggle({ label, description, checked, onChange }: {
  label: string
  description: string
  checked: boolean
  onChange: (checked: boolean) => void
}) {
  return (
    <div className="flex items-center justify-between p-4 bg-slate-700/50 rounded-xl">
      <div>
        <p className="text-white font-medium">{label}</p>
        <p className="text-slate-400 text-sm">{description}</p>
      </div>
      <button
        onClick={() => onChange(!checked)}
        className={`w-12 h-6 rounded-full transition-colors ${checked ? 'bg-emerald-500' : 'bg-slate-600'}`}
      >
        <span className={`block w-5 h-5 bg-white rounded-full transition-transform ${checked ? 'translate-x-6' : 'translate-x-0.5'}`} />
      </button>
    </div>
  )
}

