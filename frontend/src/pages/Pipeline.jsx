import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../App'
import { BookingForm } from '../components/forms'
import { Badge, ErrorBox, Loading, MonthPicker, StatusBadge, STATUS_LABEL, TierBadge, useApi } from '../components/ui'
import { num, rpShort, short, thisMonth } from '../fmt'

export default function Pipeline() {
  const { meta, user } = useApp()
  const [month, setMonth] = useState(thisMonth())
  const [cat, setCat] = useState('')
  const [tier, setTier] = useState('')
  const [mine, setMine] = useState(user.role === 'KOL Officer')
  const [overdue, setOverdue] = useState(false)
  const [mobileStatus, setMobileStatus] = useState('POSTED')
  const [open, setOpen] = useState(false)
  const { data, error, loading, reload } = useApi(`/api/bookings?month=${month}`)
  const nav = useNavigate()
  const rows = useMemo(() => (data || []).filter((b) => (!cat || b.campaign.category === cat) && (!tier || b.tierAtBooking === tier) && (!mine || b.createdById === user.id) && (!overdue || b.metrics.flags.some((f) => f.level === 'red'))), [data, cat, tier, mine, overdue, user.id])
  const cols = meta.statuses
  const card = (b) => (
    <button key={b.id} onClick={() => nav(`/booking/${b.id}`)} className={`w-full rounded-xl border bg-white p-2.5 text-left hover:border-brand ${b.metrics.flags.some((f) => f.level === 'red') ? 'border-brand' : 'border-brand-line'}`}>
      <div className="flex items-center justify-between gap-1"><span className="text-sm font-bold leading-tight">{b.kol.name}</span><TierBadge t={b.tierAtBooking} /></div>
      <div className="mt-0.5 text-[11px] text-ink/60">{b.campaign.category} · {b.campaign.name}</div>
      <div className="mt-1 flex items-center justify-between text-xs"><span className="num font-semibold">{rpShort(b.totalCostRp)}</span>{b.metrics.views > 0 && <span className="num text-ink/60">{short(b.metrics.views)} views</span>}</div>
      {b.deliverables?.[0]?.dueDate && !b.metrics.contents && <div className="text-[11px] text-ink/50">due {b.deliverables[0].dueDate}</div>}
      {b.metrics.flags.map((f) => <div key={f.code} className={`mt-1 text-[11px] font-semibold ${f.level === 'red' ? 'text-brand' : 'text-amber-700'}`}>⚠ {f.label}</div>)}
    </button>
  )
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-xl font-extrabold">Pipeline booking</h1>
        <button className="btn-primary" onClick={() => setOpen(true)}>+ Booking</button>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <MonthPicker value={month} onChange={setMonth} />
        <select className="input w-auto" value={cat} onChange={(e) => setCat(e.target.value)}><option value="">Semua kategori</option>{Object.keys(meta.categories).map((c) => <option key={c}>{c}</option>)}</select>
        <select className="input w-auto" value={tier} onChange={(e) => setTier(e.target.value)}><option value="">Semua tier</option>{meta.tiers.map((t) => <option key={t}>{t}</option>)}</select>
        <label className="flex items-center gap-2 rounded-xl border border-brand-line px-3 min-h-[44px] text-sm"><input type="checkbox" className="h-4 w-4" checked={mine} onChange={(e) => setMine(e.target.checked)} />Booking saya</label>
        <label className="flex items-center gap-2 rounded-xl border border-brand-line px-3 min-h-[44px] text-sm"><input type="checkbox" className="h-4 w-4" checked={overdue} onChange={(e) => setOverdue(e.target.checked)} />Hanya yang terlambat</label>
      </div>
      <ErrorBox msg={error} />
      {loading && !data ? <Loading /> : (
        <>
          <div className="sm:hidden">
            <div className="-mx-3 mb-2 flex gap-1.5 overflow-x-auto px-3 pb-1">
              {cols.map((s) => { const n = rows.filter((b) => b.status === s).length; return <button key={s} onClick={() => setMobileStatus(s)} className={`shrink-0 rounded-full border px-3 py-1.5 text-xs font-semibold ${mobileStatus === s ? 'border-brand bg-brand text-white' : 'border-brand-line'}`}>{STATUS_LABEL[s]} · {n}</button> })}
            </div>
            <div className="space-y-2">{rows.filter((b) => b.status === mobileStatus).map(card)}{!rows.some((b) => b.status === mobileStatus) && <p className="py-6 text-center text-sm text-ink/50">Kosong</p>}</div>
          </div>
          <div className="hidden gap-2 overflow-x-auto pb-3 sm:flex">
            {cols.map((s) => {
              const list = rows.filter((b) => b.status === s)
              return (
                <div key={s} className="w-56 shrink-0 rounded-2xl bg-brand-soft p-2">
                  <div className="mb-2 flex items-center justify-between px-1"><StatusBadge s={s} /><span className="text-xs font-bold text-ink/60">{list.length}</span></div>
                  <div className="space-y-2">{list.map(card)}</div>
                  {list.length > 0 && <div className="mt-2 px-1 text-[11px] text-ink/50 num">Σ {rpShort(list.reduce((a, b) => a + b.totalCostRp, 0))}</div>}
                </div>
              )
            })}
          </div>
        </>
      )}
      <BookingForm open={open} onClose={() => setOpen(false)} onSaved={(b) => nav(`/booking/${b.id}`)} />
    </div>
  )
}
