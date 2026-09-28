import { useEffect, useRef, useState } from 'react'
import { ApiError, checkHealth, uploadInvoice, validateFile } from './api'
import type { UploadResponse } from './api'
import { History } from './components/History'
import type { HistoryEntry } from './components/History'
import { InvoiceResult } from './components/InvoiceResult'
import { UploadZone } from './components/UploadZone'

type Health = 'checking' | 'up' | 'down'

interface Failure {
  message: string
  detail: string
}

const HEALTH_LABEL: Record<Health, string> = {
  checking: 'Comprobando servicio',
  up: 'Servicio disponible',
  down: 'Servicio no disponible',
}

const HEALTH_DOT: Record<Health, string> = {
  checking: 'bg-slate-400',
  up: 'bg-emerald-500',
  down: 'bg-red-500',
}

export default function App() {
  const [health, setHealth] = useState<Health>('checking')
  const [file, setFile] = useState<File | null>(null)
  const [register, setRegister] = useState(true)
  const [loading, setLoading] = useState(false)
  const [seconds, setSeconds] = useState(0)
  const [failure, setFailure] = useState<Failure | null>(null)
  const [result, setResult] = useState<UploadResponse | null>(null)
  const [history, setHistory] = useState<HistoryEntry[]>([])
  const [activeId, setActiveId] = useState<number | null>(null)
  const nextId = useRef(1)

  useEffect(() => {
    let cancelled = false
    checkHealth().then((ok) => {
      if (!cancelled) setHealth(ok ? 'up' : 'down')
    })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!loading) return
    const started = Date.now()
    const timer = window.setInterval(() => {
      setSeconds(Math.floor((Date.now() - started) / 1000))
    }, 1000)
    return () => window.clearInterval(timer)
  }, [loading])

  function selectFile(candidate: File) {
    const problem = validateFile(candidate)
    if (problem) {
      setFile(null)
      setFailure({ message: problem, detail: '' })
      return
    }
    setFailure(null)
    setFile(candidate)
  }

  async function submit() {
    if (!file || loading) return
    setLoading(true)
    setSeconds(0)
    setFailure(null)
    setResult(null)
    setActiveId(null)

    try {
      const response = await uploadInvoice(file, register)
      const entry: HistoryEntry = {
        id: nextId.current++,
        time: new Date().toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' }),
        result: response,
      }
      setResult(response)
      setActiveId(entry.id)
      setHistory((previous) => [entry, ...previous])
      setFile(null)
    } catch (error) {
      if (error instanceof ApiError) {
        setFailure({ message: error.message, detail: error.detail })
      } else {
        setFailure({ message: 'Ocurrió un error inesperado. Inténtalo de nuevo.', detail: '' })
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-4xl flex-col gap-8 px-4 py-10 sm:px-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">Invoice Register</h1>
          <p className="mt-1 text-slate-600 dark:text-slate-400">
            Sube una factura en PDF y sus datos se registran en Google Sheets.
          </p>
        </div>
        <span
          role="status"
          className="flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium dark:border-slate-800 dark:bg-slate-900"
        >
          <span className={`h-2 w-2 rounded-full ${HEALTH_DOT[health]}`} aria-hidden="true" />
          {HEALTH_LABEL[health]}
        </span>
      </header>

      <main className="flex flex-col gap-8">
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <UploadZone
            file={file}
            disabled={loading}
            onSelect={selectFile}
            onClear={() => setFile(null)}
          />

          <div className="mt-5 flex flex-wrap items-center justify-between gap-4">
            <label className="flex cursor-pointer items-start gap-3 text-sm">
              <input
                type="checkbox"
                checked={register}
                disabled={loading}
                onChange={(event) => setRegister(event.target.checked)}
                className="mt-0.5 h-4 w-4 rounded border-slate-300 accent-blue-600"
              />
              <span>
                <span className="font-medium">Registrar en Google Sheets</span>
                <span className="block text-slate-500 dark:text-slate-400">
                  Desmárcalo para revisar los datos sin escribir en la hoja.
                </span>
              </span>
            </label>

            <button
              type="button"
              onClick={submit}
              disabled={!file || loading}
              className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-500 dark:disabled:bg-slate-800 dark:disabled:text-slate-500"
            >
              {loading ? 'Procesando' : register ? 'Procesar y registrar' : 'Solo extraer datos'}
            </button>
          </div>
        </section>

        {loading && (
          <div
            role="status"
            className="flex items-center gap-4 rounded-xl border border-blue-200 bg-blue-50 px-5 py-4 text-sm text-blue-900 dark:border-blue-900 dark:bg-blue-950/40 dark:text-blue-100"
          >
            <span
              className="h-5 w-5 shrink-0 animate-spin rounded-full border-2 border-blue-600 border-t-transparent"
              aria-hidden="true"
            />
            <span>
              <span className="font-medium">Leyendo la factura. Llevamos {seconds} s.</span>
              <span className="block text-blue-800/80 dark:text-blue-200/80">
                Un PDF con texto tarda unos segundos. Un escaneo puede tardar cerca de un minuto.
              </span>
            </span>
          </div>
        )}

        {failure && (
          <div
            role="alert"
            className="rounded-xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-900 dark:border-red-900 dark:bg-red-950/40 dark:text-red-100"
          >
            <p className="font-medium">{failure.message}</p>
            {failure.detail && (
              <p className="mt-1 break-words text-red-800/80 dark:text-red-200/80">
                Detalle: {failure.detail}
              </p>
            )}
          </div>
        )}

        {result && <InvoiceResult result={result} />}

        <History
          entries={history}
          activeId={activeId}
          onOpen={(entry) => {
            setResult(entry.result)
            setActiveId(entry.id)
            setFailure(null)
          }}
        />
      </main>

      <footer className="mt-auto pt-6 text-center text-xs text-slate-500 dark:text-slate-500">
        Los datos se extraen con un modelo de lenguaje. Verifica los valores antes de usarlos en
        contabilidad.
      </footer>
    </div>
  )
}
