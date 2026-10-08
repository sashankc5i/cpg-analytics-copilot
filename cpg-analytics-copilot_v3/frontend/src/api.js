export const tok = { get: () => localStorage.getItem('cpg_tok'), set: t => localStorage.setItem('cpg_tok', t), clear: () => localStorage.removeItem('cpg_tok') }

export async function api(path, { method = 'GET', body, raw = false } = {}) {
  const res = await fetch('/api' + path, { method, headers: { 'Content-Type': 'application/json', ...(tok.get() ? { Authorization: 'Bearer ' + tok.get() } : {}) }, body: body ? JSON.stringify(body) : undefined })
  if (res.status === 401 && !path.startsWith('/auth/login') && !path.startsWith('/shared')) { tok.clear(); window.location.href = '/login'; throw new Error('Session expired') }
  if (!res.ok) {
    let j = {}; try { j = await res.json() } catch { /* ignore */ }
    const e = new Error((j.error || res.statusText) + (j.request_id ? ` (ref ${j.request_id})` : '')); e.status = res.status; throw e
  }
  return raw ? res : res.json()
}

export async function download(path, filename) {
  const res = await api(path, { raw: true }); const blob = await res.blob()
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = filename; a.click(); URL.revokeObjectURL(a.href)
}
