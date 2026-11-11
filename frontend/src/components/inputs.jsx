import { useEffect, useState } from 'react'
import { api } from '../api'
import { useApp } from '../App'
import { ErrorBox, Field, FileDrop, Modal, useToast } from './ui'
import { todayISO } from '../fmt'
import { celebrate } from './fx'

const daysSince = (s) => Math.floor((new Date(todayISO() + 'T00:00:00') - new Date(s + 'T00:00:00')) / 864e5)

export function ContentForm({ open, onClose, booking, onSaved }) {
  const toast = useToast()
  const [f, setF] = useState(null)
  const [err, setErr] = useState('')
  const [mismatch, setMismatch] = useState(false)
  const [busy, setBusy] = useState(false)
  useEffect(() => { if (open) { setF({ url: '', postedAt: todayISO(), format: 'Video', proofFiles: [], handleMismatchReason: '', isCollab: false, adsBoosted: false, boostCostRp: 0 }); setErr(''); setMismatch(false) } }, [open])
  if (!f) return null
  const save = async () => {
    setBusy(true); setErr('')
    try {
      const r = await api('/api/contents', { method: 'POST', body: { ...f, bookingId: booking.id } })
      toast('Konten tayang tercatat ▶️'); celebrate(undefined, undefined, 22); onSaved?.(r); onClose()
    } catch (e) {
      if (e.message.startsWith('handle_mismatch')) { setMismatch(true); setErr(e.message.replace('handle_mismatch: ', '')) } else setErr(e.message)
    } finally { setBusy(false) }
  }
  return (
    <Modal open={open} onClose={onClose} title={`Link konten · ${booking?.kol?.name || ''}`} footer={<><button className="btn-ghost" onClick={onClose}>Batal</button><button className="btn-primary" disabled={busy || !f.url} onClick={save}>Simpan</button></>}>
      <div className="space-y-3">
        <Field label="Link post (paste)" hint="Platform & handle terbaca otomatis dari link"><input className="input" inputMode="url" value={f.url} onChange={(e) => setF({ ...f, url: e.target.value })} placeholder="https://www.tiktok.com/@handle/video/…" autoFocus /></Field>
        <div className="grid grid-cols-2 gap-2">
          <Field label="Tanggal tayang"><input type="date" className="input" max={todayISO()} value={f.postedAt} onChange={(e) => setF({ ...f, postedAt: e.target.value })} /></Field>
          <Field label="Format"><select className="input" value={f.format} onChange={(e) => setF({ ...f, format: e.target.value })}>{['Video', 'Reels', 'Story', 'Feed', 'Live', 'Shorts'].map((x) => <option key={x}>{x}</option>)}</select></Field>
        </div>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" className="h-5 w-5" checked={f.adsBoosted} onChange={(e) => setF({ ...f, adsBoosted: e.target.checked })} /> Di-boost ads (biaya ikut dihitung)</label>
        {f.adsBoosted && <Field label="Biaya boost (Rp)"><input className="input" inputMode="numeric" value={f.boostCostRp || ''} onChange={(e) => setF({ ...f, boostCostRp: Number(e.target.value.replace(/\D/g, '')) })} /></Field>}
        <Field label="Screenshot post (opsional)"><FileDrop files={f.proofFiles} onChange={(v) => setF({ ...f, proofFiles: v })} label="Foto" /></Field>
        {mismatch && <Field label="Alasan handle berbeda (mis. collab post / akun kedua)"><input className="input" value={f.handleMismatchReason} onChange={(e) => setF({ ...f, handleMismatchReason: e.target.value })} /></Field>}
        <ErrorBox msg={err} />
      </div>
    </Modal>
  )
}

export function SnapshotForm({ open, onClose, content, fields, day: day0, existing, category, onSaved }) {
  const { meta, can } = useApp()
  const toast = useToast()
  const [day, setDay] = useState(day0 || 'H1')
  const [vals, setVals] = useState({})
  const [proof, setProof] = useState([])
  const [reason, setReason] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const ds = content ? daysSince(content.postedAt) : 0
  const snaps = content?.snapshots || []
  const cur = snaps.find((s) => s.day === day)
  useEffect(() => {
    if (!open) return
    const d = day0 || (['H7', 'H3', 'H1'].find((x) => ds >= { H1: 1, H3: 3, H7: 7 }[x]) || 'H1')
    setDay(d); setErr(''); setReason('')
  }, [open, day0, ds])
  useEffect(() => {
    if (!open) return
    const s = snaps.find((x) => x.day === day)
    const prev = [...snaps].filter((x) => x.day < day).pop()
    setVals(Object.fromEntries(fields.map((f) => [f, s?.[f] ?? ''])))
    setProof(s?.proofFiles || [])
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, day])
  if (!open || !content) return null
  const save = async () => {
    setBusy(true); setErr('')
    try { await api('/api/snapshots', { method: 'POST', body: { contentId: content.id, day, values: vals, proofFiles: proof, reason } }); toast(`Snapshot ${day} tersimpan`); onSaved?.(); onClose() }
    catch (e) { setErr(e.message) } finally { setBusy(false) }
  }
  const offs = { H1: 1, H3: 3, H7: 7, H30: 30 }
  return (
    <Modal open={open} onClose={onClose} title="Isi metrik dari screenshot insight" footer={<><button className="btn-ghost" onClick={onClose}>Batal</button><button className="btn-primary" disabled={busy || (cur?.locked && !can('KOL TL', 'Manager'))} onClick={save}>Simpan {day}</button></>}>
      <div className="space-y-3">
        <div className="text-xs text-ink/60 break-all">{content.url} · tayang {content.postedAt} ({ds} hari lalu) · {category}</div>
        <div className="grid grid-cols-4 gap-1.5">
          {meta.snapDays.map((d) => {
            const avail = ds >= offs[d]; const has = snaps.some((s) => s.day === d)
            return <button key={d} type="button" disabled={!avail} onClick={() => setDay(d)} className={`rounded-xl border py-2 text-sm font-bold ${day === d ? 'border-brand bg-brand text-white' : has ? 'border-ok text-ok' : 'border-brand-line'} disabled:opacity-40`}>{d.replace('H', 'H+')}{has ? ' ✓' : ''}</button>
          })}
        </div>
        {cur?.locked && <div className="rounded-xl bg-amber-50 px-3 py-2 text-xs text-amber-800">🔒 Terkunci (lewat H+7). {can('KOL TL', 'Manager') ? 'Perubahan wajib disertai alasan dan tercatat di audit log.' : 'Hanya KOL TL yang dapat mengubah.'}</div>}
        <div className="grid grid-cols-2 gap-2">
          {fields.map((f) => (
            <Field key={f} label={meta.metricLabels[f] + ' *'}>
              <input className="input num" inputMode="decimal" value={vals[f] ?? ''} onChange={(e) => setVals({ ...vals, [f]: e.target.value.replace(/[^\d.]/g, '') })} placeholder="0" />
            </Field>
          ))}
        </div>
        <Field label="Screenshot insight * (bukti wajib)"><FileDrop files={proof} onChange={setProof} label="Foto" /></Field>
        {cur?.locked && can('KOL TL', 'Manager') && <Field label="Alasan perubahan"><input className="input" value={reason} onChange={(e) => setReason(e.target.value)} /></Field>}
        <p className="text-[11px] text-ink/50">* Wajib diisi untuk kategori {category}. 0 boleh, kosong tidak.</p>
        <ErrorBox msg={err} />
      </div>
    </Modal>
  )
}
