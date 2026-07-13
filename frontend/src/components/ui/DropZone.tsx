import { useDropzone } from 'react-dropzone'
import { UploadCloud } from 'lucide-react'
import clsx from 'clsx'

interface Props {
  onFile: (f: File) => void
  accept?: Record<string, string[]>
  label?: string
  hint?: string
  disabled?: boolean
}

export function DropZone({ onFile, accept, label = 'Drop file here', hint, disabled }: Props) {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: (files) => files[0] && onFile(files[0]),
    accept,
    multiple: false,
    disabled,
  })
  return (
    <div
      {...getRootProps()}
      className={clsx(
        'border-2 border-dashed rounded-xl p-8 flex flex-col items-center gap-3 cursor-pointer transition-colors',
        isDragActive ? 'border-brand-500 bg-brand-50' : 'border-gray-300 hover:border-brand-400 hover:bg-gray-50',
        disabled && 'opacity-50 cursor-not-allowed',
      )}
    >
      <input {...getInputProps()} />
      <UploadCloud className="w-10 h-10 text-gray-400" />
      <p className="font-medium text-gray-700">{isDragActive ? 'Drop it!' : label}</p>
      {hint && <p className="text-xs text-gray-500 text-center">{hint}</p>}
    </div>
  )
}
