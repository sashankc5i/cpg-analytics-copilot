export const tok = { get: () => localStorage.getItem('cpg_tok'), set: t => localStorage.setItem('cpg_tok', t), clear: () => localStorage.removeItem('cpg_tok') }

function errorMessage(value, fallback) {
  if (typeof value === 'string' && value.trim()) return value
  if (Array.isArray(value)) {
    const messages = value.map(item => {
      if (typeof item === 'string') return item
      if (item && typeof item === 'object') {
        const location = Array.isArray(item.loc) ? item.loc.slice(1).join('.') : ''
        return [location, item.msg || item.message].filter(Boolean).join(': ')
      }
      return ''
    }).filter(Boolean)
    if (messages.length) return messages.join('; ')
  }
  if (value && typeof value === 'object') {
    const nested = value.message ?? value.detail ?? value.error_description ?? value.error
    if (nested !== undefined && nested !== value) return errorMessage(nested, fallback)
    try { return JSON.stringify(value) } catch { /* use fallback */ }
  }
  return fallback
}

export async function api(path, { method = 'GET', body, raw = false } = {}) {
  const multipart = typeof FormData !== 'undefined' && body instanceof FormData
  const res = await fetch('/api' + path, { method, headers: { ...(!multipart ? { 'Content-Type': 'application/json' } : {}), ...(tok.get() ? { Authorization: 'Bearer ' + tok.get() } : {}) }, body: body ? (multipart ? body : JSON.stringify(body)) : undefined })
  if (res.status === 401 && !path.startsWith('/auth/login') && !path.startsWith('/shared')) { tok.clear(); window.location.href = '/login'; throw new Error('Session expired') }
  if (!res.ok) {
    let j = {}; try { j = await res.json() } catch { /* ignore */ }
    const message = errorMessage(j.error ?? j.detail, res.statusText || `Request failed (${res.status})`)
    const e = new Error(message + (j.request_id ? ` (ref ${j.request_id})` : '')); e.status = res.status; throw e
  }
  return raw ? res : res.json()
}

export async function adminApi(path, options = {}) {
  const { method = 'GET', body, raw = false } = options
  const res = await fetch(path, { method, headers: { 'Content-Type': 'application/json', ...(tok.get() ? { Authorization: 'Bearer ' + tok.get() } : {}) }, body: body ? JSON.stringify(body) : undefined })
  if (res.status === 401) { tok.clear(); window.location.href = '/login'; throw new Error('Session expired') }
  if (!res.ok) {
    let j = {}; try { j = await res.json() } catch { /* ignore */ }
    const message = errorMessage(j.error ?? j.detail, res.statusText || `Request failed (${res.status})`)
    const e = new Error(message + (j.request_id ? ` (ref ${j.request_id})` : '')); e.status = res.status; throw e
  }
  return raw ? res : res.json()
}

export async function download(path, filename) {
  const res = await api(path, { raw: true }); const blob = await res.blob()
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = filename; a.click(); URL.revokeObjectURL(a.href)
}
