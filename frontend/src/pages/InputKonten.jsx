import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api'
import { useApp } from '../App'
import { ContentForm, SnapshotForm } from '../components/inputs'
import { Badge, ErrorBox, Loading, StatusBadge, TierBadge, useApi } from '../components/ui'
import { date, num, short } from '../fmt'

const ACTIVE = ['DEAL', 'BRIEF_SENT', 'DRAFT_REVIEW', 'POSTED', 'REPORT_DUE']

export default function InputKonten() {
  const { user } = useApp()
  const [sp, setSp] = useSearchParams()
  const nav = useNavigate()
  const bid = sp.get('b')
  const { data: list, error } = useApi('/api/bookings')
  const [q, setQ] = useState('')
  const [b, setB] = useState(null)
  const [addContent, setAddContent] = useState(false)
  const [snap, setSnap] = useState(null)
  const loadB = async () => { if (bid) setB(await api(`/api/bookings/${bid}`)); else setB(null) }
  useEffect(() => { loadB().catch(() => {}) /* eslint-disable-next-line */ }, [bid])
  useEffect(() => {
    if (b && sp.get('c')) { const ct = b.contents.find((x) => x.id === sp.get('c')); if (ct) setSnap({ ct, day: sp.get('d') }); setSp({ b: bid }, { replace: true }) }
    // eslint-disable-next-line
  }, [b])
  const active = useMemo(() => (list || []).filter((x) => ACTIVE.includes(x.status) && `${x.kol.name} ${x.campaign.name}`.toLowerCase().includes(q.toLowerCase()))
    .sort((a, c) => (c.createdById === user.id) - (a.createdById === user.id)), [list, q, user.id])
  if (error) return <ErrorBox msg={error} />
  if (!bid) return (
    <div className="mx-auto max-w-xl space-y-3">
      <h1 className="text-xl font-extrabold">Input konten & metrik</h1>
      <p className="text-sm text-ink/60">Pilih booking → paste link post → isi angka dari screenshot insight. Target ≤ 3 menit per konten.</p>
      <input className="input" placeholder="Cari KOL / campaign…" value={q} onChange={(e) => setQ(e.target.value)} />
      {!list ? <Loading /> : active.map((x) => (
        <button key={x.id} onClick={() => setSp({ b: x.id })} className="card flex w-full items-center gap-3 p-3 text-left hover:border-brand">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1.5"><span className="truncate font-bold">{x.kol.name}</span><TierBadge t={x.tierAtBooking} /></div>
            <div className="truncate text-xs text-ink/60">{x.campaign.category} · {x.campaign.name}</div>
            <div className="mt-1 flex flex-wrap gap-1"><StatusBadge s={x.status} />{x.metrics.flags.filter((f) => f.level === 'red').map((f) => <Badge key={f.code} tone="red">{f.label}</Badge>)}</div>
          </div>
          <span className="text-ink/40">›</span>
        </button>
      ))}
      {list && !active.length && <p className="py-6 text-center text-sm text-ink/50">Tidak ada booking aktif.</p>}
    </div>
  )
  if (!b) return <Loading />
  const ds = (s) => Math.floor((Date.now() - new Date(s + 'T00:00:00')) / 864e5)
  return (
    <div className="mx-auto max-w-xl space-y-3">
      <button onClick={() => setSp({})} className="text-sm font-semibold text-brand">‹ Pilih booking lain</button>
      <div className="card p-4">
        <div className="flex items-center gap-2"><span className="text-lg font-extrabold">{b.kol.name}</span><TierBadge t={b.tierAtBooking} /><StatusBadge s={b.status} /></div>
        <div className="text-sm text-ink/60">{b.campaign.category} · {b.campaign.name} · kode {b.uniqueCode}</div>
      </div>
      {b.contents.map((ct) => {
        const have = new Set(ct.snapshots.map((s) => s.day))
        const d = ds(ct.postedAt)
        return (
          <div key={ct.id} className="card p-4">
            <a href={ct.url} target="_blank" rel="noreferrer" className="block truncate text-sm font-semibold text-brand underline">{ct.url}</a>
            <div className="text-xs text-ink/60">tayang {date(ct.postedAt)} · {d} hari lalu</div>
            <div className="mt-3 grid grid-cols-4 gap-1.5">
              {[['H1', 1], ['H3', 3], ['H7', 7], ['H30', 30]].map(([day, off]) => {
                const s = ct.snapshots.find((x) => x.day === day)
                const avail = d >= off
                return (
                  <button key={day} disabled={!avail} onClick={() => setSnap({ ct, day })} className={`rounded-xl border py-3 text-center disabled:opacity-40 ${s ? 'border-ok bg-green-50' : avail ? 'border-brand bg-red-50' : 'border-brand-line'}`}>
                    <div className="text-sm font-bold">{day.replace('H', 'H+')}</div>
                    <div className="text-[11px] num">{s ? short(s.views) + ' views' : avail ? 'Isi' : `${off - d} hari lagi`}</div>
                  </button>
                )
              })}
            </div>
          </div>
        )
      })}
      {ACTIVE.includes(b.status) && <button className="btn-primary w-full" onClick={() => setAddContent(true)}>+ Paste link konten tayang</button>}
      <button className="btn-ghost w-full" onClick={() => nav(`/booking/${b.id}`)}>Buka detail booking</button>
      <ContentForm open={addContent} onClose={() => setAddContent(false)} booking={b} onSaved={loadB} />
      <SnapshotForm open={!!snap} onClose={() => setSnap(null)} content={snap?.ct} day={snap?.day} fields={b.requiredFields} category={b.campaign.category} onSaved={loadB} />
    </div>
  )
}
