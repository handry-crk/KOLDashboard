import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { download } from '../api'
import { Dot, EvidenceBadge, EVIDENCE_HELP, Insight, Loading, ErrorBox, MonthPicker, Section, Tile, TierBadge, StatusBadge, Table, useApi, useToast, Badge } from '../components/ui'
import { num, pct, rp, rpShort, short, thisMonth, times, monthLabel } from '../fmt'

export const C_COST = '#2F6DB5'
export const C_REV = '#D7191F'

function ChartTip({ active, payload, label, fmt = rpShort }) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-xl border border-brand-line bg-white px-3 py-2 text-xs shadow-md">
      <div className="mb-1 font-bold">{label}</div>
      {payload.map((p) => <div key={p.dataKey} className="flex items-center gap-2"><span className="h-2 w-2 rounded-sm" style={{ background: p.color }} /><span className="text-ink/70">{p.name}</span><span className="ml-auto pl-3 font-semibold num">{fmt(p.value)}</span></div>)}
    </div>
  )
}

const STATUS_TEXT = { green: 'Sesuai benchmark', amber: 'Waspada (≤1,5× benchmark)', red: 'Di atas benchmark', grey: 'Belum ada data' }

export default function Ringkasan() {
  const [month, setMonth] = useState(thisMonth())
  const { data: d, error, loading } = useApi(`/api/reports/direksi?month=${month}`)
  const toast = useToast()
  const nav = useNavigate()
  const [showFlags, setShowFlags] = useState(false)
  const exp = async (f) => { try { await download(`/api/reports/direksi?month=${month}&format=${f}`, `KOL_Laporan_Direksi_${month}.${f}`) } catch (e) { toast(e.message, 'err') } }
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div><h1 className="text-xl font-extrabold">Ringkasan Direksi</h1><p className="text-sm text-ink/60">Akuntabilitas budget KOL & dampak per objective</p></div>
        <div className="no-print flex flex-wrap items-center gap-2">
          <MonthPicker value={month} onChange={setMonth} />
          <button className="btn-ghost" onClick={() => exp('xlsx')}>Export Excel</button>
          <button className="btn-primary" onClick={() => exp('pdf')}>Export Laporan Direksi (PDF)</button>
        </div>
      </div>
      <ErrorBox msg={error} />
      {loading && !d ? <Loading /> : d && <Body d={d} month={month} nav={nav} showFlags={showFlags} setShowFlags={setShowFlags} />}
    </div>
  )
}

function Body({ d, month, nav, showFlags, setShowFlags }) {
  const t = d.tiles
  const flagsRef = () => { setShowFlags(true); setTimeout(() => document.getElementById('perlu-dicek')?.scrollIntoView({ behavior: 'smooth' }), 50) }
  return (
    <>
      <div className="grid grid-cols-2 gap-2 md:grid-cols-4 xl:grid-cols-8">
        <div className="card col-span-2 p-3">
          <div className="text-[11px] font-semibold uppercase tracking-wide text-ink/60">Budget KOL {monthLabel(month)}</div>
          <div className="mt-1 flex items-baseline gap-2"><span className="text-xl font-extrabold num">{rpShort(t.committed)}</span><span className="text-xs text-ink/60">committed dari {rpShort(t.pagu)}</span></div>
          <div className="mt-2 h-2.5 overflow-hidden rounded-full bg-brand-soft">
            <div className="h-full bg-brand" style={{ width: `${Math.min(100, (t.committed / (t.pagu || 1)) * 100)}%` }} />
          </div>
          <div className="mt-1 text-xs text-ink/60">Dibayar (DP + lunas): {rpShort(t.paid)}</div>
        </div>
        <Tile label="Konten tayang" value={num(t.contents)} sub={`${short(t.views)} views`} />
        <Tile label="Revenue DIRECT" value={rpShort(t.revenueDirect)} sub={`ASSISTED ${rpShort(t.revenueAssisted)} (terpisah)`} help={EVIDENCE_HELP.DIRECT} />
        <Tile label="ROI DIRECT (GM)" value={times(t.roiDirect)} sub={`+ASSISTED: ${times(t.roiTotal)}`} help="Revenue × GM blended ÷ biaya" />
        <Tile label="ROAS" value={times(t.roas)} sub="Frozen + K. Kuning + TT GO" />
        <Tile label="Report compliance" value={pct(t.compliance, 0)} sub={`${t.approvedCount}/${t.dueCount} lewat H+7`} />
        <Tile label="Booking tanpa report" value={num(t.noReport)} sub={rpShort(t.noReportCost) + ' tertahan'} tone={t.noReport ? 'red' : undefined} onClick={flagsRef} />
      </div>
      {d.insights.summary?.length > 0 && (
        <div className="card p-4"><ul className="space-y-1 text-sm">{d.insights.summary.map((s, i) => <li key={i}>• {s}</li>)}</ul>
          <p className="mt-2 text-xs text-ink/50">ROI = revenue × GM blended {pct(d.gm, 0)} ÷ biaya. <EvidenceBadge e="DIRECT" /> {EVIDENCE_HELP.DIRECT}. <EvidenceBadge e="ASSISTED" /> {EVIDENCE_HELP.ASSISTED}. <EvidenceBadge e="EXPOSURE" /> {EVIDENCE_HELP.EXPOSURE}. Tidak pernah dijumlahkan menjadi satu ROI.</p>
        </div>
      )}

      <Section title="Per kategori (objective)">
        <Table head={['Kategori', 'Bukti', { label: 'Plan', right: 1 }, { label: 'Spend', right: 1 }, { label: '# KOL', right: 1 }, { label: 'Views', right: 1 }, { label: 'CPV (bench)', right: 1 }, 'Outcome utama', { label: 'Cost/outcome (bench)', right: 1 }, { label: 'Rev. DIRECT', right: 1 }, { label: 'Rev. ASSISTED', right: 1 }, { label: 'ROI DIRECT', right: 1 }, { label: 'ROI +ASS.', right: 1 }, { label: 'ROAS', right: 1 }, 'Status']}>
          {d.categories.map((c) => (
            <tr key={c.category} className="hover:bg-brand-soft">
              <td className="td"><div className="font-semibold">{c.category}</div><div className="text-[11px] text-ink/50 max-w-[180px]">{c.objective}</div></td>
              <td className="td"><div className="flex flex-col gap-1">{c.evidence.map((e) => <EvidenceBadge key={e} e={e} />)}</div></td>
              <td className="td text-right num">{rpShort(c.planned)}</td>
              <td className="td text-right num font-semibold">{rpShort(c.spend)}</td>
              <td className="td text-right num">{c.kols}</td>
              <td className="td text-right num">{short(c.views)}</td>
              <td className="td text-right num">{rp(c.cpv)} <span className="text-ink/40">({rp(c.benchCpv)})</span></td>
              <td className="td"><span className="num font-semibold">{num(c.outcome)}</span> <span className="text-xs text-ink/60">{c.outcomeLabel}</span>{c.skuUplift > 0 && <div className="text-[11px] text-amber-700">+{num(c.skuUplift)} unit SKU (assisted)</div>}</td>
              <td className="td text-right num">{rp(c.costPerOutcome)} <span className="text-ink/40">({rp(c.benchCpo)})</span></td>
              <td className="td text-right num">{c.evidence.includes('DIRECT') ? rpShort(c.revenueDirect) : '–'}</td>
              <td className="td text-right num">{c.evidence.includes('ASSISTED') ? rpShort(c.revenueAssisted) : '–'}</td>
              <td className="td text-right num font-semibold">{c.evidence.includes('DIRECT') ? times(c.roiDirect) : '–'}</td>
              <td className="td text-right num">{c.evidence.includes('ASSISTED') ? times(c.roiTotal) : '–'}</td>
              <td className="td text-right num">{times(c.roas)}</td>
              <td className="td"><span className="inline-flex items-center gap-1.5 text-xs"><Dot c={c.status} />{STATUS_TEXT[c.status]}</span></td>
            </tr>
          ))}
        </Table>
        <p className="mt-2 text-[11px] text-ink/50">Benchmark masih *angka ilustrasi — kalibrasi di Pengaturan setelah 8 minggu data. Status = cost per outcome vs benchmark tertimbang biaya (tier yang dipakai).</p>
      </Section>

      <div className="grid gap-4 lg:grid-cols-2">
        <Section title="Biaya vs revenue DIRECT per minggu">
          {d.weekly.length ? (
            <div className="h-64">
              <ResponsiveContainer>
                <BarChart data={d.weekly} barGap={2} margin={{ left: 0, right: 8, top: 8 }}>
                  <CartesianGrid stroke="#EFE6E6" vertical={false} />
                  <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#6b6060' }} tickLine={false} axisLine={{ stroke: '#EBD9DA' }} tickFormatter={(v) => 'Mg ' + v} />
                  <YAxis tickFormatter={(v) => rpShort(v).replace('Rp', '')} tick={{ fontSize: 11, fill: '#6b6060' }} tickLine={false} axisLine={false} width={48} />
                  <Tooltip content={<ChartTip />} cursor={{ fill: '#FBF1F1' }} />
                  <Legend iconType="square" wrapperStyle={{ fontSize: 12 }} />
                  <Bar dataKey="spend" name="Biaya KOL" fill={C_COST} radius={[4, 4, 0, 0]} maxBarSize={28} />
                  <Bar dataKey="revenueDirect" name="Revenue DIRECT" fill={C_REV} radius={[4, 4, 0, 0]} maxBarSize={28} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : <p className="text-sm text-ink/50">Belum ada konten tayang.</p>}
          <Insight>{d.insights.weekly}</Insight>
        </Section>
        <Section title="CPV per tier">
          <div className="h-64">
            <ResponsiveContainer>
              <BarChart data={d.tiers.filter((x) => x.cpv)} margin={{ left: 0, right: 8, top: 16 }}>
                <CartesianGrid stroke="#EFE6E6" vertical={false} />
                <XAxis dataKey="tier" tick={{ fontSize: 12, fill: '#6b6060' }} tickLine={false} axisLine={{ stroke: '#EBD9DA' }} />
                <YAxis tickFormatter={(v) => 'Rp' + v} tick={{ fontSize: 11, fill: '#6b6060' }} tickLine={false} axisLine={false} width={52} />
                <Tooltip content={<ChartTip fmt={rp} />} cursor={{ fill: '#FBF1F1' }} />
                <Bar dataKey="cpv" name="CPV" fill="#B32E26" radius={[4, 4, 0, 0]} maxBarSize={44} label={{ position: 'top', fontSize: 11, fill: '#1F1A1A', formatter: (v) => rp(v) }} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <Insight>{d.insights.tier}</Insight>
        </Section>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Section title="Per tier">
          <Table head={['Tier', { label: 'Booking', right: 1 }, { label: 'Spend', right: 1 }, { label: 'Share', right: 1 }, { label: 'CPV', right: 1 }, { label: 'ER', right: 1 }, { label: 'Rev. DIRECT', right: 1 }, { label: 'Share rev.', right: 1 }, { label: 'Indeks*', right: 1 }]}>
            {d.tiers.map((x) => (
              <tr key={x.tier}>
                <td className="td"><TierBadge t={x.tier} /></td><td className="td text-right num">{x.bookings}</td><td className="td text-right num">{rpShort(x.spend)}</td>
                <td className="td text-right num">{pct(x.spendShare, 0)}</td><td className="td text-right num">{rp(x.cpv)}</td><td className="td text-right num">{pct(x.er)}</td>
                <td className="td text-right num">{rpShort(x.revenueDirect)}</td><td className="td text-right num">{pct(x.revenueShare, 0)}</td><td className="td text-right num">{times(x.effIndex)}</td>
              </tr>
            ))}
          </Table>
          <p className="mt-2 text-[11px] text-ink/50">*Indeks efisiensi = benchmark cost per outcome ÷ aktual. ≥ 1,0× lebih efisien dari benchmark.</p>
        </Section>
        <Section title="Funnel per kategori">
          <Table head={['Kategori', { label: 'Views', right: 1 }, { label: 'Klik / voucher', right: 1 }, 'Outcome', { label: 'Konversi', right: 1 }, { label: 'Rev. DIRECT', right: 1 }]}>
            {d.funnel.map((f) => (
              <tr key={f.category}>
                <td className="td font-semibold">{f.category}</td><td className="td text-right num">{short(f.views)}</td><td className="td text-right num">{f.clicks ? short(f.clicks) : '–'}</td>
                <td className="td"><span className="num font-semibold">{num(f.outcome)}</span> <span className="text-[11px] text-ink/60">{f.outcomeLabel}</span></td>
                <td className="td text-right num">{f.outcomeLabel === 'Views' ? '–' : pct(f.views ? f.outcome / f.views : null, 2)}</td>
                <td className="td text-right num">{f.revenueDirect ? rpShort(f.revenueDirect) : '–'}</td>
              </tr>
            ))}
          </Table>
          <Insight>{d.insights.funnel}</Insight>
        </Section>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <RankTable title="Top 5 KOL" rows={d.top} nav={nav} />
        <RankTable title="Bottom 5 KOL" rows={d.bottom} nav={nav} />
      </div>

      <Section title={<span id="perlu-dicek">Perlu dicek <Badge tone="red">{d.flags.length}</Badge></span>} right={<button className="btn-ghost btn-sm no-print" onClick={() => setShowFlags(!showFlags)}>{showFlags ? 'Ringkas' : 'Lihat semua'}</button>}>
        {d.flags.length === 0 ? <p className="text-sm text-ink/50">Tidak ada yang perlu dicek. 👍</p> : (
          <div className="divide-y divide-brand-line">
            {(showFlags ? d.flags : d.flags.slice(0, 6)).map((f, i) => (
              <div key={i} className={`flex flex-wrap items-center gap-2 py-2 ${f.bookingId ? 'cursor-pointer hover:bg-brand-soft' : ''}`} onClick={() => f.bookingId && nav(`/booking/${f.bookingId}`)}>
                <div className="min-w-[160px] font-semibold text-sm">{f.kol || f.campaign}</div>
                {f.kol && <div className="text-xs text-ink/60">{f.campaign}</div>}
                {f.status && <StatusBadge s={f.status} />}
                <div className="flex flex-wrap gap-1">{f.flags.map((x) => <Badge key={x.code} tone={x.level === 'red' ? 'red' : 'amber'}>{x.label}</Badge>)}</div>
                <div className="ml-auto text-sm num text-ink/70">{rpShort(f.cost)}</div>
              </div>
            ))}
          </div>
        )}
      </Section>
    </>
  )
}

function RankTable({ title, rows, nav }) {
  return (
    <Section title={title}>
      {!rows.length ? <p className="text-sm text-ink/50">Belum cukup booking dengan report lengkap.</p> : (
        <Table head={['KOL', 'Kategori', { label: 'Biaya', right: 1 }, { label: 'Cost/outcome', right: 1 }, { label: 'Bench', right: 1 }, { label: 'Indeks', right: 1 }]}>
          {rows.map((r) => (
            <tr key={r.bookingId} className="cursor-pointer hover:bg-brand-soft" onClick={() => nav(`/booking/${r.bookingId}`)}>
              <td className="td"><div className="font-semibold">{r.kol}</div><TierBadge t={r.tier} /></td>
              <td className="td text-xs">{r.category}<div className="text-ink/50">{num(r.outcome)} {r.outcomeLabel?.toLowerCase()}</div></td>
              <td className="td text-right num">{rpShort(r.cost)}</td><td className="td text-right num">{rp(r.costPerOutcome)}</td>
              <td className="td text-right num text-ink/50">{rp(r.benchCpo)}</td>
              <td className={`td text-right num font-bold ${r.index >= 1 ? 'text-ok' : r.index < 0.5 ? 'text-brand' : ''}`}>{times(r.index)}</td>
            </tr>
          ))}
        </Table>
      )}
    </Section>
  )
}
