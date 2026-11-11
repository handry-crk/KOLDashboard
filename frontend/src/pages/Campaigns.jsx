import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, download } from '../api'
import { useApp } from '../App'
import { CampaignForm, BookingForm } from '../components/forms'
import { Badge, EvidenceBadge, ErrorBox, Field, GateBadge, Loading, Modal, MonthPicker, ReviewBadge, Section, StatusBadge, Table, TierBadge, Tile, useApi, useToast, Empty } from '../components/ui'
import { date, num, pct, rp, rpShort, short, thisMonth, times } from '../fmt'

export default function Campaigns() {
  const { can } = useApp()
  const [month, setMonth] = useState(thisMonth())
  const [cat, setCat] = useState('')
  const [open, setOpen] = useState(false)
  const { data, error, loading, reload } = useApi(`/api/campaigns?month=${month}`)
  const nav = useNavigate()
  const list = (data || []).filter((c) => !cat || c.category === cat)
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-xl font-extrabold">Campaign</h1>
        <div className="flex flex-wrap gap-2">
          <MonthPicker value={month} onChange={setMonth} />
          <select className="input w-auto" value={cat} onChange={(e) => setCat(e.target.value)}><option value="">Semua kategori</option>{['Regular Visit', 'Frozen', 'NPL', 'Info Lokasi', 'Keranjang Kuning', 'TikTok GO'].map((c) => <option key={c}>{c}</option>)}</select>
          {can('Manager', 'KOL TL') && <button className="btn-primary" onClick={() => setOpen(true)}>+ Campaign</button>}
        </div>
      </div>
      <ErrorBox msg={error} />
      {loading && !data ? <Loading /> : !list.length ? <Empty>Belum ada campaign di bulan ini.</Empty> : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {list.map((c) => {
            const used = c.budgetRp ? c.committed / c.budgetRp : 0
            return (
              <button key={c.id} onClick={() => nav(`/campaign/${c.id}`)} className="card p-4 text-left hover:border-brand">
                <div className="flex items-start justify-between gap-2">
                  <div><div className="text-[11px] font-semibold text-ink/50">{c.code}</div><div className="font-bold leading-tight">{c.name}</div></div>
                  <GateBadge g={c.gateStatus} />
                </div>
                <div className="mt-2 flex flex-wrap items-center gap-1.5"><Badge tone="brand">{c.category}</Badge>{c.review && <ReviewBadge r={c.review} />}<span className="text-xs text-ink/50">{date(c.start)} – {date(c.end)}</span></div>
                <div className="mt-3 flex justify-between text-xs"><span>Committed {rpShort(c.committed)}</span><span className="text-ink/60">dari {rpShort(c.budgetRp)}</span></div>
                <div className="mt-1 h-2 overflow-hidden rounded-full bg-brand-soft"><div className={`bar-grow h-full rounded-full ${used > 0.9 ? 'bg-warn' : 'bg-brand'}`} style={{ width: `${Math.min(100, used * 100)}%` }} /></div>
                <div className="mt-3 grid grid-cols-3 gap-2 text-center">
                  <div><div className="text-[10px] uppercase text-ink/50">KOL</div><div className="font-bold num">{c.bookingCount}</div></div>
                  <div><div className="text-[10px] uppercase text-ink/50">Views</div><div className="font-bold num">{short(c.agg.views)}</div></div>
                  <div><div className="text-[10px] uppercase text-ink/50">{['NPL', 'Info Lokasi'].includes(c.category) ? 'CPV' : 'ROI DIRECT'}</div><div className="font-bold num">{['NPL', 'Info Lokasi'].includes(c.category) ? rp(c.agg.cpv) : times(c.agg.roiDirect)}</div></div>
                </div>
                {c.agg.flags > 0 && <div className="mt-2 text-xs font-semibold text-brand">⚠ {c.agg.flags} catatan perlu dicek</div>}
              </button>
            )
          })}
        </div>
      )}
      <CampaignForm open={open} onClose={() => setOpen(false)} onSaved={reload} />
    </div>
  )
}

export function CampaignDetail() {
  const { id } = useParams()
  const { can, meta } = useApp()
  const toast = useToast()
  const { data: c, error, reload } = useApi(`/api/campaigns/${id}`)
  const { data: rep, reload: reloadRep } = useApi(`/api/reports/campaign/${id}`)
  const [edit, setEdit] = useState(false)
  const [book, setBook] = useState(false)
  const [rev, setRev] = useState(false)
  const nav = useNavigate()
  if (error) return <ErrorBox msg={error} />
  if (!c) return <Loading />
  const a = c.agg
  const refresh = () => { reload(); reloadRep() }
  const groups = [['Pra-deal', ['SHORTLIST', 'NEGO', 'WAITING_APPROVAL']], ['Deal & produksi', ['DEAL', 'BRIEF_SENT', 'DRAFT_REVIEW']], ['Tayang / report', ['POSTED', 'REPORT_DUE', 'REPORT_SUBMITTED']], ['Selesai', ['REPORT_APPROVED', 'PAID']], ['Batal', ['CANCELLED']]]
  return (
    <div className="space-y-4">
      <Link to="/campaign" className="no-print text-sm font-semibold text-brand">‹ Campaign</Link>
      <div className="card p-4">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <div className="text-xs font-semibold text-ink/50">{c.code}</div>
            <h1 className="text-xl font-extrabold">{c.name}</h1>
            <div className="mt-1 flex flex-wrap items-center gap-1.5"><Badge tone="brand">{c.category}</Badge><GateBadge g={c.gateStatus} />{c.config.evidence.map((e) => <EvidenceBadge key={e} e={e} />)}<span className="text-xs text-ink/60">{date(c.start)} – {date(c.end)} · Owner {c.ownerName}</span></div>
            <p className="mt-2 text-sm text-ink/70">{c.objective}</p>
            {c.target?.outlets?.length > 0 && <p className="mt-1 text-xs text-ink/60">Outlet: {c.target.outlets.join(', ')}{c.target.sku && ` · SKU ${c.target.sku}`}</p>}
          </div>
          <div className="no-print flex flex-wrap gap-2">
            <button className="btn-ghost" onClick={() => download(`/api/reports/campaign/${id}?format=xlsx`, `KOL_Report_${c.code}.xlsx`).catch((e) => toast(e.message, 'err'))}>Export</button>
            {can('Manager', 'KOL TL') && <button className="btn-ghost" onClick={() => setEdit(true)}>Edit</button>}
            {can('Manager', 'KOL TL') && <button className="btn-ghost" onClick={() => setRev(true)}>Review</button>}
            {can('Manager', 'KOL TL', 'KOL Officer') && !['HOLD', 'SELESAI'].includes(c.gateStatus) && <button className="btn-primary" onClick={() => setBook(true)}>+ Booking KOL</button>}
          </div>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2 md:grid-cols-6">
        <Tile label="Budget" icon="💰" raw={c.budgetRp} format={rpShort} sub={`Committed ${rpShort(c.committed)}`} />
        <Tile label="Views" icon="👀" raw={a.views} format={short} sub={`CPV ${rp(a.cpv)}`} />
        <Tile label="ER" value={pct(a.er)} />
        <Tile label={c.config.outcomeLabel} icon="🎯" raw={a.outcome} format={num} sub={`Cost/outcome ${rp(a.costPerOutcome)}`} />
        <Tile label="Revenue DIRECT" value={c.config.evidence.includes('DIRECT') ? rpShort(a.revenueDirect) : '–'} sub={c.config.assisted ? `ASSISTED ${rpShort(a.revenueAssisted)}` : ''} />
        <Tile label="ROI DIRECT" value={times(a.roiDirect)} sub={c.config.assisted ? `+ASSISTED ${times(a.roiTotal)}` : (a.roas ? `ROAS ${times(a.roas)}` : '')} />
      </div>
      {rep && (
        <Section title="Planned vs Actual">
          <Table head={['Metric', { label: 'Target', right: 1 }, { label: 'Actual', right: 1 }, { label: 'Achievement', right: 1 }]}>
            {rep.pva.map((p) => {
              const f = p.fmt === 'rp' ? rp : p.fmt === 'x' ? times : num
              return <tr key={p.metric}><td className="td min-w-[150px]">{p.metric}</td><td className="td text-right num text-ink/60">{p.target ? f(p.target) : '–'}</td><td className="td text-right num font-semibold">{f(p.actual)}</td>
                <td className={`td text-right num font-semibold ${p.achievement == null ? '' : p.achievement >= 1 ? 'text-ok' : p.achievement >= 0.7 ? 'text-amber-700' : 'text-brand'}`}>{p.achievement == null ? '–' : pct(p.achievement, 0)}</td></tr>
            })}
          </Table>
          {c.config.assisted && <p className="mt-2 text-xs text-ink/50">ASSISTED = revenue outlet target di window {c.category === 'Info Lokasi' ? 'D0–D+13' : 'D0–D+6'} dikurangi rata-rata hari yang sama 4 minggu sebelumnya; dibagi proporsional views bila ada beberapa KOL di window yang sama. Butuh import penjualan outlet (Pengaturan).</p>}
        </Section>
      )}
      {c.review && (
        <Section title={<span>Review <ReviewBadge r={c.review} /></span>}>
          <p className="text-sm">{c.reviewNote}</p>
          <div className="mt-2 grid gap-2 text-sm sm:grid-cols-3">
            <div><div className="label">What worked</div>{c.whatWorked || '–'}</div><div><div className="label">What didn’t</div>{c.whatDidnt || '–'}</div><div><div className="label">Next action</div>{c.nextAction || '–'}</div>
          </div>
          <p className="mt-2 text-xs text-ink/50">oleh {c.reviewedBy} · {date(c.reviewedAt)}</p>
        </Section>
      )}
      <Section title="Booking KOL">
        <div className="grid gap-3 lg:grid-cols-5">
          {groups.map(([g, sts]) => {
            const rows = c.rows.filter((r) => sts.includes(r.booking.status))
            return (
              <div key={g} className="rounded-2xl bg-brand-soft p-2">
                <div className="mb-2 px-1 text-xs font-bold uppercase text-ink/60">{g} · {rows.length}</div>
                <div className="space-y-2">
                  {rows.map((r) => (
                    <button key={r.booking.id} onClick={() => nav(`/booking/${r.booking.id}`)} className="lift w-full rounded-xl border border-brand-line bg-white p-2.5 text-left hover:border-brand">
                      <div className="flex items-center justify-between gap-1"><span className="text-sm font-bold leading-tight">{r.kol.name}</span><TierBadge t={r.booking.tierAtBooking} /></div>
                      <div className="mt-1 flex flex-wrap items-center gap-1"><StatusBadge s={r.booking.status} /><span className="text-xs num text-ink/60">{rpShort(r.metrics.cost)}</span></div>
                      {r.metrics.views > 0 && <div className="mt-1 text-[11px] text-ink/60 num">{short(r.metrics.views)} views · {num(r.metrics.outcome)} outcome</div>}
                      {r.metrics.flags.map((f) => <div key={f.code} className={`mt-1 text-[11px] font-semibold ${f.level === 'red' ? 'text-brand' : 'text-amber-700'}`}>⚠ {f.label}</div>)}
                    </button>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      </Section>
      <CampaignForm open={edit} onClose={() => setEdit(false)} initial={{ ...c, bookingCount: c.rows.length }} onSaved={refresh} />
      <BookingForm open={book} onClose={() => setBook(false)} campaignId={id} onSaved={(b) => nav(`/booking/${b.id}`)} />
      <ReviewForm open={rev} onClose={() => setRev(false)} c={c} onSaved={refresh} />
    </div>
  )
}

function ReviewForm({ open, onClose, c, onSaved }) {
  const toast = useToast()
  const [f, setF] = useState({ review: c.review || 'KEEP', reviewNote: c.reviewNote || '', whatWorked: c.whatWorked || '', whatDidnt: c.whatDidnt || '', nextAction: c.nextAction || '' })
  const [err, setErr] = useState('')
  const save = async () => {
    try { await api(`/api/campaigns/${c.id}/review`, { method: 'POST', body: f }); toast('Review disimpan'); onSaved(); onClose() } catch (e) { setErr(e.message) }
  }
  return (
    <Modal open={open} onClose={onClose} title="Review campaign (M+1)" footer={<><button className="btn-ghost" onClick={onClose}>Batal</button><button className="btn-primary" onClick={save}>Simpan review</button></>}>
      <div className="space-y-3">
        <div className="grid grid-cols-3 gap-2">{['SCALE', 'KEEP', 'STOP'].map((r) => <button key={r} onClick={() => setF({ ...f, review: r })} className={`btn ${f.review === r ? 'bg-brand text-white' : 'border border-brand-line'}`}>{r}</button>)}</div>
        <Field label="Learning utama (min. 10 karakter)"><textarea className="input min-h-[72px] py-2" value={f.reviewNote} onChange={(e) => setF({ ...f, reviewNote: e.target.value })} /></Field>
        <Field label="What worked"><input className="input" value={f.whatWorked} onChange={(e) => setF({ ...f, whatWorked: e.target.value })} /></Field>
        <Field label="What didn’t"><input className="input" value={f.whatDidnt} onChange={(e) => setF({ ...f, whatDidnt: e.target.value })} /></Field>
        <Field label="Next action"><input className="input" value={f.nextAction} onChange={(e) => setF({ ...f, nextAction: e.target.value })} /></Field>
        <p className="text-xs text-ink/50">Campaign baru bisa ditutup SELESAI oleh Manager setelah review diisi dan semua report di-approve.</p>
        <ErrorBox msg={err} />
      </div>
    </Modal>
  )
}
