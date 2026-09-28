export function formatMoney(value: number, currency: string): string {
  try {
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: currency || 'COP',
      maximumFractionDigits: 2,
    }).format(value)
  } catch {
    // The currency code comes from the model and may not be a valid ISO code.
    return `${new Intl.NumberFormat('es-CO').format(value)} ${currency}`.trim()
  }
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat('es-CO', { maximumFractionDigits: 2 }).format(value)
}

/** "2026-09-03" -> "03/09/2026", without Date parsing to avoid timezone shifts. */
export function formatDate(iso: string | null): string {
  if (!iso) return 'Sin dato'
  const [year, month, day] = iso.split('-')
  return year && month && day ? `${day}/${month}/${year}` : iso
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
