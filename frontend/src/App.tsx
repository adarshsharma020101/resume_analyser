import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { isAuthenticated } from './lib/auth'
import { Layout } from './components/Layout'

// Import Pages
import { Login } from './pages/Login'
import { Dashboard } from './pages/Dashboard'
import { UploadResume } from './pages/UploadResume'
import { LinkedInProfile } from './pages/LinkedInProfile'
import { JobDescription } from './pages/JobDescription'
import { ImportJobs } from './pages/ImportJobs'
import { AnalysisResults } from './pages/AnalysisResults'
import { Opportunities } from './pages/Opportunities'
import { ExportReport } from './pages/ExportReport'
import { Privacy } from './pages/Privacy'
import { McpSetup } from './pages/McpSetup'
import { Settings } from './pages/Settings'

function Protected({ children }: { children: React.ReactNode }) {
  return isAuthenticated() ? <Layout>{children}</Layout> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        
        <Route path="/" element={<Protected><Dashboard /></Protected>} />
        <Route path="/upload-resume" element={<Protected><UploadResume /></Protected>} />
        <Route path="/linkedin" element={<Protected><LinkedInProfile /></Protected>} />
        <Route path="/job" element={<Protected><JobDescription /></Protected>} />
        <Route path="/import-jobs" element={<Protected><ImportJobs /></Protected>} />
        <Route path="/analysis" element={<Protected><AnalysisResults /></Protected>} />
        <Route path="/opportunities" element={<Protected><Opportunities /></Protected>} />
        <Route path="/reports" element={<Protected><ExportReport /></Protected>} />
        <Route path="/privacy" element={<Protected><Privacy /></Protected>} />
        <Route path="/mcp-setup" element={<Protected><McpSetup /></Protected>} />
        <Route path="/settings" element={<Protected><Settings /></Protected>} />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
