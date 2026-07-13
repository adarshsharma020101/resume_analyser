import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { documentsApi, jobsApi, analysisApi } from '../lib/api'
import { useAnalysisPoll } from '../hooks/useAnalysis'
import { ScoreGauge } from '../components/ui/ScoreGauge'
import { PlayCircle, AlertTriangle, ArrowRight, ShieldCheck, CheckCircle2, Loader2, Sparkles, HelpCircle, FileText, Bookmark } from 'lucide-react'
import toast from 'react-hot-toast'

export function AnalysisResults() {
    const location = useLocation()
    const [resumes, setResumes] = useState<any[]>([])
    const [linkedinProfiles, setLinkedinProfiles] = useState<any[]>([])
    const [jobs, setJobs] = useState<any[]>([])

    const [selectedResume, setSelectedResume] = useState('')
    const [selectedLinkedin, setSelectedLinkedin] = useState('')
    const [selectedJob, setSelectedJob] = useState('')

    const [runningSessionId, setRunningSessionId] = useState<string | null>(null)
    const [submitting, setSubmitting] = useState(false)

    // Polling hook
    const { data: pollData, loading: pollLoading, error: pollError } = useAnalysisPoll(runningSessionId)

    // Grab session from router state if redirected
    useEffect(() => {
        const stateSessionId = (location.state as any)?.sessionId
        if (stateSessionId) {
            setRunningSessionId(stateSessionId)
        }
    }, [location.state])

    useEffect(() => {
        async function loadOptions() {
            try {
                const [docs, jds] = await Promise.all([
                    documentsApi.list(),
                    jobsApi.listDescriptions(),
                ])
                const rList = docs.filter((d: any) => d.doc_type === 'resume')
                const lList = docs.filter((d: any) => d.doc_type === 'linkedin_profile' || d.doc_type === 'linkedin_export' || d.doc_type === 'linkedin_pdf')
                setResumes(rList)
                setLinkedinProfiles(lList)
                setJobs(jds)

                if (rList.length > 0) setSelectedResume(rList[0].id)
                if (lList.length > 0) setSelectedLinkedin(lList[0].id)
                if (jds.length > 0) setSelectedJob(jds[0].id)
            } catch (err) {
                console.error(err)
                toast.error('Failed to load selection options')
            }
        }
        loadOptions()
    }, [])

    const handleStartAnalysis = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!selectedResume) {
            toast.error('At least one resume is required to analyze')
            return
        }
        setSubmitting(true)
        const tid = toast.loading('Initializing analysis container session...')
        try {
            const res = await analysisApi.start({
                resume_document_id: selectedResume,
                linkedin_document_id: selectedLinkedin || undefined,
                target_job_id: selectedJob || undefined,
            })
            toast.success('Analysis session started!', { id: tid })
            setRunningSessionId(res.session_id)
        } catch (err: any) {
            console.error(err)
            toast.error(err.response?.data?.detail || 'Failed to trigger analyzer', { id: tid })
        } finally {
            setSubmitting(false)
        }
    }

    const isCompleted = pollData?.status === 'completed'
    const isFailed = pollData?.status === 'failed'

    return (
        <div className="space-y-8">
            <div>
                <h2 className="text-2xl font-extrabold text-slate-800 tracking-tight">Analysis &amp; Score Alignment</h2>
                <p className="text-xs text-slate-500 mt-1">
                    Perform resume structure validation, keyword checks, profile consistency, and alignment scoring.
                </p>
            </div>

            {/* Select panel */}
            {!runningSessionId && (
                <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm">
                    <h3 className="font-bold text-slate-700 mb-4 flex items-center gap-2">
                        <PlayCircle className="w-5 h-5 text-indigo-500" /> Start Analysis Session
                    </h3>

                    <form onSubmit={handleStartAnalysis} className="space-y-6">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            <div>
                                <label className="block text-xs font-semibold uppercase text-slate-450 mb-2">Select Resume *</label>
                                <select
                                    value={selectedResume}
                                    onChange={(e) => setSelectedResume(e.target.value)}
                                    className="w-full bg-slate-50 border border-slate-250 rounded-xl py-2.5 px-4 text-xs font-medium text-slate-801 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                                    required
                                >
                                    <option value="">-- Choose Resume --</option>
                                    {resumes.map(r => (
                                        <option key={r.id} value={r.id}>{r.filename}</option>
                                    ))}
                                </select>
                            </div>

                            <div>
                                <label className="block text-xs font-semibold uppercase text-slate-450 mb-2">Select LinkedIn Profile (Optional)</label>
                                <select
                                    value={selectedLinkedin}
                                    onChange={(e) => setSelectedLinkedin(e.target.value)}
                                    className="w-full bg-slate-50 border border-slate-250 rounded-xl py-2.5 px-4 text-xs font-medium text-slate-801 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                                >
                                    <option value="">-- Skip LinkedIn --</option>
                                    {linkedinProfiles.map(l => (
                                        <option key={l.id} value={l.id}>{l.filename}</option>
                                    ))}
                                </select>
                            </div>

                            <div>
                                <label className="block text-xs font-semibold uppercase text-slate-450 mb-2">Select Target Job (Optional)</label>
                                <select
                                    value={selectedJob}
                                    onChange={(e) => setSelectedJob(e.target.value)}
                                    className="w-full bg-slate-50 border border-slate-250 rounded-xl py-2.5 px-4 text-xs font-medium text-slate-801 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                                >
                                    <option value="">-- Standalone (General) --</option>
                                    {jobs.map(j => (
                                        <option key={j.id} value={j.id}>{j.title} ({j.company})</option>
                                    ))}
                                </select>
                            </div>
                        </div>

                        <button
                            type="submit"
                            disabled={submitting}
                            className="bg-slate-900 hover:bg-slate-850 text-white font-semibold text-xs px-6 py-2.5 rounded-xl transition-all flex items-center gap-2"
                        >
                            Apply Scoring Rules
                        </button>
                    </form>
                </div>
            )}

            {/* Loading state indicator */}
            {runningSessionId && (pollLoading || !isCompleted) && !isFailed && !pollError && (
                <div className="bg-white border border-slate-200 rounded-3xl p-8 shadow-sm flex flex-col items-center justify-center gap-4 text-center">
                    <Loader2 className="w-10 h-10 text-blue-600 animate-spin" />
                    <h3 className="font-bold text-slate-800">Local CrewAI Pipeline Running...</h3>
                    <p className="text-xs text-slate-500 max-w-sm">
                        Orchestrating local agents (Structure Inspector, ATS Analyzer, Verification Auditor). Evaluating scoring weights. This can take up to 30-90 seconds.
                    </p>
                    <div className="mt-4 px-4 py-2 border rounded-full bg-slate-50 text-[10px] text-slate-400 font-mono">
                        Session ID: {runningSessionId}
                    </div>
                </div>
            )}

            {/* Error displays */}
            {(pollError || isFailed) && (
                <div className="bg-rose-50 border border-rose-200 rounded-3xl p-6 text-rose-800 space-y-3">
                    <h3 className="font-bold flex items-center gap-2">
                        <AlertTriangle className="w-5 h-5 text-rose-600" /> CrewAI Processing Failed
                    </h3>
                    <p className="text-xs">
                        {pollError || pollData?.error_message || 'An unexpected error occurred during execution. Please check your Ollama service settings.'}
                    </p>
                    <button
                        onClick={() => setRunningSessionId(null)}
                        className="bg-rose-600 hover:bg-rose-700 text-white text-xs px-4 py-2 rounded-xl font-medium transition-all"
                    >
                        Start Over
                    </button>
                </div>
            )}

            {/* Success results page view */}
            {runningSessionId && isCompleted && pollData && (
                <div className="space-y-8 animate-fadeIn">
                    {/* Main summary board */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        {/* ScoreGauge Panel */}
                        <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm flex flex-col items-center justify-center text-center">
                            <ScoreGauge score={pollData.ats_score.total_score} />
                            <div className="bg-slate-50 border border-slate-100 rounded-2xl p-4 mt-4 text-[10px] text-slate-500 leading-relaxed max-w-[240px]">
                                <strong>Estimate Type:</strong> {pollData.ats_score.score_type.toUpperCase().replace('_', ' ')}
                                <p className="mt-1">{pollData.ats_score.disclaimer}</p>
                            </div>
                        </div>

                        {/* In-depth Score Breakdowns list */}
                        <div className="md:col-span-2 bg-white border border-slate-200 rounded-3xl p-6 shadow-sm flex flex-col justify-between">
                            <div>
                                <h3 className="font-bold text-slate-700 mb-4 flex items-center justify-between">
                                    <span>Score Breakdown Component Details</span>
                                    <span className="text-xs text-slate-400 font-normal">Weights configured locally</span>
                                </h3>

                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                    {pollData.score_components.map((c: any, index: number) => (
                                        <div key={index} className="p-3.5 border border-slate-100 bg-slate-50/20 rounded-xl space-y-1">
                                            <div className="flex justify-between items-center text-xs">
                                                <span className="font-bold text-slate-700">{c.component_name}</span>
                                                <span className="font-semibold text-slate-500">{c.earned_points} / {c.max_points}</span>
                                            </div>
                                            {c.deduction_reason && (
                                                <p className="text-[10px] text-slate-500 leading-snug">
                                                    {c.deduction_reason}
                                                </p>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            </div>

                            <button
                                onClick={() => setRunningSessionId(null)}
                                className="mt-6 self-start text-xs font-bold text-blue-650 hover:underline flex items-center gap-1"
                            >
                                Trigger New Run <ArrowRight className="w-3.5 h-3.5" />
                            </button>
                        </div>
                    </div>

                    {/* Recommendations checklist block */}
                    <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm">
                        <h3 className="font-bold text-slate-700 mb-6 flex items-center gap-2">
                            <Sparkles className="w-5 h-5 text-indigo-500" /> Prioritized Recommendations ({pollData.recommendations.length})
                        </h3>

                        <div className="space-y-4">
                            {pollData.recommendations.map((r: any) => (
                                <div key={r.id} className="border border-slate-200 rounded-2xl p-5 hover:border-slate-300 transition-colors">
                                    <div className="flex flex-wrap items-center gap-2 mb-2">
                                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${r.priority === 'critical' ? 'bg-rose-500/15 text-rose-800' :
                                                r.priority === 'high' ? 'bg-amber-500/15 text-amber-800' :
                                                    r.priority === 'medium' ? 'bg-indigo-500/15 text-indigo-800' : 'bg-slate-500/15 text-slate-800'
                                            }`}>
                                            {r.priority.toUpperCase()}
                                        </span>
                                        <span className="text-[10px] font-semibold text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">
                                            {r.category.toUpperCase()}
                                        </span>
                                        {r.is_draft && (
                                            <span className="text-[10px] font-bold text-amber-800 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded-full flex items-center gap-1">
                                                <Sparkles className="w-3 h-3 text-amber-600" /> Draft Recommendation
                                            </span>
                                        )}
                                    </div>

                                    <h4 className="font-bold text-slate-800 text-sm mt-1">{r.title}</h4>
                                    <p className="text-xs text-slate-600 mt-2 leading-relaxed">
                                        <strong>Impact:</strong> {r.why_it_matters}
                                    </p>

                                    <div className="bg-slate-50 rounded-xl p-3 mt-3 text-xs border border-slate-100">
                                        <p className="font-semibold text-slate-705">Proposed Actionable Plan / Rewritten Copy:</p>
                                        <p className="text-slate-605 mt-1 font-mono italic">{r.suggested_action}</p>
                                        {r.draft_suggestion && (
                                            <div className="text-[10px] text-amber-700 bg-amber-500/5 border border-amber-500/10 p-2.5 rounded-lg mt-2.5 font-sans leading-relaxed">
                                                ⚠️ <strong>Verify Accuracy:</strong> {r._draft_notice}
                                            </div>
                                        )}
                                    </div>

                                    {/* Provenance reference list */}
                                    {r.source_citations && r.source_citations.length > 0 && (
                                        <div className="mt-3 flex flex-wrap gap-2.5 items-center">
                                            <span className="text-[10px] font-semibold text-slate-400 uppercase">Grounded Citations:</span>
                                            {r.source_citations.map((cite: any, idx: number) => (
                                                <div key={idx} className="inline-flex items-center gap-1 text-[10px] bg-blue-50 text-blue-700 font-semibold px-2 py-0.5 rounded border border-blue-500/15" title={cite.excerpt}>
                                                    <FileText className="w-3 h-3" />
                                                    <span>{cite.source_type}</span>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
