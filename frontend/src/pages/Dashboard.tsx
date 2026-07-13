import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { documentsApi, analysisApi } from '../lib/api'
import { getUser } from '../lib/auth'
import { FileText, Linkedin, PlayCircle, Clock, AlertTriangle, ArrowRight, ShieldCheck } from 'lucide-react'
import toast from 'react-hot-toast'

export function Dashboard() {
    const [resumes, setResumes] = useState<any[]>([])
    const [linkedinProfiles, setLinkedinProfiles] = useState<any[]>([])
    const [sessions, setSessions] = useState<any[]>([])
    const [loading, setLoading] = useState(true)
    const user = getUser()

    useEffect(() => {
        async function fetchData() {
            try {
                const [docsRes, sessionsRes] = await Promise.all([
                    documentsApi.list(),
                    analysisApi.list(),
                ])
                setResumes(docsRes.filter((d: any) => d.doc_type === 'resume'))
                setLinkedinProfiles(docsRes.filter((d: any) => d.doc_type === 'linkedin_profile' || d.doc_type === 'linkedin_export' || d.doc_type === 'linkedin_pdf'))
                setSessions(sessionsRes || [])
            } catch (err: any) {
                console.error(err)
                toast.error('Failed to load dashboard data')
            } finally {
                setLoading(false)
            }
        }
        fetchData()
    }, [])

    const hasResume = resumes.length > 0
    const hasLinkedIn = linkedinProfiles.length > 0

    return (
        <div className="space-y-8">
            {/* Welcome Banner */}
            <div className="bg-slate-900 text-white rounded-3xl p-8 relative overflow-hidden shadow-xl border border-white/5">
                <div className="absolute top-[-40%] right-[-10%] w-[300px] h-[300px] rounded-full bg-blue-600/10 blur-[80px]" />
                <div className="relative z-10 max-w-2xl">
                    <span className="text-xs font-semibold text-blue-400 bg-blue-500/10 px-3 py-1 rounded-full border border-blue-500/20">
                        System: Local Sandbox
                    </span>
                    <h2 className="text-3xl font-extrabold tracking-tight mt-3">Welcome back, {user?.username}!</h2>
                    <p className="text-slate-400 mt-2 leading-relaxed">
                        Upload your resume, LinkedIn profile, or job description targets. All analyses are run using the local Ollama LLM execution pipeline, safeguarding your privacy.
                    </p>
                </div>
            </div>

            {loading ? (
                <div className="flex justify-center items-center h-48">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-900" />
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {/* Main Action Steps Column */}
                    <div className="md:col-span-2 space-y-6">
                        <h3 className="text-lg font-bold text-slate-800">Quick Start Checklist</h3>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            {/* Step 1: Resume */}
                            <div className={`p-6 rounded-2xl border transition-all ${hasResume ? 'bg-emerald-50/60 border-emerald-500/20' : 'bg-white border-slate-200 hover:border-slate-350'
                                }`}>
                                <div className="flex justify-between items-start">
                                    <div className={`p-3 rounded-xl ${hasResume ? 'bg-emerald-500/10 text-emerald-600' : 'bg-blue-500/10 text-blue-600'}`}>
                                        <FileText className="w-6 h-6" />
                                    </div>
                                    {hasResume ? (
                                        <span className="text-xs bg-emerald-500/20 text-emerald-800 font-semibold px-2.5 py-0.5 rounded-full">
                                            Uploaded
                                        </span>
                                    ) : (
                                        <span className="text-xs bg-slate-100 text-slate-600 font-semibold px-2.5 py-0.5 rounded-full">
                                            Required
                                        </span>
                                    )}
                                </div>
                                <h4 className="font-bold text-slate-800 mt-4">1. Document Resume</h4>
                                <p className="text-xs text-slate-500 mt-1">Upload your standard resume to begin the alignment check.</p>
                                <Link to="/upload-resume" className="inline-flex items-center text-xs font-bold text-blue-600 hover:text-blue-700 mt-4 gap-1">
                                    {hasResume ? 'Manage resume' : 'Upload now'} <ArrowRight className="w-3.5 h-3.5" />
                                </Link>
                            </div>

                            {/* Step 2: LinkedIn */}
                            <div className={`p-6 rounded-2xl border transition-all ${hasLinkedIn ? 'bg-emerald-50/60 border-emerald-500/20' : 'bg-white border-slate-200 hover:border-slate-350'
                                }`}>
                                <div className="flex justify-between items-start">
                                    <div className={`p-3 rounded-xl ${hasLinkedIn ? 'bg-emerald-500/10 text-emerald-600' : 'bg-blue-500/10 text-blue-700'}`}>
                                        <Linkedin className="w-6 h-6" />
                                    </div>
                                    {hasLinkedIn ? (
                                        <span className="text-xs bg-emerald-500/20 text-emerald-800 font-semibold px-2.5 py-0.5 rounded-full">
                                            Uploaded
                                        </span>
                                    ) : (
                                        <span className="text-xs bg-slate-100 text-slate-550 font-semibold px-2.5 py-0.5 rounded-full">
                                            Reference
                                        </span>
                                    )}
                                </div>
                                <h4 className="font-bold text-slate-800 mt-4">2. LinkedIn Profile</h4>
                                <p className="text-xs text-slate-500 mt-1">Connect your exported profile ZIP or pasted text data.</p>
                                <Link to="/linkedin" className="inline-flex items-center text-xs font-bold text-blue-600 hover:text-blue-700 mt-4 gap-1">
                                    {hasLinkedIn ? 'Manage profile' : 'Upload profile'} <ArrowRight className="w-3.5 h-3.5" />
                                </Link>
                            </div>
                        </div>

                        {/* Run Analysis Call to action */}
                        {hasResume ? (
                            <div className="bg-blue-50 border border-blue-500/10 rounded-2xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
                                <div>
                                    <h4 className="font-bold text-blue-900 flex items-center gap-2">
                                        <PlayCircle className="w-5 h-5 text-blue-600" /> Start Consistency &amp; Alignment Run
                                    </h4>
                                    <p className="text-xs text-blue-700 mt-1">
                                        Ready to proceed with your uploaded resume? Run the analysis to evaluate score breakdowns.
                                    </p>
                                </div>
                                <Link
                                    to="/analysis"
                                    className="bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs px-5 py-2.5 rounded-xl text-center shadow-md transition-all self-start md:self-auto"
                                >
                                    Analyze Resume
                                </Link>
                            </div>
                        ) : (
                            <div className="bg-amber-50/60 border border-amber-500/10 rounded-2xl p-6 flex items-start gap-4">
                                <AlertTriangle className="w-5 h-5 text-amber-550 flex-shrink-0 mt-0.5" />
                                <div>
                                    <h4 className="font-bold text-amber-900">Upload a Resume to Unlock Analysis</h4>
                                    <p className="text-xs text-amber-700 mt-0.5">
                                        Before starting the CrewAI evaluation agent pipeline, you must upload at least one valid resume PDF/DOCX or pasted text document.
                                    </p>
                                </div>
                            </div>
                        )}

                        {/* Recent Analysis Sessions list */}
                        <div className="bg-white border border-slate-200 rounded-2xl p-6">
                            <h3 className="font-bold text-slate-800 flex items-center gap-2 mb-4">
                                <Clock className="w-4 h-4 text-slate-500" /> Recent Runs
                            </h3>
                            {sessions.length === 0 ? (
                                <p className="text-xs text-slate-500 text-center py-6">No previous analysis runs found.</p>
                            ) : (
                                <div className="divide-y divide-slate-100">
                                    {sessions.slice(0, 5).map((s: any) => (
                                        <div key={s.session_id} className="py-3.5 flex justify-between items-center text-xs">
                                            <div>
                                                <p className="font-bold text-slate-700 uppercase">{s.analysis_type.replace('_', ' ')}</p>
                                                <p className="text-slate-400 mt-0.5">{new Date(s.created_at).toLocaleString()}</p>
                                            </div>
                                            <div className="flex items-center gap-3">
                                                <span className={`px-2.5 py-0.5 rounded-full font-semibold ${s.status === 'completed' ? 'bg-emerald-500/15 text-emerald-800' :
                                                        s.status === 'failed' ? 'bg-rose-500/15 text-rose-800' : 'bg-blue-500/15 text-blue-800'
                                                    }`}>
                                                    {s.status}
                                                </span>
                                                {s.status === 'completed' && (
                                                    <Link to="/analysis" state={{ sessionId: s.session_id }} className="text-blue-650 font-bold hover:underline">
                                                        View
                                                    </Link>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Right sidebar stats column */}
                    <div className="space-y-6">
                        <div className="bg-white border border-slate-200 rounded-2xl p-6">
                            <h3 className="font-bold text-slate-800 flex items-center gap-2 mb-4">
                                <ShieldCheck className="w-4 h-4 text-emerald-600" /> Security Guarantee
                            </h3>
                            <ul className="text-xs text-slate-655 space-y-3">
                                <li className="flex items-start gap-2">
                                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 mt-1.5 flex-shrink-0" />
                                    <span><strong>Zero Egress:</strong> Outbound requests are blocked. No API keys or remote trackers are loaded.</span>
                                </li>
                                <li className="flex items-start gap-2">
                                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 mt-1.5 flex-shrink-0" />
                                    <span><strong>Open LLM:</strong> Generative claims are run strictly inside local Ollama parameters.</span>
                                </li>
                                <li className="flex items-start gap-2">
                                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 mt-1.5 flex-shrink-0" />
                                    <span><strong>Portability:</strong> You can completely export or wipe your entire database from settings/privacy at any time.</span>
                                </li>
                            </ul>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
