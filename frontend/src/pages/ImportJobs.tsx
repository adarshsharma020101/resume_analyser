import { useEffect, useState } from 'react'
import { jobsApi } from '../lib/api'
import { DropZone } from '../components/ui/DropZone'
import { Database, AlertTriangle, AlertCircle, RefreshCw, Layers, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'

export function ImportJobs() {
    const [datasets, setDatasets] = useState<any[]>([])
    const [uploading, setUploading] = useState(false)
    const [loading, setLoading] = useState(true)

    const fetchDatasets = async () => {
        try {
            const list = await jobsApi.listDatasets()
            setDatasets(list || [])
        } catch (err) {
            console.error(err)
            toast.error('Failed to load datasets')
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchDatasets()
    }, [])

    const handleUploadDataset = async (file: File) => {
        setUploading(true)
        const tid = toast.loading(`Importing jobs from ${file.name}...`)
        try {
            const res = await jobsApi.importDataset(file)
            toast.success(`Successfully imported dataset "${res.name}" with ${res.job_count} jobs!`, { id: tid, duration: 6000 })
            if (res.import_warnings && res.import_warnings.length > 0) {
                toast.error(`Import warnings: ${res.import_warnings.join(', ')}`, { duration: 6000 })
            }
            fetchDatasets()
        } catch (err: any) {
            console.error(err)
            toast.error(err.response?.data?.detail || 'Failed to import job dataset', { id: tid })
        } finally {
            setUploading(false)
        }
    }

    return (
        <div className="space-y-8">
            <div>
                <h2 className="text-2xl font-extrabold text-slate-800 tracking-tight flex items-center gap-2">
                    <Database className="w-6 h-6 text-purple-650" /> Import Job Dataset
                </h2>
                <p className="text-xs text-slate-500 mt-1">
                    Import batches of local opportunities (in CSV/JSON formats) to trigger bulk alignment score matching.
                </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Upload Side */}
                <div className="lg:col-span-2 space-y-6">
                    <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm">
                        <h3 className="font-bold text-slate-700 mb-4 flex items-center gap-2">
                            <Layers className="w-4 h-4 text-purple-500" /> Ingest CSV / JSON Listings
                        </h3>

                        <DropZone
                            onFile={handleUploadDataset}
                            disabled={uploading}
                            accept={{
                                'text/csv': ['.csv'],
                                'application/json': ['.json'],
                            }}
                            label="Select CSV or JSON file"
                            hint="Import batches of opportunities (CSV columns must include: title, company, description)"
                        />

                        {uploading && (
                            <div className="flex items-center justify-center gap-2 text-xs text-slate-500 mt-4 animate-pulse">
                                <Loader2 className="w-4 h-4 animate-spin text-purple-600" />
                                <span>Validating listings offline...</span>
                            </div>
                        )}
                    </div>
                </div>

                {/* Informational Column */}
                <div className="space-y-6">
                    <div className="bg-purple-50/70 border border-purple-550/10 rounded-2xl p-6 text-xs text-purple-900 space-y-3">
                        <h4 className="font-bold flex items-center gap-1.5"><AlertCircle className="w-4 h-4 text-purple-600" /> Expected Schema</h4>
                        <p className="leading-relaxed">
                            Ensure your CSV file contains core descriptive headers:
                        </p>
                        <div className="bg-slate-900 text-slate-300 p-3 rounded-lg font-mono text-[10px] space-y-1 overflow-x-auto">
                            <div>title,company,location,description</div>
                            <div>"Staff Engineer","Acme Inc","SF","Develop core backend systems..."</div>
                        </div>
                        <p className="leading-relaxed">
                            If matching a JSON file, structure it as a clean list of job objects.
                        </p>
                    </div>
                </div>
            </div>

            {/* Dataset History */}
            <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm">
                <h3 className="font-bold text-slate-700 mb-4 flex items-center gap-2">
                    <RefreshCw className="w-4 h-4 text-slate-500" /> Imported Batches
                </h3>

                {loading ? (
                    <div className="flex justify-center py-6">
                        <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
                    </div>
                ) : datasets.length === 0 ? (
                    <p className="text-xs text-slate-500 text-center py-6">No job datasets imported yet.</p>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {datasets.map((d: any) => (
                            <div key={d.id} className="p-4 rounded-xl border border-slate-200 bg-slate-50/40 flex flex-col justify-between text-xs">
                                <div>
                                    <h4 className="font-bold text-slate-800 truncate" title={d.name}>{d.name}</h4>
                                    <p className="text-slate-400 mt-1">Source: {d.source_file || 'Direct upload'}</p>
                                </div>
                                <div className="flex justify-between items-center mt-3 pt-3 border-t border-slate-100">
                                    <span className="text-[10px] bg-purple-500/10 text-purple-700 font-semibold px-2 py-0.5 rounded-full">
                                        {d.job_count} Jobs Listed
                                    </span>
                                    <span className="text-[10px] text-slate-400">
                                        {new Date(d.created_at).toLocaleDateString()}
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    )
}
