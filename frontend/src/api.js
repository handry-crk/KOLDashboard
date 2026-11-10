const BASE = import.meta.env.VITE_API_URL || ''

export const auth = {
  get token() { try { return localStorage.getItem('kol_token') } catch { return null } },
  set(token, user) { try { localStorage.setItem('kol_token', token); localStorage.setItem('kol_user', JSON.stringify(user)) } catch {} },
  user() { try { return JSON.parse(localStorage.getItem('kol_user') || 'null') } catch { return null } },
  clear() { try { localStorage.removeItem('kol_token'); localStorage.removeItem('kol_user') } catch {} },
}

export class ApiError extends Error {}

export async function api(path, { method = 'GET', body, raw } = {}) {
  const headers = {}
  if (auth.token) headers.Authorization = 'Bearer ' + auth.token
  let payload = body
  if (body && !(body instanceof FormData)) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body) }
  const res = await fetch(BASE + path, { method, headers, body: payload })
  if (res.status === 401 && !path.startsWith('/api/auth/login')) { auth.clear(); window.location.href = '/login'; return }
  if (!res.ok) {
    let msg = 'Terjadi kesalahan'
    try { const j = await res.json(); msg = typeof j.detail === 'string' ? j.detail : (j.detail?.[0]?.msg || msg) } catch {}
    throw new ApiError(msg)
  }
  if (raw) return res
  return res.json()
}

export async function download(path, filename) {
  const res = await api(path, { raw: true })
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a'); a.href = url; a.download = filename; a.click()
  setTimeout(() => URL.revokeObjectURL(url), 2000)
}

export async function upload(file) {
  const fd = new FormData(); fd.append('file', file)
  return api('/api/files', { method: 'POST', body: fd })
}

export const fileUrl = (id) => `${BASE}/api/files/${id}?t=${encodeURIComponent(auth.token || '')}`
