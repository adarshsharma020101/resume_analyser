import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { privacyApi } from '../lib/api'
import { clearUser } from '../lib/auth'
import { ShieldCheck, ShieldAlert, Download, Trash2, HelpCircle } from 'lucide-react'
import toast from 'react-hot-toast'

export function Privacy() {
    const [deleting, setDeleting] = useState(false)
    const [exporting, setExporting] = useState(false)
    const navigate = useNavigate()

    const handleExport = async () => {
        setExporting(true)
        const tid = toast.loading('Compiling portable JSON export...')
        try {
            const res = await privacyApi.exportData()
            const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(res, null, 2))
            const downloadAnchor = document.createElement('a')
            downloadAnchor.setAttribute('href', dataStr)
            downloadAnchor.setAttribute('download', `ats_analyzer_export_${new Date().toISOString().split('T')[0]}.json`)
            document.body.appendChild(downloadAnchor)
            downloadAnchor.click()
            downloadAnchor.remove()
            toast.success('Local export downloaded successfully!', { id: tid })
        } catch (err: any) {
            console.error(err)
            toast.error('Failed to export portable profile list', { id: tid })
        } finally {
            setExporting(false)
        }
    }

    const handleDeleteAllData = async () => {
        const confirmation = confirm(
            'CRITICAL: This will destroy your local account, all uploaded resume/LinkedIn files, analysis tables, recommendations, and vector DB indices from SQLite and ChromaDB permanently.\n\nThis execution cannot be undone. Are you absolutely sure?'
        )
        if (!confirmation) return

        setDeleting(true)
        const tid = toast.loading('Deleting account databases. Please wait...')
        try {
            await privacyApi.deleteAll()
            clearUser()
            toast.success('Your local environment has been entirely wiped.', { id: tid, duration: 6000 })
            navigate('/login')
        } catch (err: any) {
            console.error(err)
            toast.error('Unable to clear profile database tables.', { id: tid })
        } finally {
            setDeleting(false)
        }
    }

    return (
        <div className="space-y-8">
            <div>
                <h2 className="text-2xl font-extrabold text-slate-800 tracking-tight flex items-center gap-2">
                    <ShieldCheck className="w-6 h-6 text-emerald-555" /> Privacy &amp; Data Governance
                </h2>
                <p className="text-xs text-slate-500 mt-1">
                    Review security certifications, download full profiles data ports, or purge your local workstation storage.
                </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div className="lg:col-span-2 space-y-6">
                    {/* Data Portability (Export) */}
                    <div className="bg-white border border-slate-205 rounded-3xl p-6 shadow-sm">
                        <h3 className="font-bold text-slate-700 mb-2 flex items-center gap-1.5">
                            <Download className="w-4.5 h-4.5 text-slate-500" /> Portable Data Export
                        </h3>
                        <p className="text-xs text-slate-500 mb-4">
                            Download your structured profile settings, education logs, skills parameters, and analysis session history in standard JSON format.
                        </p>

                        <button
                            onClick={handleExport}
                            disabled={exporting}
                            className="bg-slate-900 hover:bg-slate-850 text-white font-semibold text-xs px-5 py-2.5 rounded-xl transition-all disabled:opacity-50 flex items-center gap-1.5"
                        >
                            Export Local Data Portfolio
                        </button>
                    </div>

                    {/* Wipe data table */}
                    <div className="bg-red-50/50 border border-red-500/10 rounded-3xl p-6 shadow-sm">
                        <h3 className="font-bold text-rose-800 mb-2 flex items-center gap-1.5">
                            <ShieldAlert className="w-4.5 h-4.5 text-rose-600" /> Purge Account and Media
                        </h3>
                        <p className="text-xs text-slate-550 mb-4">
                            Completely delete your login identifier credentials, decrypted files stored on disk, matching indexes, and document history databases from workspace repositories.
                        </p>

                        <button
                            onClick={handleDeleteAllData}
                            disabled={deleting}
                            className="bg-rose-600 hover:bg-rose-700 text-white font-semibold text-xs px-5 py-2.5 rounded-xl transition-all disabled:opacity-50 flex items-center gap-1.5"
                        >
                            <Trash2 className="w-4 h-4" /> Purge Workstation Storage
                        </button>
                    </div>
                </div>

                {/* Security Disclaimers */}
                <div className="space-y-6">
                    <div className="bg-slate-900 text-white rounded-2xl p-6 text-xs border border-white/5 space-y-4">
                        <h4 className="font-bold flex items-center gap-1.5 text-emerald-450"><ShieldCheck className="w-4 h-4" /> Locally Validated Sandbox</h4>
                        <p className="leading-relaxed text-slate-400">
                            The ATS Analyzer executes in isolation. System components DO NOT establish external connections to remote ports except local Docker/Ollama layers.
                        </p>
                        <p className="leading-relaxed text-slate-450 uppercase tracking-wider text-[9px]">
                            No cookies, tracking pixels, telemetry packages, cleanups, or analytics APIs are loaded.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    )
}
