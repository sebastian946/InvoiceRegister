// Client for the FastAPI backend. Paths are relative, so the same build works
// behind the Vite dev proxy and when FastAPI serves the built files itself.

export interface InvoiceItem {
  description: string
  quantity: number
  unit_price: number
  total: number
}

export interface Invoice {
  invoice_number: string | null
  issue_date: string | null
  due_date: string | null
  supplier_name: string | null
  supplier_tax_id: string | null
  customer_name: string | null
  currency: string
  subtotal: number
  tax: number
  total: number
  items: InvoiceItem[]
}

export interface UploadResponse {
  invoice: Invoice
  filename: string
  registered: boolean
}

export const MAX_FILE_BYTES = 20 * 1024 * 1024
const REQUEST_TIMEOUT_MS = 240_000
const API_BASE: string = import.meta.env.VITE_API_BASE ?? ''

export class ApiError extends Error {
  readonly status: number
  readonly detail: string

  constructor(status: number, message: string, detail = '') {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

const FRIENDLY: Record<number, string> = {
  400: 'El archivo no tiene nombre. Renómbralo e inténtalo de nuevo.',
  401: 'Tu sesión expiró. Recarga la página para iniciar sesión otra vez.',
  403: 'No tienes permiso para usar este servicio.',
  413: 'El archivo es demasiado grande.',
  415: 'Solo se aceptan archivos PDF.',
  422: 'No se encontró texto legible en el PDF. Revisa que no esté vacío o dañado.',
  502: 'No se pudo procesar la factura. Falló la extracción o el registro en la hoja.',
  504: 'El servidor tardó demasiado en responder. Inténtalo de nuevo.',
}

/** FastAPI sends `detail` as a string, or as a list of validation errors. */
function readDetail(body: unknown): string {
  if (!body || typeof body !== 'object' || !('detail' in body)) return ''
  const detail = (body as { detail: unknown }).detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((entry) => (entry && typeof entry === 'object' && 'msg' in entry ? String(entry.msg) : ''))
      .filter(Boolean)
      .join('. ')
  }
  return ''
}

export function validateFile(file: File): string | null {
  const isPdf = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')
  if (!isPdf) return 'Solo se aceptan archivos PDF.'
  if (file.size === 0) return 'El archivo está vacío.'
  if (file.size > MAX_FILE_BYTES) return 'El archivo supera el límite de 20 MB.'
  return null
}

export async function uploadInvoice(file: File, register: boolean): Promise<UploadResponse> {
  const body = new FormData()
  // Send an explicit PDF type: the backend rejects anything else with 415,
  // and some browsers leave `file.type` empty.
  body.append('file', new File([file], file.name, { type: 'application/pdf' }))

  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)

  let response: Response
  try {
    response = await fetch(`${API_BASE}/invoices/upload?register=${register}`, {
      method: 'POST',
      body,
      signal: controller.signal,
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError(0, 'La extracción tardó demasiado y se canceló. Inténtalo de nuevo.')
    }
    // A failed fetch is either no network, or an expired login redirecting
    // the request to the sign-in page.
    throw new ApiError(0, 'No se pudo conectar con el servidor. Revisa tu conexión o recarga la página.')
  } finally {
    window.clearTimeout(timer)
  }

  const isJson = response.headers.get('content-type')?.includes('application/json') ?? false
  const payload: unknown = isJson ? await response.json().catch(() => null) : null

  if (!response.ok) {
    const fallback = `El servidor respondió con un error (${response.status}).`
    throw new ApiError(response.status, FRIENDLY[response.status] ?? fallback, readDetail(payload))
  }
  if (!payload) {
    throw new ApiError(response.status, 'El servidor devolvió una respuesta inesperada. Recarga la página.')
  }
  return payload as UploadResponse
}

export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/Health`)
    if (!response.ok) return false
    const body = (await response.json()) as { status?: string }
    return body.status === 'healthy'
  } catch {
    return false
  }
}
