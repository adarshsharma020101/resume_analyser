import { useEffect, useState } from 'react'
import { jobsApi, analysisApi } from '../lib/api'
import { Target, Search, Filter, AlertTriangle, ArrowRight, ShieldCheck, CheckCircle2, Loader2, Sparkles, Building2, MapPin, BarChart3, HelpCircle } from 'lucide-react'
import toast from 'react-hot-toast'

export function Opportunities() {
    const [sessions, setSessions] = useState<any[]>([])
    const [selectedSessionId, setSelectedSessionId] = useState('')
    const [matches, setMatches] = useState<any[]>([])
    const [searchTerm, setSearchTerm] = useState('')
    const [minScore, setMinScore] = useState(0)
    const [loading, setLoading] = useState(true)
    const [matchingLoading, setMatchingLoading] = useState(false)

    // Details expand toggle
    const [expandedId, setExpandedId] = useState<string | null>(null)

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
                toast.error('Failed to load completed analysis sessions')
            } finally {
                setLoading(false)
            }
        }
        loadSessions()
    }, [])

    useEffect(() => {
        if (!selectedSessionId) {
            setMatches([])
            return
        }
        async function fetchMatches() {
            setMatchingLoading(true)
            try {
                const res = await analysisApi.get(selectedSessionId)
                setMatches(res.opportunity_matches || [])
            } catch (err) {
                console.error(err)
                toast.error('Failed to load matches for this session')
            } finally {
                setMatchingLoading(false)
            }
        }
        fetchMatches()
    }, [selectedSessionId])

    const filteredMatches = matches.filter((m: any) => {
        // Basic search on company or title (some might not have it loaded synchronously)
        const label = `${m.match_label}`.toLowerCase()
        const exp = `${m.match_explanation}`.toLowerCase()

        const matchesSearch = label.includes(searchTerm.toLowerCase()) || exp.includes(searchTerm.toLowerCase())
        const scoreVal = m.final_match_score * 100
        const matchesScore = scoreVal >= minScore

        return matchesSearch && matchesScore
    })

    return (
        <div className="space-y-8">
            <div>
                <h2 className="text-2xl font-extrabold text-slate-800 tracking-tight flex items-center gap-2">
                    <Target className="w-6 h-6 text-emerald-500" /> Opportunity Alignment Matches
                </h2>
                <p className="text-xs text-slate-500 mt-1">
                    Displays scores matched against locally imported job listings. No telemetry or external cloud tracking occurs.
                </p>
            </div>

            {loading ? (
                <div className="flex justify-center items-center h-48">
                    <Loader2 className="w-8 h-8 animate-spin text-slate-400" />
                </div>
            ) : sessions.length === 0 ? (
                <div className="bg-white border border-slate-200 rounded-3xl p-8 text-center text-xs text-slate-500 shadow-sm max-w-lg mx-auto">
                    <AlertTriangle className="w-8 h-8 text-amber-500 mx-auto mb-3" />
                    <h4 className="font-bold text-slate-700">No Completed Analyses Found</h4>
                    <p className="mt-1">
                        Before scanning matches, trigger an analysis session to populate your resume profile traits.
                    </p>
                </div>
            ) : (
                <div className="space-y-6">
                    {/* Controls Bar */}
                    <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm grid grid-cols-1 md:grid-cols-4 gap-6 items-end">
                        <div>
                            <label className="block text-xs font-semibold uppercase text-slate-450 mb-2">Analysis Session Context</label>
                            <select
                                value={selectedSessionId}
                                onChange={(e) => setSelectedSessionId(e.target.value)}
                                className="w-full bg-slate-50 border border-slate-250 rounded-xl py-2 px-3.5 text-xs font-medium text-slate-801 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                            >
                                {sessions.map(s => (
                                    <option key={s.session_id} value={s.session_id}>
                                        {s.analysis_type.toUpperCase().replace('_', ' ')} - {new Date(s.created_at).toLocaleDateString()}
                                    </option>
                                ))}
                            </select>
                        </div>

                        <div>
                            <label className="block text-xs font-semibold uppercase text-slate-450 mb-2">Search Match Label</label>
                            <div className="relative">
                                <span className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
                                    <Search className="w-3.5 h-3.5 text-slate-400" />
                                </span>
                                <input
                                    type="text"
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                    className="w-full bg-slate-50 border border-slate-250 rounded-xl py-2 pl-9 pr-3.5 text-xs font-medium text-slate-801 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                                    placeholder="e.g. Strong overlap..."
                                />
                            </div>
                        </div>

                        <div>
                            <label className="block text-xs font-semibold uppercase text-slate-450 mb-2">Minimum Score Match ({minScore}%)</label>
                            <input
                                type="range"
                                min="0"
                                max="100"
                                value={minScore}
                                onChange={(e) => setMinScore(Number(e.target.value))}
                                className="w-full h-2 bg-slate-100 rounded-lg appearance-none cursor-pointer accent-emerald-500 mb-2"
                            />
                        </div>

                        <div className="text-right text-[10px] text-slate-400 leading-snug">
                            Total matched records currently displayed: <strong>{filteredMatches.length}</strong>
                        </div>
                    </div>

                    {/* Results grid */}
                    {matchingLoading ? (
                        <div className="flex justify-center py-12">
                            <Loader2 className="w-8 h-8 animate-spin text-emerald-500" />
                        </div>
                    ) : filteredMatches.length === 0 ? (
                        <div className="text-center py-12 border border-dashed border-slate-200 rounded-3xl bg-slate-50/50 text-xs text-slate-450">
                            No local matching opportunities met your search criteria.
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {filteredMatches.map((m: any) => {
                                const isExpanded = expandedId === m.id
                                const pct = Math.round(m.final_match_score * 100)

                                return (
                                    <div
                                        key={m.id}
                                        className="bg-white border border-slate-200 rounded-2xl hover:shadow-md transition-shadow duration-200 overflow-hidden"
                                    >
                                        <div className="p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
                                            <div className="space-y-2">
                                                <div className="flex items-center gap-2 flex-wrap">
                                                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${pct >= 70 ? 'bg-emerald-500/10 text-emerald-800 border border-emerald-500/20' :
                                                            pct >= 50 ? 'bg-amber-500/10 text-amber-800 border border-amber-500/20' :
                                                                'bg-slate-500/10 text-slate-800 border border-slate-500/10'
                                                        }`}>
                                                        {m.match_label}
                                                    </span>
                                                    <span className="text-[10px] text-slate-400 bg-slate-100 px-2 py-0.5 rounded border border-slate-200/50 font-mono">
                                                        Confidence: {(m.confidence * 100).toFixed(0)}%
                                                    </span>
                                                </div>

                                                <h4 className="font-extrabold text-slate-800 text-sm">
                                                    Job Opportunity Match
                                                </h4>
                                                <p className="text-xs text-slate-550 max-w-xl line-clamp-2 mt-2 leading-relaxed">
                                                    {m.match_explanation}
                                                </p>
                                            </div>

                                            {/* Score Indicator & Toggle button */}
                                            <div className="flex items-center gap-6 flex-shrink-0">
                                                <div className="flex flex-col items-center">
                                                    <span className={`text-2xl font-extrabold ${pct >= 70 ? 'text-emerald-600' : pct >= 50 ? 'text-amber-500' : 'text-slate-500'
                                                        }`}>
                                                        {pct}<span className="text-xs text-slate-400 font-medium">/100</span>
                                                    </span>
                                                    <span className="text-[9px] text-slate-450 font-bold uppercase mt-1">Match Score</span>
                                                </div>

                                                <button
                                                    onClick={() => setExpandedId(isExpanded ? null : m.id)}
                                                    className="bg-slate-50 text-slate-655 hover:bg-slate-100 border border-slate-200 font-semibold text-xs px-4 py-2 rounded-xl transition-all"
                                                >
                                                    {isExpanded ? 'Hide Details' : 'View Alignment'}
                                                </button>
                                            </div>
                                        </div>

                                        {/* Detailed Alignment breakdown panels */}
                                        {isExpanded && (
                                            <div className="px-6 pb-6 border-t border-slate-100 bg-slate-50/30 divide-y divide-slate-100 animate-slideDown">
                                                {/* 1. Skill Overlaps */}
                                                <div className="py-4 grid grid-cols-1 md:grid-cols-2 gap-6 text-xs">
                                                    <div>
                                                        <h5 className="font-bold text-slate-700 mb-2 flex items-center gap-1.5">
                                                            <CheckCircle2 className="w-4 h-4 text-emerald-500" /> Matched Skills Overlaps ({m.matched_skills.length})
                                                        </h5>
                                                        {m.matched_skills.length === 0 ? (
                                                            <p className="text-slate-450 italic">No skills overlap extracted.</p>
                                                        ) : (
                                                            <div className="flex flex-wrap gap-1.5 mt-2">
                                                                {m.matched_skills.map((s: string, idx: number) => (
                                                                    <span key={idx} className="bg-emerald-500/10 text-emerald-800 font-medium px-2 py-0.5 rounded text-[10px]">
                                                                        {s}
                                                                    </span>
                                                                ))}
                                                            </div>
                                                        )}
                                                    </div>

                                                    <div>
                                                        <h5 className="font-bold text-slate-700 mb-2 flex items-center gap-1.5">
                                                            <AlertTriangle className="w-4 h-4 text-amber-500" /> Missing Requirements / Skills ({m.missing_requirements.length})
                                                        </h5>
                                                        {m.missing_requirements.length === 0 ? (
                                                            <p className="text-slate-450 italic">All extracted requirements covered.</p>
                                                        ) : (
                                                            <div className="flex flex-wrap gap-1.5 mt-2">
                                                                {m.missing_requirements.map((s: string, idx: number) => (
                                                                    <span key={idx} className="bg-rose-500/10 text-rose-800 font-medium px-2 py-0.5 rounded text-[10px]">
                                                                        {s}
                                                                    </span>
                                                                ))}
                                                            </div>
                                                        )}
                                                    </div>
                                                </div>

                                                {/* 2. Match Scores details */}
                                                <div className="py-4 text-xs">
                                                    <h5 className="font-bold text-slate-700 mb-2">Weighted Matching Diagnostics</h5>
                                                    <div className="grid grid-cols-3 gap-4 text-center mt-2">
                                                        <div className="p-3 bg-white border border-slate-200 rounded-xl">
                                                            <p className="text-[10px] text-slate-450 font-bold uppercase">Keyword Overlap</p>
                                                            <p className="text-sm font-extrabold text-slate-800 mt-1">{(m.keyword_overlap_score * 100).toFixed(0)}%</p>
                                                        </div>
                                                        <div className="p-3 bg-white border border-slate-200 rounded-xl">
                                                            <p className="text-[10px] text-slate-450 font-bold uppercase">Semantic Embed similarity</p>
                                                            <p className="text-sm font-extrabold text-slate-800 mt-1">{(m.embedding_similarity_score * 100).toFixed(0)}%</p>
                                                        </div>
                                                        <div className="p-3 bg-white border border-slate-200 rounded-xl">
                                                            <p className="text-[10px] text-slate-450 font-bold uppercase">BM25 / SQLite Score</p>
                                                            <p className="text-sm font-extrabold text-slate-800 mt-1">{(m.bm25_score * 10).toFixed(1)} / 10</p>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                )
                            })}
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}
