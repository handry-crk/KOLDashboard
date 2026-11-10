import { useState } from 'react'
import { Link } from 'react-router-dom'
import { download } from '../api'
import { useApp } from '../App'
import { Badge, ErrorBox, Loading, MonthPicker, ReviewBadge, Section, StatusBadge, Table, TierBadge, useApi, useToast, GateBadge, EvidenceBadge } from '../components/ui'
import { date, dateTime, num, pct, rp, rpShort, short, shiftMonth, thisMonth, times, todayISO } from '../fmt'

const addDays = (iso, n) => { const d = new Date(iso + 'T00:00:00'); d.setDate(d.getDate() + n); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}` }

const mondayOf = (iso) => { const k = (new Date(iso + 'T00:00:00').getDay() + 6) % 7; return addDays(iso, -k) }

export default function Laporan() {
  const { can } = useApp()
  const [tab, setTab] = useState('weekly')
  const tabs = [['weekly', 'Tab 8 KOL (mingguan)'], ['review', 'Review M+1'], ['campaign', 'Report per campaign'], ...(can('Manager', 'KOL TL') ? [['audit', 'Audit log']] : [])]
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-extrabold">Laporan</h1>
      <div className="no-print flex flex-wrap gap-2">{tabs.map(([k, l]) => <button key={k} onClick={() => setTab(k)} className={`btn btn-sm ${tab === k ? 'bg-brand text-white' : 'border border-brand-line'}`}>{l}</button>)}</div>
      {tab === 'weekly' && <Weekly />}
      {tab === 'review' && <Review />}
      {tab === 'campaign' && <PerCampaign />}
      {tab === 'audit' && <Audit />}
    </div>
  )
}

function Weekly() {
  const toast = useToast()
  const [week, setWeek] = useState(addDays(mondayOf(todayISO()), -7))
  const { data: w, error } = useApi(`/api/reports/weekly?week=${week}`)
  return (
    <div className="space-y-4">
      <div className="no-print flex flex-wrap items-center gap-2">
        <div className="inline-flex items-center rounded-xl border border-brand-line">
          <button className="h-10 w-10 text-lg" onClick={() => setWeek(addDays(week, -7))}>‹</button>
          <span className="px-2 text-sm font-semibold">{date(week)} – {date(addDays(week, 6))}</span>
          <button className="h-10 w-10 text-lg" onClick={() => setWeek(addDays(week, 7))}>›</button>
        </div>
        <button className="btn-ghost" onClick={() => download(`/api/reports/weekly?week=${week}&format=xlsx`, `KOL_Tab8_${week}.xlsx`).catch((e) => toast(e.message, 'err'))}>Export Excel</button>
        <button className="btn-ghost" onClick={() => window.print()}>Cetak / PDF</button>
      </div>
      <ErrorBox msg={error} />
      {!w ? <Loading /> : (
        <>
          <p className="text-xs text-ink/60">Input tab 8 Meeting Input Pack (deadline Selasa 15.00). Cut-off Minggu 23.59.</p>
          <div className="grid grid-cols-2 gap-2 md:grid-cols-6">
            {[['Booking tayang', num(w.agg.bookings)], ['Biaya', rpShort(w.agg.cost)], ['Views', short(w.agg.views)], ['CPV', rp(w.agg.cpv)], ['Revenue DIRECT', rpShort(w.agg.revenueDirect)], ['Terlambat', num(w.overdue.length)]].map(([l, v]) => (
              <div key={l} className="card p-3"><div className="text-[11px] font-semibold uppercase text-ink/60">{l}</div><div className="text-lg font-extrabold num">{v}</div></div>
            ))}
          </div>
          <Section title="Insight prioritas (Evidence → Diagnosis → Implikasi)">
            {!w.insights.length ? <p className="text-sm text-ink/50">Belum ada data minggu ini.</p> : w.insights.map((i, k) => (
              <div key={k} className="mb-2 rounded-xl bg-brand-soft p-3 text-sm"><b>{k + 1}.</b> {i.evidence} <Badge tone="amber">{i.diagnosis}</Badge><div className="mt-1">→ {i.implication}</div><div className="mt-1 text-xs text-ink/60">Owner {i.owner} · deadline {date(i.deadline)}</div></div>
            ))}
          </Section>
          <Section title="Konten tayang minggu ini">
            <Table head={['KOL', 'Campaign', { label: 'Post', right: 1 }, { label: 'Biaya', right: 1 }, { label: 'Views', right: 1 }, 'Outcome', { label: 'Rev. DIRECT', right: 1 }, 'Status']}>
              {w.rows.map((r, i) => <tr key={i}><td className="td"><b>{r.kol}</b> <TierBadge t={r.tier} /></td><td className="td text-xs">{r.campaign}<div className="text-ink/50">{r.category}</div></td><td className="td text-right num">{r.posts}</td><td className="td text-right num">{rpShort(r.cost)}</td><td className="td text-right num">{short(r.views)}</td><td className="td text-xs"><b className="num">{num(r.outcome)}</b> {r.outcomeLabel}</td><td className="td text-right num">{rpShort(r.revenueDirect)}</td><td className="td"><StatusBadge s={r.status} /></td></tr>)}
            </Table>
          </Section>
          <Section title="Report / deliverable terlambat (semua)">
            <Table head={['KOL', 'Campaign', 'Status', 'Catatan', 'Officer']}>
              {w.overdue.map((o, i) => <tr key={i}><td className="td font-semibold">{o.kol}</td><td className="td text-xs">{o.campaign}</td><td className="td"><StatusBadge s={o.status} /></td><td className="td text-xs text-brand">{o.flag}</td><td className="td text-xs">{o.officer}</td></tr>)}
            </Table>
          </Section>
        </>
      )}
    </div>
  )
}

function Review() {
  const toast = useToast()
  const [month, setMonth] = useState(shiftMonth(thisMonth(), -1))
  const { data: d, error } = useApi(`/api/reports/review?month=${month}`)
  return (
    <div className="space-y-4">
      <div className="no-print flex flex-wrap items-center gap-2"><MonthPicker value={month} onChange={setMonth} />
        <button className="btn-ghost" onClick={() => download(`/api/reports/review?month=${month}&format=xlsx`, `KOL_Review_${month}.xlsx`).catch((e) => toast(e.message, 'err'))}>Export Excel</button>
        <button className="btn-ghost" onClick={() => window.print()}>Cetak / PDF</button></div>
      <ErrorBox msg={error} />
      {!d ? <Loading /> : (
        <>
          <Section title="Planned vs Actual per kategori">
            <Table head={['Kategori', 'Bukti', { label: 'Plan', right: 1 }, { label: 'Actual', right: 1 }, { label: 'CPV (bench)', right: 1 }, 'Outcome', { label: 'Cost/outcome (bench)', right: 1 }, { label: 'ROI DIRECT', right: 1 }, { label: 'Indeks', right: 1 }, 'Saran']}>
              {d.rows.map((r) => <tr key={r.category}><td className="td font-semibold">{r.category}</td><td className="td">{r.evidence.map((e) => <EvidenceBadge key={e} e={e} />)}</td><td className="td text-right num">{rpShort(r.planned)}</td><td className="td text-right num">{rpShort(r.spend)}</td><td className="td text-right num">{rp(r.cpv)} <span className="text-ink/40">({rp(r.benchCpv)})</span></td><td className="td text-xs"><b className="num">{num(r.outcome)}</b> {r.outcomeLabel}</td><td className="td text-right num">{rp(r.costPerOutcome)} <span className="text-ink/40">({rp(r.benchCpo)})</span></td><td className="td text-right num">{times(r.roiDirect)}</td><td className="td text-right num">{times(r.index)}</td><td className="td"><ReviewBadge r={r.suggestion} /></td></tr>)}
            </Table>
            <p className="mt-2 text-xs text-ink/50">Saran otomatis: indeks ≥ 1,2× → SCALE, &lt; 0,5× → STOP, di antaranya KEEP. Keputusan akhir di review campaign oleh KOL TL & Manager.</p>
          </Section>
          <Section title="Status campaign">
            <Table head={['Campaign', 'Kategori', 'Gate', 'Review', 'Catatan']}>
              {d.campaigns.map((c, i) => <tr key={i}><td className="td font-semibold">{c.name}</td><td className="td text-xs">{c.category}</td><td className="td"><GateBadge g={c.gateStatus} /></td><td className="td"><ReviewBadge r={c.review} /></td><td className="td text-xs">{c.reviewNote || <span className="text-brand">Belum direview</span>}</td></tr>)}
            </Table>
          </Section>
        </>
      )}
    </div>
  )
}

function PerCampaign() {
  const [month, setMonth] = useState(thisMonth())
  const { data: camps } = useApi(`/api/campaigns?month=${month}`)
  const [cid, setCid] = useState('')
  const { data: r } = useApi(cid ? `/api/reports/campaign/${cid}` : null)
  const toast = useToast()
  return (
    <div className="space-y-4">
      <div className="no-print flex flex-wrap items-center gap-2"><MonthPicker value={month} onChange={(m) => { setMonth(m); setCid('') }} />
        <select className="input w-auto" value={cid} onChange={(e) => setCid(e.target.value)}><option value="">Pilih campaign…</option>{(camps || []).map((c) => <option key={c.id} value={c.id}>{c.category} · {c.name}</option>)}</select>
        {cid && <><button className="btn-ghost" onClick={() => download(`/api/reports/campaign/${cid}?format=xlsx`, `KOL_Report_${r?.campaign.code}.xlsx`).catch((e) => toast(e.message, 'err'))}>Export Excel</button><button className="btn-ghost" onClick={() => window.print()}>Cetak / PDF</button></>}
      </div>
      {cid && r && (
        <div className="card space-y-4 p-5">
          <div><div className="text-xs text-ink/50">{r.campaign.code}</div><h2 className="text-lg font-extrabold">{r.campaign.name}</h2><div className="text-sm text-ink/60">{r.campaign.category} · {date(r.campaign.start)} – {date(r.campaign.end)} · {r.campaign.objective}</div></div>
          <div>
            <h3 className="mb-2 font-bold">Ringkasan</h3>
            <p className="text-sm">Biaya {rp(r.agg.cost)} untuk {r.agg.bookings} KOL menghasilkan {short(r.agg.views)} views (CPV {rp(r.agg.cpv)}), {num(r.agg.outcome)} {r.config.outcomeLabel.toLowerCase()}{r.config.evidence.includes('DIRECT') ? `, revenue DIRECT ${rp(r.agg.revenueDirect)} (ROI ${times(r.agg.roiDirect)})` : ''}{r.config.assisted ? `, dan estimasi uplift outlet ${rp(r.agg.revenueAssisted)} (ASSISTED)` : ''}.</p>
          </div>
          <Table head={['Metric', { label: 'Target', right: 1 }, { label: 'Actual', right: 1 }, { label: 'Achievement', right: 1 }]}>
            {r.pva.map((p) => { const f = p.fmt === 'rp' ? rp : p.fmt === 'x' ? times : num; return <tr key={p.metric}><td className="td">{p.metric}</td><td className="td text-right num">{p.target ? f(p.target) : '–'}</td><td className="td text-right num font-semibold">{f(p.actual)}</td><td className="td text-right num">{p.achievement == null ? '–' : pct(p.achievement, 0)}</td></tr> })}
          </Table>
          <Table head={['KOL', 'Status', { label: 'Biaya', right: 1 }, { label: 'Views', right: 1 }, { label: 'ER', right: 1 }, { label: 'Outcome', right: 1 }, { label: 'Cost/outcome', right: 1 }, { label: 'ROI DIRECT', right: 1 }, 'Catatan']}>
            {r.rows.map((x, i) => <tr key={i}><td className="td"><b>{x.kol}</b> <TierBadge t={x.tier} /><div className="text-[11px] text-ink/50">{x.code}</div></td><td className="td"><StatusBadge s={x.status} /></td><td className="td text-right num">{rpShort(x.cost)}</td><td className="td text-right num">{short(x.views)}</td><td className="td text-right num">{pct(x.er)}</td><td className="td text-right num">{num(x.outcome)}</td><td className="td text-right num">{rp(x.costPerOutcome)}</td><td className="td text-right num">{times(x.roiDirect)}</td><td className="td text-xs text-amber-700">{x.flags.join(' · ')}</td></tr>)}
          </Table>
          <div>
            <h3 className="mb-1 font-bold">Evaluation {r.campaign.review && <ReviewBadge r={r.campaign.review} />}</h3>
            {r.campaign.review ? <div className="grid gap-2 text-sm sm:grid-cols-3"><div><div className="label">What worked</div>{r.campaign.whatWorked || '–'}</div><div><div className="label">What didn’t</div>{r.campaign.whatDidnt || '–'}</div><div><div className="label">Next action</div>{r.campaign.nextAction || '–'}</div></div>
              : <p className="text-sm text-brand">Belum direview. <Link className="underline" to={`/campaign/${cid}`}>Isi review</Link></p>}
          </div>
        </div>
      )}
    </div>
  )
}

function Audit() {
  const { data, error } = useApi('/api/audit?limit=300')
  if (error) return <ErrorBox msg={error} />
  if (!data) return <Loading />
  return (
    <Section title="Audit log (300 terakhir)">
      <Table head={['Waktu', 'Oleh', 'Aksi', 'Ref', 'Perubahan', 'Alasan']}>
        {data.map((a) => <tr key={a.id}><td className="td text-xs whitespace-nowrap">{dateTime(a.at)}</td><td className="td text-xs">{a.by}<div className="text-ink/50">{a.role}</div></td><td className="td text-xs font-semibold">{a.what}</td><td className="td text-[11px] text-ink/50">{a.ref}</td>
          <td className="td max-w-md text-[11px]">{a.before && <div className="text-ink/50 break-all">sebelum: {JSON.stringify(a.before)}</div>}{a.after && <div className="break-all">sesudah: {JSON.stringify(a.after)}</div>}</td><td className="td text-xs">{a.reason}</td></tr>)}
      </Table>
    </Section>
  )
}
