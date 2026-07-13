import { Link, useLocation, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, FileText, Linkedin, Briefcase, Database,
  BarChart3, Target, Download, Shield, Settings, Info, LogOut,
} from 'lucide-react'
import clsx from 'clsx'
import { clearUser } from '../lib/auth'

const NAV = [
  { to: '/',              icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/upload-resume', icon: FileText,         label: 'Upload Resume' },
  { to: '/linkedin',      icon: Linkedin,         label: 'LinkedIn' },
  { to: '/job',           icon: Briefcase,        label: 'Job Description' },
  { to: '/import-jobs',   icon: Database,         label: 'Import Jobs' },
  { to: '/analysis',      icon: BarChart3,        label: 'Analysis Results' },
  { to: '/opportunities', icon: Target,           label: 'Opportunities' },
  { to: '/reports',       icon: Download,         label: 'Export Report' },
  { to: '/privacy',       icon: Shield,           label: 'Privacy & Data' },
  { to: '/mcp-setup',     icon: Info,             label: 'MCP Setup' },
  { to: '/settings',      icon: Settings,         label: 'Settings' },
]

export function Layout({ children }: { children: React.ReactNode }) {
  const { pathname } = useLocation()
  const navigate = useNavigate()

  const logout = () => { clearUser(); navigate('/login') }

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-56 bg-white border-r border-gray-200 flex flex-col">
        <div className="px-4 py-5 border-b border-gray-200">
          <h1 className="text-base font-bold text-brand-700">ATS Analyzer</h1>
          <p className="text-xs text-gray-500 mt-0.5">Local &amp; Private</p>
        </div>
        <nav className="flex-1 overflow-y-auto py-2">
          {NAV.map(({ to, icon: Icon, label }) => (
            <Link
              key={to}
              to={to}
              className={clsx(
                'flex items-center gap-3 px-4 py-2.5 text-sm transition-colors',
                pathname === to
                  ? 'bg-brand-50 text-brand-700 font-medium border-r-2 border-brand-600'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900',
              )}
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              {label}
            </Link>
          ))}
        </nav>
        <div className="p-4 border-t border-gray-200">
          <button onClick={logout} className="flex items-center gap-2 text-sm text-gray-500 hover:text-red-600 transition-colors w-full">
            <LogOut className="w-4 h-4" /> Sign out
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-5xl mx-auto px-6 py-8">{children}</div>
      </main>
    </div>
  )
}
