const id = new Intl.NumberFormat('id-ID')
export const num = (x) => (x === null || x === undefined || Number.isNaN(x) ? '–' : id.format(Math.round(x)))
export const rp = (x) => (x === null || x === undefined ? '–' : 'Rp' + id.format(Math.round(x)))
export const rpShort = (x) => {
  if (x === null || x === undefined) return '–'
  const a = Math.abs(x)
  if (a >= 1e9) return 'Rp' + (x / 1e9).toLocaleString('id-ID', { maximumFractionDigits: 1 }) + ' M'
  if (a >= 1e6) return 'Rp' + (x / 1e6).toLocaleString('id-ID', { maximumFractionDigits: 1 }) + ' jt'
  if (a >= 1e3) return 'Rp' + (x / 1e3).toLocaleString('id-ID', { maximumFractionDigits: 0 }) + ' rb'
  return 'Rp' + id.format(Math.round(x))
}
export const short = (x) => {
  if (x === null || x === undefined) return '–'
  const a = Math.abs(x)
  if (a >= 1e6) return (x / 1e6).toLocaleString('id-ID', { maximumFractionDigits: 1 }) + ' jt'
  if (a >= 1e3) return (x / 1e3).toLocaleString('id-ID', { maximumFractionDigits: 0 }) + ' rb'
  return id.format(Math.round(x))
}
export const pct = (x, d = 1) => (x === null || x === undefined ? '–' : (x * 100).toLocaleString('id-ID', { maximumFractionDigits: d, minimumFractionDigits: d }) + '%')
export const times = (x) => (x === null || x === undefined ? '–' : x.toLocaleString('id-ID', { maximumFractionDigits: 2, minimumFractionDigits: 1 }) + '×')
export const date = (s) => (s ? new Date(s.length <= 10 ? s + 'T00:00:00' : s).toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' }) : '–')
export const dateTime = (s) => (s ? new Date(s).toLocaleString('id-ID', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : '–')
export const thisMonth = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}` }
export const todayISO = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}` }
export const monthLabel = (m) => { if (!m) return ''; const [y, mo] = m.split('-'); return new Date(+y, +mo - 1, 1).toLocaleDateString('id-ID', { month: 'long', year: 'numeric' }) }
export const shiftMonth = (m, n) => { const [y, mo] = m.split('-').map(Number); const d = new Date(y, mo - 1 + n, 1); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}` }
