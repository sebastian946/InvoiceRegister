import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'
import type { ProxyOptions } from 'vite'

// In development the browser talks to Vite, and Vite forwards API calls to the
// backend. Same origin from the browser's point of view, so no CORS.
//
// Where the backend lives is configuration, not code. It comes from the .env
// files in this folder, in this order of priority:
//
//   real environment variables   highest, e.g. $env:BACKEND_URL in PowerShell
//   .env.local                   personal overrides, ignored by git
//   .env.development             shared default: the local backend
//
// BACKEND_URL    where the dev proxy sends API calls.
// BACKEND_TOKEN  identity token for a private Cloud Run backend. Optional.
//
// Neither name starts with VITE_ on purpose: Vite exposes VITE_* variables to
// browser code, and a token must stay in this Node process only.
export default defineConfig(({ mode }) => {
  // The empty prefix loads every variable, not only the VITE_* ones.
  const env = loadEnv(mode, import.meta.dirname, '')
  const backend = (env.BACKEND_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '')
  const token = env.BACKEND_TOKEN?.trim()

  const api: ProxyOptions = {
    target: backend,
    changeOrigin: true,
    // One extraction can take close to a minute, more for scanned PDFs.
    timeout: 300_000,
    proxyTimeout: 300_000,
    ...(token ? { headers: { Authorization: `Bearer ${token}` } } : {}),
  }

  if (mode === 'development') {
    console.log(`  API proxy -> ${backend}${token ? ' (with token)' : ''}`)
  }

  return {
    plugins: [react(), tailwindcss()],
    server: {
      proxy: {
        '/invoices': api,
        '/Health': api,
      },
    },
  }
})
