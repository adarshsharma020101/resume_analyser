import { useEffect, useState } from 'react'
import { jobsApi } from '../lib/api'
import { DropZone } from '../components/ui/DropZone'
import { Briefcase, AlertCircle, FileText, CheckCircle2, Loader2, Save } from 'lucide-react'
import toast from 'react-hot-toast'

export function JobDescription() {
    const [jds, setJds] = useState<any[]>([])
    const [rawText, setRawText] = useState('')
    const [title, setTitle] = useState('')
    const [company, setCompany] = useState('')
    const [submittingText, setSubmittingText] = useState(false)
    const [uploading, setUploading] = useState(false)
    const [loading, setLoading] = useState(true)

    const fetchJds = async () => {
        try {
            const list = await jobsApi.listDescriptions()
            setJds(list || [])
        } catch (err) {
            console.error(err)
            toast.error('Failed to load job descriptions')
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchJds()
    }, [])

    const handlePasteSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!rawText.trim()) {
            toast.error('Please enter the job description text')
            return
        }
        setSubmittingText(true)
        const tid = toast.loading('Extracting job keywords and requirements...')
        try {
            const res = await jobsApi.addDescription({
                raw_text: rawText,
                title: title || undefined,
                company: company || undefined,
            })
            toast.success(`Job description for "${res.title}" saved!`, { id: tid })
            setRawText('')
            setTitle('')
            setCompany('')
            fetchJds()
        } catch (err: any) {
            console.error(err)
            toast.error(err.response?.data?.detail || 'Failed to save job description', { id: tid })
        } finally {
            setSubmittingText(false)
        }
    }

    const handleUploadJDFile = async (file: File) => {
        setUploading(true)
        const tid = toast.loading(`Uploading & parsing ${file.name}...`)
        try {
            const res = await jobsApi.uploadDescription(file)
            toast.success(`Uploaded description for "${res.title}" successfully!`, { id: tid })
            fetchJds()
        } catch (err: any) {
            console.error(err)
            toast.error(err.response?.data?.detail || 'Failed to ingest file description', { id: tid })
        } finally {
            setUploading(false)
        }
    }

    return (
        <div className="space-y-8">
            <div>
                <h2 className="text-2xl font-extrabold text-slate-800 tracking-tight flex items-center gap-2">
                    <Briefcase className="w-6 h-6 text-indigo-500" /> Target Job Description
                </h2>
                <p className="text-xs text-slate-500 mt-1">
                    Specify a target job description: either write/paste details or upload files to evaluate scoring matches.
                </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Forms column */}
                <div className="lg:col-span-2 space-y-6">
                    {/* Paste description */}
                    <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm">
                        <h3 className="font-bold text-slate-700 mb-4 flex items-center gap-1.5">
                            <Save className="w-4 h-4 text-indigo-550" /> Paste Job Text
                        </h3>

                        <form onSubmit={handlePasteSubmit} className="space-y-4">
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs font-semibold uppercase text-slate-400 mb-2">Job Title (Optional)</label>
                                    <input
                                        type="text"
                                        value={title}
                                        onChange={(e) => setTitle(e.target.value)}
                                        className="w-full bg-slate-50 border border-slate-250 rounded-xl py-2.5 px-4 text-xs font-medium text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                                        placeholder="e.g. Staff Backend Engineer"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs font-semibold uppercase text-slate-400 mb-2">Company (Optional)</label>
                                    <input
                                        type="text"
                                        value={company}
                                        onChange={(e) => setCompany(e.target.value)}
                                        className="w-full bg-slate-50 border border-slate-250 rounded-xl py-2.5 px-4 text-xs font-medium text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                                        placeholder="e.g. Google DeepMind"
                                    />
                                </div>
                            </div>

                            <div>
                                <label className="block text-xs font-semibold uppercase text-slate-400 mb-2">Job Description Text</label>
                                <textarea
                                    value={rawText}
                                    onChange={(e) => setRawText(e.target.value)}
                                    rows={8}
                                    className="w-full bg-slate-50 border border-slate-250 rounded-xl py-2.5 px-4 text-xs font-medium text-slate-850 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all font-mono"
                                    placeholder="Paste requirements, skills, role duties here..."
                                    required
                                />
                            </div>

                            <button
                                type="submit"
                                disabled={submittingText}
                                className="bg-slate-900 text-white hover:bg-slate-850 font-semibold text-xs px-5 py-2.5 rounded-xl transition-all disabled:opacity-50 flex items-center gap-2"
                            >
                                {submittingText ? (
                                    <>
                                        <Loader2 className="w-3.5 h-3.5 animate-spin" /> Extrapolating agents...
                                    </>
                                ) : 'Save Job Description'}
                            </button>
                        </form>
                    </div>

                    {/* Upload Job File */}
                    <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm">
                        <h3 className="font-bold text-slate-700 mb-4 flex items-center gap-1.5">
                            <FileText className="w-4 h-4 text-indigo-550" /> Upload Job File
                        </h3>
                        <DropZone
                            onFile={handleUploadJDFile}
                            disabled={uploading}
                            accept={{
                                'application/pdf': ['.pdf'],
                                'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
                                'text/plain': ['.txt'],
                            }}
                            label="Select job file"
                            hint="PDF, DOCX, or TXT"
                        />
                        {uploading && (
                            <div className="flex items-center justify-center gap-2 text-xs text-slate-500 mt-4 animate-pulse">
                                <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                                <span>Running local document intake pipeline...</span>
                            </div>
                        )}
                    </div>
                </div>

                {/* Existing Target Jobs list */}
                <div className="space-y-6">
                    <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm">
                        <h3 className="font-bold text-slate-700 mb-4">Saved Descriptions</h3>
                        {loading ? (
                            <div className="flex justify-center py-4">
                                <Loader2 className="w-5 h-5 animate-spin text-slate-400" />
                            </div>
                        ) : jds.length === 0 ? (
                            <p className="text-xs text-slate-450 text-center py-4">No saved descriptions yet.</p>
                        ) : (
                            <div className="space-y-3.5 divide-y divide-slate-100 max-h-[400px] overflow-y-auto pr-1">
                                {jds.map((j) => (
                                    <div key={j.id} className="pt-3 first:pt-0 text-xs">
                                        <p className="font-bold text-slate-850 truncate">{j.title || 'Untitled'}</p>
                                        <p className="text-slate-500 mt-0.5">{j.company || 'Unknown Company'}</p>
                                        <p className="text-[10px] text-slate-400 mt-1">Saved: {new Date(j.created_at).toLocaleDateString()}</p>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    )
}
