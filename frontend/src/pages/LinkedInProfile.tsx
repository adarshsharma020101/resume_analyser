import { useEffect, useState } from 'react'
import { documentsApi } from '../lib/api'
import { DropZone } from '../components/ui/DropZone'
import { Linkedin, AlertCircle, Info, ShieldCheck, CheckCircle2, Loader2, Link2, Trash2 } from 'lucide-react'
import toast from 'react-hot-toast'

export function LinkedInProfile() {
    const [linkedinUrl, setLinkedinUrl] = useState('')
    const [linkedinId, setLinkedinId] = useState('')
    const [uploading, setUploading] = useState(false)
    const [savingUrl, setSavingUrl] = useState(false)
    const [profileDoc, setProfileDoc] = useState<any>(null)
    const [loading, setLoading] = useState(true)

    const fetchProfile = async () => {
        try {
            const docs = await documentsApi.list()
            const li = docs.find((d: any) => d.doc_type === 'linkedin_profile' || d.doc_type === 'linkedin_export' || d.doc_type === 'linkedin_pdf')
            setProfileDoc(li || null)
        } catch (err) {
            console.error(err)
            toast.error('Failed to load profile list')
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchProfile()
    }, [])

    const handleRegisterUrl = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!linkedinUrl && !linkedinId) {
            toast.error('Please submit either a LinkedIn URL or ID')
            return
        }
        setSavingUrl(true)
        try {
            const res = await documentsApi.addLinkedInIdentifier(linkedinUrl || undefined, linkedinId || undefined)
            toast.success(res.message, { duration: 6000 })
        } catch (err: any) {
            console.error(err)
            toast.error(err.response?.data?.detail || 'Failed to save URL identifier')
        } finally {
            setSavingUrl(false)
        }
    }

    const handleUploadProfile = async (file: File) => {
        setUploading(true)
        const tid = toast.loading(`Uploading & parsing LinkedIn ${file.name}...`)
        try {
            await documentsApi.uploadLinkedInProfile(file)
            toast.success(`${file.name} uploaded successfully!`, { id: tid })
            fetchProfile()
        } catch (err: any) {
            console.error(err)
            toast.error(err.response?.data?.detail || 'Failed to ingest LinkedIn profile', { id: tid })
        } finally {
            setUploading(false)
        }
    }

    const handleDeleteProfile = async () => {
        if (!confirm('Are you sure you want to delete this LinkedIn profile document?')) return
        try {
            await documentsApi.delete(profileDoc.id)
            toast.success('LinkedIn profile data deleted')
            setProfileDoc(null)
        } catch (err) {
            console.error(err)
            toast.error('Failed to delete profile')
        }
    }

    return (
        <div className="space-y-8">
            <div>
                <h2 className="text-2xl font-extrabold text-slate-800 tracking-tight flex items-center gap-2">
                    <Linkedin className="w-6 h-6 text-blue-650" /> Add LinkedIn Information
                </h2>
                <p className="text-xs text-slate-500 mt-1">
                    Save your URL structure and upload profile source data for consistency cross-checks.
                </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* URL Reference Form */}
                <div className="lg:col-span-2 space-y-6">
                    <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm">
                        <h3 className="font-bold text-slate-700 mb-2 flex items-center gap-1.5">
                            <Link2 className="w-4 h-4 text-slate-505" /> 1. Connect Account Metadata
                        </h3>
                        <p className="text-xs text-slate-500 mb-4">
                            Saving your URL registers the account link. Note: For privacy and zero-egress reasons, saving a URL alone will NOT scrape metadata.
                        </p>

                        <form onSubmit={handleRegisterUrl} className="space-y-4">
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs font-semibold uppercase text-slate-400 mb-2">LinkedIn URL</label>
                                    <input
                                        type="url"
                                        value={linkedinUrl}
                                        onChange={(e) => setLinkedinUrl(e.target.value)}
                                        className="w-full bg-slate-50 border border-slate-250 rounded-xl py-2.5 px-4 text-xs font-medium text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                                        placeholder="https://linkedin.com/in/username"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs font-semibold uppercase text-slate-400 mb-2">LinkedIn ID Reference</label>
                                    <input
                                        type="text"
                                        value={linkedinId}
                                        onChange={(e) => setLinkedinId(e.target.value)}
                                        className="w-full bg-slate-50 border border-slate-250 rounded-xl py-2.5 px-4 text-xs font-medium text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                                        placeholder="e.g. member-12345"
                                    />
                                </div>
                            </div>

                            <button
                                type="submit"
                                disabled={savingUrl}
                                className="bg-slate-900 text-white hover:bg-slate-850 font-semibold text-xs px-4 py-2.5 rounded-xl transition-all disabled:opacity-50"
                            >
                                {savingUrl ? 'Saving...' : 'Register Connection'}
                            </button>
                        </form>
                    </div>

                    {/* Profile File Upload */}
                    <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm">
                        <h3 className="font-bold text-slate-700 mb-2 flex items-center gap-1.5">
                            <ShieldCheck className="w-4 h-4 text-slate-505" /> 2. Upload Profile Data
                        </h3>
                        <p className="text-xs text-slate-500 mb-4">
                            To support resume-vs-LinkedIn consistency check, upload a PDF export, an official JSON/CSV archive exported from LinkedIn settings, or paste text content.
                        </p>

                        {profileDoc ? (
                            <div className="border border-slate-200 bg-slate-50/50 rounded-2xl p-4 flex justify-between items-center text-xs">
                                <div className="flex items-center gap-3">
                                    <div className="p-2 bg-blue-50 text-blue-600 rounded-xl">
                                        <Linkedin className="w-4 h-4" />
                                    </div>
                                    <div>
                                        <p className="font-bold text-slate-700">{profileDoc.filename}</p>
                                        <p className="text-slate-400 mt-0.5">Format: {profileDoc.doc_type} • Uploaded on {new Date(profileDoc.created_at).toLocaleDateString()}</p>
                                    </div>
                                </div>
                                <button
                                    onClick={handleDeleteProfile}
                                    className="p-2 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-rose-50 transition-all font-bold"
                                >
                                    <Trash2 className="w-4.5 h-4.5" />
                                </button>
                            </div>
                        ) : (
                            <DropZone
                                onFile={handleUploadProfile}
                                disabled={uploading}
                                accept={{
                                    'application/pdf': ['.pdf'],
                                    'application/zip': ['.zip'],
                                    'text/plain': ['.txt'],
                                    'application/json': ['.json'],
                                    'text/csv': ['.csv'],
                                }}
                                label="Select LinkedIn details file"
                                hint="ZIP Export, Profile PDF, JSON, or CSV (Max 10MB)"
                            />
                        )}

                        {uploading && (
                            <div className="flex items-center justify-center gap-2 text-xs text-slate-500 mt-4 animate-pulse">
                                <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                                <span>Parsing profile data offline...</span>
                            </div>
                        )}
                    </div>
                </div>

                {/* Warning Panel */}
                <div className="space-y-6">
                    <div className="bg-blue-50/80 border border-blue-500/10 rounded-2xl p-6 text-xs text-blue-900 space-y-3">
                        <h4 className="font-bold flex items-center gap-1.5"><Info className="w-4 h-4 text-blue-600" /> LinkedIn Privacy Warning</h4>
                        <p className="leading-relaxed">
                            We never perform web scraping or login automation on your behalf. Standard browser integrations that bypass LinkedIn auth violate rules.
                        </p>
                        <p className="leading-relaxed">
                            To obtain data: go to your LinkedIn profile details &rarr; Click <em>More</em> &rarr; <em>Save as PDF</em>, or request an official account archive data export from LinkedIn Settings.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    )
}
