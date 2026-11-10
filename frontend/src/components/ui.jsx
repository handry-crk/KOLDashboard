import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { api, upload, fileUrl } from '../api'
import { monthLabel, shiftMonth } from '../fmt'

export const STATUS_LABEL = {
  SHORTLIST: 'Shortlist', NEGO: 'Negosiasi', WAITING_APPROVAL: 'Menunggu approval', DEAL: 'Deal', BRIEF_SENT: 'Brief terkirim',
  DRAFT_REVIEW: 'Review draft', POSTED: 'Tayang', REPORT_DUE: 'Report terlambat', REPORT_SUBMITTED: 'Report disubmit',
  REPORT_APPROVED: 'Report approved', PAID: 'Lunas', CANCELLED: 'Batal',
}
const STATUS_TONE = {
  SHORTLIST: 'grey', NEGO: 'grey', WAITING_APPROVAL: 'amber', DEAL: 'blue', BRIEF_SENT: 'blue', DRAFT_REVIEW: 'blue', POSTED: 'blue',
  REPORT_DUE: 'red', REPORT_SUBMITTED: 'amber', REPORT_APPROVED: 'green', PAID: 'greenSolid', CANCELLED: 'grey',
}
const TONES = {
  grey: 'bg-neutral-100 text-neutral-600 border-neutral-200', blue: 'bg-sky-50 text-sky-700 border-sky-200',
  amber: 'bg-amber-50 text-amber-800 border-amber-300', red: 'bg-red-50 text-brand border-red-200',
  green: 'bg-green-50 text-ok border-green-200', greenSolid: 'bg-ok text-white border-ok', brand: 'bg-brand text-white border-brand',
}
export function Badge({ tone = 'grey', children, className = '' }) {
  return <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-semibold whitespace-nowrap ${TONES[tone]} ${className}`}>{children}</span>
}
export const StatusBadge = ({ s }) => <Badge tone={STATUS_TONE[s]}>{STATUS_LABEL[s] || s}</Badge>
const TIER_STYLE = { Nano: 'bg-[#FBE3E4] text-brand-deep', Micro: 'bg-[#F4B7BA] text-brand-deep', Macro: 'bg-[#E0555B] text-white', Mega: 'bg-brand-deep text-white' }
export const TierBadge = ({ t }) => <span className={`inline-flex rounded-md px-1.5 py-0.5 text-[11px] font-bold ${TIER_STYLE[t] || ''}`}>{t}</span>
export function EvidenceBadge({ e }) {
  const s = { DIRECT: 'bg-ok text-white border-ok', ASSISTED: 'bg-white text-amber-700 border-warn', EXPOSURE: 'bg-neutral-200 text-neutral-700 border-neutral-300' }[e]
  return <span title={EVIDENCE_HELP[e]} className={`inline-flex rounded-md border px-1.5 py-0.5 text-[10px] font-bold tracking-wide ${s}`}>{e}</span>
}
export const EVIDENCE_HELP = {
  DIRECT: 'Terhitung pasti dari kode unik, link, TikTok Shop, atau TikTok GO',
  ASSISTED: 'Estimasi uplift penjualan outlet vs rata-rata 4 minggu sebelumnya',
  EXPOSURE: 'Views / reach saja',
}
export const GateBadge = ({ g }) => <Badge tone={{ GO: 'green', GWC: 'amber', HOLD: 'red', PENDING: 'grey', SELESAI: 'greenSolid' }[g] || 'grey'}>{g === 'GWC' ? 'GO W/ COND.' : g}</Badge>
export const ReviewBadge = ({ r }) => r ? <Badge tone={{ SCALE: 'greenSolid', KEEP: 'blue', STOP: 'red' }[r]}>{r}</Badge> : <span className="text-xs text-neutral-400">–</span>
export const Dot = ({ c }) => <span className={`inline-block h-2.5 w-2.5 rounded-full ${{ green: 'bg-ok', amber: 'bg-warn', red: 'bg-brand', grey: 'bg-neutral-300' }[c]}`} />

export function Tile({ label, value, sub, tone, onClick, help }) {
  return (
    <button type="button" onClick={onClick} title={help} className={`card p-3 text-left ${onClick ? 'hover:border-brand cursor-pointer' : 'cursor-default'} ${tone === 'red' ? 'border-brand bg-red-50' : ''}`}>
      <div className="text-[11px] font-semibold uppercase tracking-wide text-ink/60">{label}</div>
      <div className={`mt-1 text-xl font-extrabold num ${tone === 'red' ? 'text-brand' : ''}`}>{value}</div>
      {sub && <div className="mt-0.5 text-xs text-ink/60">{sub}</div>}
    </button>
  )
}

export function Section({ title, right, children, className = '' }) {
  return (
    <section className={`card p-4 ${className}`}>
      {(title || right) && <div className="mb-3 flex flex-wrap items-center justify-between gap-2"><h2 className="text-base font-bold">{title}</h2>{right}</div>}
      {children}
    </section>
  )
}

export function Insight({ children }) {
  if (!children) return null
  return <p className="mt-2 rounded-xl bg-brand-soft px-3 py-2 text-sm text-ink/80">💡 {children}</p>
}

export function Loading() { return <div className="p-8 text-center text-sm text-ink/50">Memuat…</div> }
export function Empty({ children }) { return <div className="rounded-xl border border-dashed border-brand-line p-6 text-center text-sm text-ink/50">{children}</div> }
export function ErrorBox({ msg }) { return msg ? <div className="rounded-xl border border-brand bg-red-50 px-3 py-2 text-sm text-brand">{msg}</div> : null }

export function Modal({ open, onClose, title, children, footer, wide }) {
  useEffect(() => {
    if (!open) return
    const h = (e) => e.key === 'Escape' && onClose?.()
    window.addEventListener('keydown', h); return () => window.removeEventListener('keydown', h)
  }, [open, onClose])
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 sm:items-center" onMouseDown={onClose}>
      <div onMouseDown={(e) => e.stopPropagation()} className={`max-h-[92vh] w-full overflow-y-auto rounded-t-3xl bg-white sm:rounded-3xl ${wide ? 'sm:max-w-4xl' : 'sm:max-w-lg'}`}>
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-brand-line bg-white px-4 py-3">
          <h3 className="text-base font-bold">{title}</h3>
          <button onClick={onClose} className="h-9 w-9 rounded-full text-xl leading-none hover:bg-brand-soft" aria-label="Tutup">×</button>
        </div>
        <div className="p-4">{children}</div>
        {footer && <div className="sticky bottom-0 flex flex-wrap justify-end gap-2 border-t border-brand-line bg-white px-4 py-3">{footer}</div>}
      </div>
    </div>
  )
}

export function Field({ label, children, hint, className = '' }) {
  return <label className={`block ${className}`}><span className="label">{label}</span>{children}{hint && <span className="mt-1 block text-[11px] text-ink/50">{hint}</span>}</label>
}

export function MoneyInput({ value, onChange, ...p }) {
  const [txt, setTxt] = useState(value ? new Intl.NumberFormat('id-ID').format(value) : '')
  useEffect(() => { setTxt(value ? new Intl.NumberFormat('id-ID').format(value) : (value === 0 ? '0' : '')) }, [value])
  return <input {...p} inputMode="numeric" className="input num" value={txt} placeholder="0"
    onChange={(e) => { const n = Number(e.target.value.replace(/\D/g, '') || 0); setTxt(e.target.value.replace(/[^\d.]/g, '')); onChange(n) }}
    onBlur={() => setTxt(value ? new Intl.NumberFormat('id-ID').format(value) : '')} />
}

export function MonthPicker({ value, onChange }) {
  return (
    <div className="inline-flex items-center rounded-xl border border-brand-line">
      <button className="h-10 w-10 text-lg hover:bg-brand-soft rounded-l-xl" onClick={() => onChange(shiftMonth(value, -1))} aria-label="Bulan sebelumnya">‹</button>
      <span className="min-w-[130px] px-2 text-center text-sm font-semibold capitalize">{monthLabel(value)}</span>
      <button className="h-10 w-10 text-lg hover:bg-brand-soft rounded-r-xl" onClick={() => onChange(shiftMonth(value, 1))} aria-label="Bulan berikutnya">›</button>
    </div>
  )
}

export function FileDrop({ files, onChange, label = 'Upload screenshot insight', accept = 'image/*' }) {
  const ref = useRef()
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const pick = async (e) => {
    const list = Array.from(e.target.files || []); if (!list.length) return
    setBusy(true); setErr('')
    try { const ids = []; for (const f of list) { const r = await upload(f); ids.push(r.id) } onChange([...(files || []), ...ids]) }
    catch (x) { setErr(x.message) } finally { setBusy(false); e.target.value = '' }
  }
  return (
    <div>
      <div className="flex flex-wrap gap-2">
        {(files || []).map((f) => (
          <div key={f} className="relative">
            {f.endsWith('.pdf') ? <a href={fileUrl(f)} target="_blank" rel="noreferrer" className="flex h-20 w-16 items-center justify-center rounded-lg border border-brand-line text-xs">PDF</a>
              : <a href={fileUrl(f)} target="_blank" rel="noreferrer"><img src={fileUrl(f)} alt="bukti" className="h-20 w-16 rounded-lg border border-brand-line object-cover" /></a>}
            <button type="button" onClick={() => onChange(files.filter((x) => x !== f))} className="absolute -right-1.5 -top-1.5 h-6 w-6 rounded-full bg-ink text-xs text-white" aria-label="Hapus">×</button>
          </div>
        ))}
        <button type="button" onClick={() => ref.current.click()} disabled={busy} className="flex h-20 min-w-[64px] flex-col items-center justify-center rounded-lg border-2 border-dashed border-brand/40 px-2 text-[11px] font-semibold text-brand">
          {busy ? 'Upload…' : <><span className="text-xl leading-none">+</span>{label.length < 14 ? label : 'Foto'}</>}
        </button>
      </div>
      <input ref={ref} type="file" accept={accept} multiple hidden onChange={pick} />
      {err && <p className="mt-1 text-xs text-brand">{err}</p>}
    </div>
  )
}

// Toast
const ToastCtx = createContext(() => {})
export function ToastProvider({ children }) {
  const [items, setItems] = useState([])
  const push = useCallback((msg, tone = 'ok') => {
    const id = Math.random(); setItems((x) => [...x, { id, msg, tone }])
    setTimeout(() => setItems((x) => x.filter((i) => i.id !== id)), 4200)
  }, [])
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="fixed bottom-20 left-1/2 z-[60] flex w-[92%] max-w-md -translate-x-1/2 flex-col gap-2 sm:bottom-6">
        {items.map((t) => <div key={t.id} className={`rounded-xl px-4 py-3 text-sm font-medium shadow-lg ${t.tone === 'err' ? 'bg-brand text-white' : 'bg-ink text-white'}`}>{t.msg}</div>)}
      </div>
    </ToastCtx.Provider>
  )
}
export const useToast = () => useContext(ToastCtx)

export function useApi(path, deps = []) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const load = useCallback(async () => {
    if (!path) return
    setLoading(true); setError('')
    try { setData(await api(path)) } catch (e) { setError(e.message) } finally { setLoading(false) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, ...deps])
  useEffect(() => { load() }, [load])
  return { data, error, loading, reload: load, setData }
}

export function ReasonModal({ open, title, label = 'Alasan', onClose, onSubmit, confirmText = 'Simpan', danger }) {
  const [txt, setTxt] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  useEffect(() => { if (open) { setTxt(''); setErr('') } }, [open])
  return (
    <Modal open={open} onClose={onClose} title={title} footer={<>
      <button className="btn-ghost" onClick={onClose}>Batal</button>
      <button className={danger ? 'btn-primary' : 'btn-ok'} disabled={busy} onClick={async () => { setBusy(true); setErr(''); try { await onSubmit(txt) } catch (e) { setErr(e.message) } finally { setBusy(false) } }}>{confirmText}</button>
    </>}>
      <Field label={label}><textarea className="input min-h-[96px] py-2" value={txt} onChange={(e) => setTxt(e.target.value)} autoFocus /></Field>
      <div className="mt-2"><ErrorBox msg={err} /></div>
    </Modal>
  )
}

export function Table({ head, children, className = '' }) {
  return (
    <div className={`overflow-x-auto rounded-xl border border-brand-line ${className}`}>
      <table className="w-full border-collapse">
        <thead><tr>{head.map((h, i) => <th key={i} className={`th ${h?.right ? 'text-right' : ''}`}>{h?.label ?? h}</th>)}</tr></thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  )
}
