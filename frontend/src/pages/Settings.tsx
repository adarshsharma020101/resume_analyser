import { useEffect, useState } from 'react'
import { settingsApi } from '../lib/api'
import { Settings as SettingsIcon, Sliders, ShieldCheck, Key, RefreshCw, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'

export function Settings() {
    const [weights, setWeights] = useState<any>(null)
    const [loading, setLoading] = useState(true)

    const fetchWeights = async () => {
        try {
            const w = await settingsApi.getScoringWeights()
            setWeights(w)
        } catch (err) {
            console.error(err)
            toast.error('Failed to load scoring weights from config')
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchWeights()
    }, [])

    return (
        <div className="space-y-8">
            <div>
                <h2 className="text-2xl font-extrabold text-slate-800 tracking-tight flex items-center gap-2">
                    <SettingsIcon className="w-6 h-6 text-slate-600" /> Core Environment Settings
                </h2>
                <p className="text-xs text-slate-500 mt-1">
                    Inspect local system parameters, deterministic scoring weights, and credential tokens. Both UI and DB run on-device.
                </p>
            </div>

            {loading ? (
                <div className="flex justify-center py-12">
                    <Loader2 className="w-8 h-8 animate-spin text-slate-400" />
                </div>
            ) : (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    {/* Weights details */}
                    <div className="lg:col-span-2 space-y-6">
                        <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm">
                            <h3 className="font-bold text-slate-700 mb-2 flex items-center gap-1.5">
                                <Sliders className="w-4.5 h-4.5 text-slate-500" /> Scoring Weights Configuration
                            </h3>
                            <p className="text-xs text-slate-500 mb-6">
                                Scoring is strictly code-based (not computed via open LLM hallucinations). Values sum to {weights?.total || 100}%. Update these weights in your backend <code>.env</code> file.
                            </p>

                            {weights && (
                                <div className="space-y-4">
                                    {Object.entries(weights)
                                        .filter(([key]) => key !== 'total')
                                        .map(([key, value]: [string, any]) => {
                                            const pct = Math.round((value / weights.total) * 100)
                                            return (
                                                <div key={key} className="space-y-1.5">
                                                    <div className="flex justify-between items-center text-xs">
                                                        <span className="font-bold text-slate-750 uppercase tracking-wide">
                                                            {key.replace('_', ' ')}
                                                        </span>
                                                        <span className="font-semibold text-slate-500">{value} pts ({pct}%)</span>
                                                    </div>
                                                    <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                                                        <div
                                                            className="bg-indigo-600 h-full rounded-full transition-all duration-500"
                                                            style={{ width: `${pct}%` }}
                                                        />
                                                    </div>
                                                </div>
                                            )
                                        })}
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Local Service Status */}
                    <div className="space-y-6">
                        <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm">
                            <h3 className="font-bold text-slate-700 mb-4 flex items-center gap-1.5">
                                <ShieldCheck className="w-4.5 h-4.5 text-emerald-600" /> Environment Health
                            </h3>
                            <ul className="text-xs text-slate-600 space-y-3">
                                <li className="flex justify-between">
                                    <span className="text-slate-400">Database Engine:</span>
                                    <span className="font-semibold text-slate-800">SQLite (Local File)</span>
                                </li>
                                <li className="flex justify-between">
                                    <span className="text-slate-400">Semantic Vector Store:</span>
                                    <span className="font-semibold text-slate-800">ChromaDB (Isolated)</span>
                                </li>
                                <li className="flex justify-between">
                                    <span className="text-slate-400">AI LLM Pipeline:</span>
                                    <span className="font-semibold text-slate-800">Ollama (Self-Hosted)</span>
                                </li>
                            </ul>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
