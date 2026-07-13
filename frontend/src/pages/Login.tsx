import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { authApi } from '../lib/api'
import { setUser } from '../lib/auth'
import toast from 'react-hot-toast'
import { Shield, Lock, User, AtSign, Loader2 } from 'lucide-react'

export function Login() {
    const [isRegister, setIsRegister] = useState(false)
    const [username, setUsername] = useState('')
    const [password, setPassword] = useState('')
    const [email, setEmail] = useState('')
    const [loading, setLoading] = useState(false)
    const navigate = useNavigate()

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!username || !password) {
            toast.error('Please enter all required fields')
            return
        }
        setLoading(true)
        try {
            if (isRegister) {
                const res = await authApi.register(username, password)
                setUser(res)
                toast.success(`Welcome to ATS Analyzer, ${username}!`)
            } else {
                const res = await authApi.login(username, password)
                setUser(res)
                toast.success(`Logged in as ${username}.`)
            }
            navigate('/')
        } catch (err: any) {
            console.error(err)
            toast.error(err.response?.data?.detail || 'An error occurred during authentication')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-6 relative overflow-hidden">
            {/* Background Gradients */}
            <div className="absolute top-[-20%] left-[-20%] w-[60%] h-[60%] rounded-full bg-blue-900/10 blur-[120px] pointer-events-none" />
            <div className="absolute bottom-[-20%] right-[-20%] w-[60%] h-[60%] rounded-full bg-violet-900/10 blur-[120px] pointer-events-none" />

            <div className="w-full max-w-md relative z-10">
                <div className="flex flex-col items-center mb-8">
                    <div className="p-3 bg-gradient-to-tr from-blue-600 to-indigo-600 rounded-2xl shadow-lg ring-1 ring-white/10 mb-4 animate-pulse">
                        <Shield className="w-8 h-8 text-white" />
                    </div>
                    <h2 className="text-3xl font-extrabold text-white tracking-tight">ATS Analyzer</h2>
                    <p className="text-sm text-slate-400 mt-2">Privacy-First Local Resume & LinkedIn Job Alignment</p>
                </div>

                {/* Card */}
                <div className="bg-slate-900/80 backdrop-blur-xl border border-white/5 rounded-3xl p-8 shadow-2xl relative overflow-hidden">
                    <div className="absolute top-0 left-0 w-full h-[2px] bg-gradient-to-r from-transparent via-blue-500 to-transparent opacity-50" />

                    <h3 className="text-xl font-bold text-white mb-6 text-center">
                        {isRegister ? 'Create Local Account' : 'Sign In'}
                    </h3>

                    <form onSubmit={handleSubmit} className="space-y-5">
                        <div>
                            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Username</label>
                            <div className="relative">
                                <span className="absolute inset-y-0 left-0 flex items-center pl-3.5 pointer-events-none">
                                    <User className="w-4 h-4 text-slate-500" />
                                </span>
                                <input
                                    type="text"
                                    value={username}
                                    onChange={(e) => setUsername(e.target.value)}
                                    className="w-full bg-slate-950/50 border border-slate-800 rounded-xl py-3 pl-10 pr-4 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all font-medium"
                                    placeholder="e.g. john_doe"
                                    required
                                />
                            </div>
                        </div>

                        {isRegister && (
                            <div>
                                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Email Address (Optional)</label>
                                <div className="relative">
                                    <span className="absolute inset-y-0 left-0 flex items-center pl-3.5 pointer-events-none">
                                        <AtSign className="w-4 h-4 text-slate-500" />
                                    </span>
                                    <input
                                        type="email"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        className="w-full bg-slate-950/50 border border-slate-800 rounded-xl py-3 pl-10 pr-4 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all font-medium"
                                        placeholder="e.g. john@local.test"
                                    />
                                </div>
                            </div>
                        )}

                        <div>
                            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Password</label>
                            <div className="relative">
                                <span className="absolute inset-y-0 left-0 flex items-center pl-3.5 pointer-events-none">
                                    <Lock className="w-4 h-4 text-slate-500" />
                                </span>
                                <input
                                    type="password"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    className="w-full bg-slate-950/50 border border-slate-800 rounded-xl py-3 pl-10 pr-4 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all font-medium"
                                    placeholder="••••••••"
                                    required
                                />
                            </div>
                        </div>

                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-medium text-sm rounded-xl py-3 shadow-lg shadow-blue-500/10 hover:shadow-blue-500/20 focus:outline-none focus:ring-2 focus:ring-blue-500/50 active:scale-[0.98] transition-all flex items-center justify-center gap-2 mt-2"
                        >
                            {loading ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                                <span>{isRegister ? 'Register' : 'Access Analyzer'}</span>
                            )}
                        </button>
                    </form>

                    <div className="mt-6 text-center">
                        <button
                            onClick={() => { setIsRegister(!isRegister); setUsername(''); setPassword(''); setEmail('') }}
                            className="text-xs text-slate-400 hover:text-white transition-colors"
                        >
                            {isRegister ? 'Already have an account? Sign In' : "Don't have an account yet? Create one"}
                        </button>
                    </div>
                </div>

                <div className="text-center mt-6">
                    <p className="text-[10px] text-slate-600 uppercase tracking-widest leading-relaxed">
                        All profile parsing, score alignments, and indexing take place 100% locally.
                    </p>
                </div>
            </div>
        </div>
    )
}
