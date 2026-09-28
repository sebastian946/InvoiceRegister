import type { UploadResponse } from '../api'
import { formatMoney } from '../format'

export interface HistoryEntry {
  id: number
  time: string
  result: UploadResponse
}

interface Props {
  entries: HistoryEntry[]
  activeId: number | null
  onOpen: (entry: HistoryEntry) => void
}

export function History({ entries, activeId, onOpen }: Props) {
  if (entries.length === 0) return null

  return (
    <section>
      <h2 className="mb-1 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
        Procesadas en esta sesión
      </h2>
      <p className="mb-3 text-xs text-slate-500 dark:text-slate-400">
        Esta lista se borra al recargar la página. El registro permanente está en la hoja de cálculo.
      </p>
      <ul className="divide-y divide-slate-200 overflow-hidden rounded-xl border border-slate-200 bg-white dark:divide-slate-800 dark:border-slate-800 dark:bg-slate-900">
        {entries.map((entry) => {
          const { invoice, registered } = entry.result
          return (
            <li key={entry.id}>
              <button
                type="button"
                onClick={() => onOpen(entry)}
                className={`flex w-full items-center justify-between gap-4 px-4 py-3 text-left text-sm hover:bg-slate-50 dark:hover:bg-slate-800 ${
                  entry.id === activeId ? 'bg-blue-50 dark:bg-blue-950/40' : ''
                }`}
              >
                <span className="min-w-0">
                  <span className="block truncate font-medium">
                    {invoice.invoice_number || 'Sin número'} · {invoice.supplier_name || 'Proveedor sin dato'}
                  </span>
                  <span className="text-xs text-slate-500 dark:text-slate-400">
                    {entry.time} · {registered ? 'Registrada' : 'Solo extraída'}
                  </span>
                </span>
                <span className="shrink-0 font-medium tabular-nums">
                  {formatMoney(invoice.total, invoice.currency)}
                </span>
              </button>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
