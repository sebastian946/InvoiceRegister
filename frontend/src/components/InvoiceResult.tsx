import type { UploadResponse } from '../api'
import { formatDate, formatMoney, formatNumber } from '../format'

// Every value below is rendered as React text. Invoice data is produced by a
// model reading an untrusted PDF, so it must never be injected as HTML.

function Field({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
        {label}
      </dt>
      <dd className="mt-0.5 break-words font-medium">{value || 'Sin dato'}</dd>
    </div>
  )
}

export function InvoiceResult({ result }: { result: UploadResponse }) {
  const { invoice, registered, filename } = result
  const money = (value: number) => formatMoney(value, invoice.currency)

  return (
    <section className="rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-6 py-4 dark:border-slate-800">
        <div>
          <h2 className="text-lg font-semibold">Factura {invoice.invoice_number || 'sin número'}</h2>
          <p className="break-all text-sm text-slate-500 dark:text-slate-400">{filename}</p>
        </div>
        <span
          className={`rounded-full px-3 py-1 text-xs font-semibold ${
            registered
              ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300'
              : 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300'
          }`}
        >
          {registered ? 'Registrada en la hoja' : 'Solo extraída, no registrada'}
        </span>
      </header>

      <dl className="grid grid-cols-1 gap-5 px-6 py-5 sm:grid-cols-2 lg:grid-cols-3">
        <Field label="Proveedor" value={invoice.supplier_name} />
        <Field label="NIT del proveedor" value={invoice.supplier_tax_id} />
        <Field label="Cliente" value={invoice.customer_name} />
        <Field label="Fecha de emisión" value={formatDate(invoice.issue_date)} />
        <Field label="Fecha de vencimiento" value={formatDate(invoice.due_date)} />
        <Field label="Moneda" value={invoice.currency} />
      </dl>

      <div className="overflow-x-auto border-t border-slate-200 dark:border-slate-800">
        <table className="w-full min-w-[32rem] text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-950/50 dark:text-slate-400">
            <tr>
              <th className="px-6 py-3 font-medium">Descripción</th>
              <th className="px-4 py-3 text-right font-medium">Cantidad</th>
              <th className="px-4 py-3 text-right font-medium">Precio unitario</th>
              <th className="px-6 py-3 text-right font-medium">Total</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {invoice.items.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-6 py-6 text-center text-slate-500 dark:text-slate-400">
                  La factura no tiene líneas de detalle.
                </td>
              </tr>
            ) : (
              invoice.items.map((item, index) => (
                <tr key={index}>
                  <td className="px-6 py-3">{item.description}</td>
                  <td className="px-4 py-3 text-right tabular-nums">{formatNumber(item.quantity)}</td>
                  <td className="px-4 py-3 text-right tabular-nums">{money(item.unit_price)}</td>
                  <td className="px-6 py-3 text-right tabular-nums">{money(item.total)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <dl className="ml-auto grid w-full max-w-xs gap-1.5 px-6 py-5 text-sm">
        <div className="flex justify-between">
          <dt className="text-slate-500 dark:text-slate-400">Subtotal</dt>
          <dd className="tabular-nums">{money(invoice.subtotal)}</dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-slate-500 dark:text-slate-400">Impuestos</dt>
          <dd className="tabular-nums">{money(invoice.tax)}</dd>
        </div>
        <div className="mt-1 flex justify-between border-t border-slate-200 pt-2 text-base font-semibold dark:border-slate-800">
          <dt>Total</dt>
          <dd className="tabular-nums">{money(invoice.total)}</dd>
        </div>
      </dl>
    </section>
  )
}
