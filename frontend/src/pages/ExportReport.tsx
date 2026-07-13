import { useEffect, useState } from 'react'
import { analysisApi, reportsApi } from '../lib/api'
import { Download, FileJson, FileText, Globe, AlertCircle, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'

export function ExportReport() {
    const [sessions, setSessions] = useState<any[]>([])
    const [selectedSessionId, setSelectedSessionId] = useState('')
    const [loading, setLoading] = useState(true)
    const [generating, setGenerating] = useState(false)
    const [downloadUrls, setDownloadUrls] = useState<{ [key: string]: string }>({})

    useEffect(() => {
        async function loadSessions() {
            try {
                const list = await analysisApi.list()
                const completed = list.filter((s: any) => s.status === 'completed')
                setSessions(completed || [])
                if (completed.length > 0) {
                    setSelectedSessionId(completed[0].session_id)
                }
            } catch (err) {
                console.error(err)
                toast.error('Failed to load sessions')
            } finally {
                setLoading(false)
            }
        }
        loadSessions()
    }, [])

    const handleGenerate = async (format: 'json' | 'html' | 'pdf') => {
        if (!selectedSessionId) {
            toast.error('Please select an analysis session context')
            return
        }
        setGenerating(true)
        const tid = toast.loading(`Generating local ${format.toUpperCase()} report...`)
        try {
            const res = await reportsApi.generate(selectedSessionId, format)
            toast.success(`${format.toUpperCase()} report generated!`, { id: tid })
            // Cache URL link
            const downloadPath = reportsApi.downloadUrl(selectedSessionId, format)
            setDownloadUrls(prev => ({ ...prev, [format]: downloadPath }))
        } catch (err: any) {
            console.error(err)
            toast.error(err.response?.data?.detail || 'Failed to generate report', { id: tid })
        } finally {
            setGenerating(false)
        }
    }

    return (
        <div className="space-y-8">
            <div>
                <h2 className="text-2xl font-extrabold text-slate-800 tracking-tight flex items-center gap-2">
                    <Download className="w-6 h-6 text-indigo-600" /> Export Performance Reports
                </h2>
                <p className="text-xs text-slate-500 mt-1">
                    Export full scoring lists and itemized recommendation details from completed local analysis runs.
                </p>
            </div>

            {loading ? (
                <div className="flex justify-center py-12">
                    <Loader2 className="w-8 h-8 animate-spin text-slate-400" />
                </div>
            ) : sessions.length === 0 ? (
                <div className="bg-white border rounded-3xl p-8 text-center text-xs text-slate-500 shadow-sm max-w-md mx-auto">
                    <AlertCircle className="w-8 h-8 text-amber-500 mx-auto mb-2" />
                    <h4 className="font-bold text-slate-700">No Completed Sessions</h4>
                    <p className="mt-1">Analyze a resume before exporting outputs.</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    <div className="lg:col-span-2 space-y-6">
                        <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm">
                            <h3 className="font-bold text-slate-700 mb-4">1. Select Target Session Context</h3>

                            <select
                                value={selectedSessionId}
                                onChange={(e) => {
                                    setSelectedSessionId(e.target.value)
                                    setDownloadUrls({}) // Reset on change
                                }}
                                className="w-full bg-slate-50 border border-slate-200 rounded-xl py-2.5 px-4 text-xs font-medium text-slate-808 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                            >
                                {sessions.map(s => (
                                    <option key={s.session_id} value={s.session_id}>
                                        {s.analysis_type.toUpperCase().replace('_', ' ')} - {new Date(s.created_at).toLocaleString()}
                                    </option>
                                ))}
                            </select>
                        </div>

                        {/* Export format panels */}
                        <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm">
                            <h3 className="font-bold text-slate-700 mb-4">2. Pick Output Format</h3>

                            <div className="space-y-4">
                                {/* JSON */}
                                <div className="p-4 border rounded-2xl flex items-center justify-between gap-4 bg-slate-50/20">
                                    <div className="flex items-start gap-3 text-xs">
                                        <div className="p-2.5 bg-blue-50 text-blue-650 rounded-xl">
                                            <FileJson className="w-5 h-5" />
                                        </div>
                                        <div>
                                            <h4 className="font-bold text-slate-800">Structured JSON Metadata</h4>
                                            <p className="text-slate-450 mt-0.5">Machine-readable data including claim logs and hash signatures.</p>
                                        </div>
                                    </div>

                                    <div className="flex items-center gap-2">
                                        <button
                                            onClick={() => handleGenerate('json')}
                                            disabled={generating}
                                            className="bg-slate-900 hover:bg-slate-850 text-white font-semibold text-xs px-3.5 py-2 rounded-xl transition-all"
                                        >
                                            Build
                                        </button>
                                        {downloadUrls['json'] && (
                                            <a
                                                href={downloadUrls['json']}
                                                download
                                                className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs px-3.5 py-2 rounded-xl transition-all flex items-center gap-1"
                                            >
                                                <Download className="w-3.5 h-3.5" /> Download
                                            </a>
                                        )}
                                    </div>
                                </div>

                                {/* HTML */}
                                <div className="p-4 border rounded-2xl flex items-center justify-between gap-4 bg-slate-50/20">
                                    <div className="flex items-start gap-3 text-xs">
                                        <div className="p-2.5 bg-indigo-50 text-indigo-650 rounded-xl">
                                            <Globe className="w-5 h-5" />
                                        </div>
                                        <div>
                                            <h4 className="font-bold text-slate-800">Static HTML Page</h4>
                                            <p className="text-slate-450 mt-0.5">Styled HTML report bundle for general user browser sharing.</p>
                                        </div>
                                    </div>

                                    <div className="flex items-center gap-2">
                                        <button
                                            onClick={() => handleGenerate('html')}
                                            disabled={generating}
                                            className="bg-slate-900 hover:bg-slate-850 text-white font-semibold text-xs px-3.5 py-2 rounded-xl transition-all"
                                        >
                                            Build
                                        </button>
                                        {downloadUrls['html'] && (
                                            <a
                                                href={downloadUrls['html']}
                                                target="_blank"
                                                rel="noreferrer"
                                                className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs px-3.5 py-2 rounded-xl transition-all flex items-center gap-1"
                                            >
                                                Open Website
                                            </a>
                                        )}
                                    </div>
                                </div>

                                {/* PDF */}
                                <div className="p-4 border rounded-2xl flex items-center justify-between gap-4 bg-slate-50/20">
                                    <div className="flex items-start gap-3 text-xs">
                                        <div className="p-2.5 bg-purple-50 text-purple-650 rounded-xl">
                                            <FileText className="w-5 h-5" />
                                        </div>
                                        <div>
                                            <h4 className="font-bold text-slate-800">Standard PDF Document</h4>
                                            <p className="text-slate-455 mt-0.5">Printable corporate PDF sheet incorporating scoring details.</p>
                                        </div>
                                    </div>

                                    <div className="flex items-center gap-2">
                                        <button
                                            onClick={() => handleGenerate('pdf')}
                                            disabled={generating}
                                            className="bg-slate-900 hover:bg-slate-850 text-white font-semibold text-xs px-3.5 py-2 rounded-xl transition-all"
                                        >
                                            Build
                                        </button>
                                        {downloadUrls['pdf'] && (
                                            <a
                                                href={downloadUrls['pdf']}
                                                download
                                                className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs px-3.5 py-2 rounded-xl transition-all flex items-center gap-1"
                                            >
                                                <Download className="w-3.5 h-3.5" /> Download PDF
                                            </a>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="space-y-6">
                        <div className="bg-amber-50/60 border border-amber-550/15 rounded-2xl p-6 text-xs text-amber-800 space-y-2">
                            <h4 className="font-bold flex items-center gap-1.5"><AlertCircle className="w-4 h-4 text-amber-600" /> Export Policies</h4>
                            <p className="leading-relaxed">
                                Rendered files are temporarily stored within local servers. Ensure you clean these folders if using shared desktop configurations.
                            </p>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
