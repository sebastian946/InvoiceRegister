import { useRef, useState } from 'react'
import type { DragEvent } from 'react'
import { formatBytes } from '../format'

interface Props {
  file: File | null
  disabled: boolean
  onSelect: (file: File) => void
  onClear: () => void
}

export function UploadZone({ file, disabled, onSelect, onClear }: Props) {
  const input = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setDragging(false)
    if (disabled) return
    const dropped = event.dataTransfer.files[0]
    if (dropped) onSelect(dropped)
  }

  const border = dragging
    ? 'border-blue-500 bg-blue-50 dark:bg-blue-950/40'
    : 'border-slate-300 hover:border-blue-400 dark:border-slate-700 dark:hover:border-blue-500'

  return (
    <div
      onDragOver={(event) => {
        event.preventDefault()
        if (!disabled) setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      className={`rounded-xl border-2 border-dashed p-8 text-center transition-colors ${border} ${
        disabled ? 'opacity-60' : ''
      }`}
    >
      <input
        ref={input}
        type="file"
        accept="application/pdf,.pdf"
        className="sr-only"
        disabled={disabled}
        onChange={(event) => {
          const picked = event.target.files?.[0]
          if (picked) onSelect(picked)
          event.target.value = ''
        }}
      />

      {file ? (
        <div className="flex flex-col items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-blue-100 text-xs font-bold text-blue-700 dark:bg-blue-900 dark:text-blue-200">
            PDF
          </div>
          <div>
            <p className="break-all font-medium">{file.name}</p>
            <p className="text-sm text-slate-500 dark:text-slate-400">{formatBytes(file.size)}</p>
          </div>
          <button
            type="button"
            onClick={onClear}
            disabled={disabled}
            className="text-sm font-medium text-slate-600 underline-offset-2 hover:underline disabled:cursor-not-allowed dark:text-slate-300"
          >
            Quitar archivo
          </button>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-3">
          <svg
            className="h-10 w-10 text-slate-400"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 16V4m0 0 4 4m-4-4L8 8M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"
            />
          </svg>
          <p className="text-slate-600 dark:text-slate-300">Arrastra aquí la factura en PDF</p>
          <button
            type="button"
            onClick={() => input.current?.click()}
            disabled={disabled}
            className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium shadow-sm hover:bg-slate-50 disabled:cursor-not-allowed dark:border-slate-700 dark:bg-slate-900 dark:hover:bg-slate-800"
          >
            Seleccionar archivo
          </button>
          <p className="text-xs text-slate-500 dark:text-slate-400">Solo PDF, hasta 20 MB</p>
        </div>
      )}
    </div>
  )
}
