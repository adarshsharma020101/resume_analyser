import { useEffect, useState } from 'react'
import { DropZone } from '../components/ui/DropZone'
import { documentsApi } from '../lib/api'
import { FileText, Trash2, AlertCircle, CheckCircle, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'

export function UploadResume() {
    const [resumes, setResumes] = useState<any[]>([])
    const [uploading, setUploading] = useState(false)
    const [loading, setLoading] = useState(true)

    const fetchResumes = async () => {
        try {
            const docs = await documentsApi.list('resume')
            setResumes(docs || [])
        } catch (err: any) {
            console.error(err)
            toast.error('Failed to load resumes')
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchResumes()
    }, [])

    const handleUploadFile = async (file: File) => {
        setUploading(true)
        const tid = toast.loading(`Uploading & parsing ${file.name}...`)
        try {
            const res = await documentsApi.uploadResume(file)
            toast.success(`${file.name} uploaded successfully!`, { id: tid })
            if (res.parsing_warnings && res.parsing_warnings.length > 0) {
                toast.error(`Completed with style risks: ${res.parsing_warnings.join(', ')}`, { duration: 6000 })
            }
            fetchResumes()
        } catch (err: any) {
            console.error(err)
            toast.error(err.response?.data?.detail || 'Failed to upload/parse resume', { id: tid })
        } finally {
            setUploading(false)
        }
    }

    const handleDelete = async (id: string) => {
        if (!confirm('Are you sure you want to delete this resume?')) return
        try {
            await documentsApi.delete(id)
            toast.success('Resume deleted')
            fetchResumes()
        } catch (err: any) {
            console.error(err)
            toast.error('Failed to delete resume')
        }
    }

    return (
        <div className="space-y-8">
            <div>
                <h2 className="text-2xl font-extrabold text-slate-800 tracking-tight">Upload Resume</h2>
                <p className="text-xs text-slate-500 mt-1">
                    Supports PDF, DOCX, or plain text formats. Submissions are processed completely and securely on this local machine.
                </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Upload Form */}
                <div className="lg:col-span-2 space-y-6">
                    <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm">
                        <h3 className="font-bold text-slate-700 mb-4">Click or Drag Resume</h3>
                        <DropZone
                            onFile={handleUploadFile}
                            disabled={uploading}
                            accept={{
                                'application/pdf': ['.pdf'],
                                'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
                                'text/plain': ['.txt'],
                            }}
                            label="Select your resume"
                            hint="PDF, DOCX, or TXT (Max 5MB)"
                        />
                        {uploading && (
                            <div className="flex items-center justify-center gap-2 text-xs text-slate-500 mt-4 animate-pulse">
                                <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                                <span>Running local document extraction agents... This may take a moment.</span>
                            </div>
                        )}
                    </div>
                </div>

                {/* Action / Disclaimer Panel */}
                <div className="space-y-6">
                    <div className="bg-amber-50/60 border border-amber-500/10 rounded-2xl p-6 text-xs text-amber-800 space-y-2">
                        <h4 className="font-bold flex items-center gap-1.5"><AlertCircle className="w-4 h-4 text-amber-600" /> ATS Compatibility Notice</h4>
                        <p className="leading-relaxed">
                            We process formatting and section structures using local libraries. Please note:
                        </p>
                        <ul className="list-disc pl-4 space-y-1.5 mt-2">
                            <li>ATS Readiness is an estimate. Actual corporate ATS systems use proprietary keyword parsers.</li>
                            <li>Always check warnings for overlapping text columns, complex tables, or excessive imagery.</li>
                        </ul>
                    </div>
                </div>
            </div>

            {/* Uploaded Documents List */}
            <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm">
                <h3 className="font-bold text-slate-700 mb-4 flex items-center gap-2">
                    <FileText className="w-4 h-4 text-slate-500" /> Uploaded Resumes
                </h3>

                {loading ? (
                    <div className="flex items-center justify-center h-20">
                        <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
                    </div>
                ) : resumes.length === 0 ? (
                    <div className="text-center py-8 border border-dashed border-slate-200 rounded-2xl text-xs text-slate-500">
                        No resume files uploaded yet.
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {resumes.map((d: any) => (
                            <div key={d.id} className="p-4 rounded-xl border border-slate-200 flex justify-between items-center text-xs bg-slate-50/40 hover:bg-slate-50 transition-colors">
                                <div className="flex items-start gap-3">
                                    <div className="p-2 bg-blue-50 text-blue-600 rounded-lg">
                                        <FileText className="w-4 h-4" />
                                    </div>
                                    <div>
                                        <p className="font-bold text-slate-700 truncate max-w-[200px]" title={d.filename}>
                                            {d.filename}
                                        </p>
                                        <p className="text-slate-400 mt-1 flex items-center gap-1">
                                            {d.parsing_status === 'completed' ? (
                                                <>
                                                    <CheckCircle className="w-3.5 h-3.5 text-emerald-500" /> Completed
                                                </>
                                            ) : d.parsing_status === 'failed' ? (
                                                <>
                                                    <AlertCircle className="w-3.5 h-3.5 text-rose-500" /> Failed
                                                </>
                                            ) : (
                                                <>
                                                    <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-500" /> In Progress
                                                </>
                                            )}
                                            <span className="text-[10px]">•</span>
                                            <span>{(d.file_size_bytes / 1024).toFixed(1)} KB</span>
                                        </p>
                                    </div>
                                </div>
                                <button
                                    onClick={() => handleDelete(d.id)}
                                    className="p-2 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-rose-50 transition-all"
                                    aria-label="Delete resume"
                                >
                                    <Trash2 className="w-4 h-4" />
                                </button>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    )
}
