import { Fragment, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, fileUrl } from '../api'
import { useApp } from '../App'
import { BookingForm } from '../components/forms'
import { ContentForm, SnapshotForm } from '../components/inputs'
import { Badge, ErrorBox, Loading, ReasonModal, Section, StatusBadge, STATUS_LABEL, Table, TierBadge, Tile, useApi, useToast, GateBadge } from '../components/ui'
import { date, dateTime, num, pct, rp, rpShort, short, times } from '../fmt'

export default function BookingPage() {
  const { id } = useParams()
  const { can, meta, user } = useApp()
  const toast = useToast()
  const { data: b, error, reload } = useApi(`/api/bookings/${id}`)
  const [edit, setEdit] = useState(false)
  const [addContent, setAddContent] = useState(false)
  const [snap, setSnap] = useState(null)
  const [reasonFor, setReasonFor] = useState(null)
  const [back, setBack] = useState('')
  if (error) return <ErrorBox msg={error} />
  if (!b) return <Loading />
  const m = b.metrics
  const editor = can('Manager', 'KOL TL', 'KOL Officer')
  const lead = can('Manager', 'KOL TL')
  const go = async (to, reason = '') => {
    try { await api(`/api/bookings/${id}/transition`, { method: 'POST', body: { to, reason } }); toast(`Status → ${STATUS_LABEL[to]}`); reload() }
    catch (e) { toast(e.message, 'err'); throw e }
  }
  const approve = async (decision, reason = '') => {
    try { await api(`/api/bookings/${id}/approve`, { method: 'POST', body: { to: decision, reason } }); toast(decision === 'approve' ? 'Disetujui' : 'Ditolak'); reload() }
    catch (e) { toast(e.message, 'err'); throw e }
  }
  const next = {
    SHORTLIST: [['NEGO', 'Mulai negosiasi']],
    NEGO: b.needsApproval && !b.hasApproval ? [['WAITING_APPROVAL', 'Minta approval Manager']] : [['DEAL', 'Tandai DEAL']],
    DEAL: [['BRIEF_SENT', 'Brief terkirim']], BRIEF_SENT: [['DRAFT_REVIEW', 'Draft diterima']],
    POSTED: [['REPORT_SUBMITTED', 'Submit report']], REPORT_DUE: [['REPORT_SUBMITTED', 'Submit report']],
  }[b.status] || []
  const fields = b.requiredFields
  const hasDirect = meta.categories[b.campaign.category]?.evidence.includes('DIRECT')
  return (
    <div className="space-y-4">
      <Link to={`/campaign/${b.campaign.id}`} className="text-sm font-semibold text-brand">‹ {b.campaign.name}</Link>
      <div className="card p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-2"><Link to={`/kol/${b.kol.id}`} className="text-xl font-extrabold hover:text-brand">{b.kol.name}</Link><TierBadge t={b.tierAtBooking} /><StatusBadge s={b.status} /></div>
            <div className="mt-1 text-sm text-ink/60">@{b.kol.handles?.[b.platform] || b.kol.handles?.tiktok} · {b.platform} · {b.campaign.category} · <GateBadge g={b.campaign.gateStatus} /></div>
            <div className="mt-2 flex flex-wrap gap-2 text-sm"><Badge tone="grey">Kode: <b className="ml-1">{b.uniqueCode}</b></Badge>{b.trackingLink && <a className="text-brand underline" href={b.trackingLink} target="_blank" rel="noreferrer">Link tracking</a>}</div>
          </div>
          <div className="flex flex-wrap gap-2">
            {editor && !['PAID', 'CANCELLED'].includes(b.status) && next.map(([to, label]) => <button key={to} className="btn-primary" disabled={to === 'REPORT_SUBMITTED' && !m.reportComplete} title={to === 'REPORT_SUBMITTED' && !m.reportComplete ? 'Lengkapi snapshot H+7 dulu' : ''} onClick={() => go(to).catch(() => {})}>{label}</button>)}
            {editor && ['DEAL', 'BRIEF_SENT', 'DRAFT_REVIEW', 'POSTED', 'REPORT_DUE'].includes(b.status) && <button className={b.status === 'DRAFT_REVIEW' || b.status === 'DEAL' || b.status === 'BRIEF_SENT' ? 'btn-primary' : 'btn-ghost'} onClick={() => setAddContent(true)}>+ Link konten tayang</button>}
            {user.role === 'Manager' && b.status === 'WAITING_APPROVAL' && <><button className="btn-ok" onClick={() => approve('approve', 'OK').catch(() => {})}>Approve & DEAL</button><button className="btn-ghost" onClick={() => setReasonFor('reject')}>Tolak</button></>}
            {lead && b.status === 'REPORT_SUBMITTED' && <><button className="btn-ok" onClick={() => go('REPORT_APPROVED').catch(() => {})}>Approve report</button><button className="btn-ghost" onClick={() => setReasonFor('rejectReport')}>Kembalikan</button></>}
            {editor && <button className="btn-ghost" onClick={() => setEdit(true)}>Edit</button>}
            {editor && !['PAID', 'CANCELLED'].includes(b.status) && <button className="btn-ghost text-brand" onClick={() => setReasonFor('cancel')}>Batalkan</button>}
          </div>
        </div>
        {b.status === 'WAITING_APPROVAL' && user.role !== 'Manager' && <p className="mt-3 rounded-xl bg-amber-50 px-3 py-2 text-sm text-amber-800">Menunggu approval Manager (tier {b.tierAtBooking} / biaya di atas batas).</p>}
        {b.status === 'REPORT_APPROVED' && <p className="mt-3 rounded-xl bg-green-50 px-3 py-2 text-sm text-ok">Report sudah di-approve {b.reportApprovedBy}. Booking masuk antrean pelunasan Finance.</p>}
        {['POSTED', 'REPORT_DUE'].includes(b.status) && !m.reportComplete && <p className="mt-3 rounded-xl bg-red-50 px-3 py-2 text-sm text-brand">Report belum lengkap: isi snapshot H+7 (dengan screenshot) untuk setiap konten sebelum submit. Tanpa report, KOL tidak bisa dilunasi.</p>}
        {lead && !['SHORTLIST', 'CANCELLED'].includes(b.status) && (
          <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-brand-line pt-3 text-xs">
            <span className="text-ink/60">Mundurkan status (KOL TL/Manager):</span>
            <select className="input w-auto min-h-[36px] text-sm" value={back} onChange={(e) => setBack(e.target.value)}>
              <option value="">Pilih…</option>{meta.statuses.slice(0, meta.statuses.indexOf(b.status)).filter((s) => s !== 'REPORT_DUE').map((s) => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}
            </select>
            {back && <button className="btn-ghost btn-sm" onClick={() => setReasonFor('back')}>Mundurkan</button>}
          </div>
        )}
      </div>

      {m.flags.length > 0 && <div className="flex flex-wrap gap-1.5">{m.flags.map((f) => <Badge key={f.code} tone={f.level === 'red' ? 'red' : 'amber'}>⚠ {f.label}</Badge>)}</div>}

      <div className="grid grid-cols-2 gap-2 md:grid-cols-6">
        <Tile label="Total biaya" value={rpShort(m.cost)} sub={`Fee ${rpShort(b.costs.feeRp)}`} />
        <Tile label="Views" value={short(m.views)} sub={`CPV ${rp(m.cpv)} (bench ${rp(m.benchmark.cpv)})`} />
        <Tile label="ER" value={pct(m.er)} sub={`bench ${pct(m.benchmark.er)}`} />
        <Tile label={m.outcomeLabel} value={num(m.outcome)} sub={`${rp(m.costPerOutcome)}/outcome (bench ${rp(m.benchmark.cpo)})`} />
        <Tile label="Revenue DIRECT" value={hasDirect ? rpShort(m.revenueDirect) : '–'} sub={m.roas != null ? `ROAS ${times(m.roas)}` : (m.revenueAssisted ? `ASSISTED ${rpShort(m.revenueAssisted)}` : (!hasDirect ? 'Kategori tanpa DIRECT' : ''))} />
        <Tile label="ROI DIRECT" value={hasDirect ? times(m.roiDirect) : '–'} sub={m.revenueAssisted ? `+ASSISTED ${times(m.roiTotal)}` : ''} />
      </div>

      <Section title="Konten & metrik" right={editor && ['DEAL', 'BRIEF_SENT', 'DRAFT_REVIEW', 'POSTED', 'REPORT_DUE'].includes(b.status) && <button className="btn-ghost btn-sm" onClick={() => setAddContent(true)}>+ Konten</button>}>
        {!b.contents.length ? <p className="text-sm text-ink/50">Belum ada konten tayang.</p> : b.contents.map((ct) => (
          <div key={ct.id} className="mb-4 last:mb-0">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <a href={ct.url} target="_blank" rel="noreferrer" className="max-w-full truncate text-sm font-semibold text-brand underline">{ct.url}</a>
              <Badge tone={ct.status === 'Live' ? 'green' : 'red'}>{ct.status}</Badge>
              <span className="text-xs text-ink/60">tayang {date(ct.postedAt)}{ct.handleMismatchReason && ` · handle beda: ${ct.handleMismatchReason}`}</span>
              {editor && <button className="btn-primary btn-sm ml-auto" onClick={() => setSnap(ct)}>Isi / ubah metrik</button>}
              {editor && ct.status === 'Live' && <button className="btn-ghost btn-sm" onClick={async () => { await api(`/api/contents/${ct.id}`, { method: 'PUT', body: { ...ct, bookingId: b.id, status: 'Dihapus' } }); toast('Ditandai dihapus'); reload() }}>Tandai dihapus</button>}
            </div>
            <Table head={['Snapshot', ...fields.map((f) => ({ label: meta.metricLabels[f], right: 1 })), 'Bukti', 'Diisi']}>
              {['H1', 'H3', 'H7', 'H30'].map((d) => {
                const s = ct.snapshots.find((x) => x.day === d)
                return (
                  <tr key={d} className={!s ? 'text-ink/40' : ''}>
                    <td className="td font-semibold">{d.replace('H', 'H+')} {s?.locked && '🔒'}</td>
                    {fields.map((f) => <td key={f} className="td text-right num">{s ? (f.endsWith('Rp') ? rpShort(s[f]) : f === 'audienceLocalPct' ? s[f] + '%' : num(s[f])) : '–'}</td>)}
                    <td className="td">{s?.proofFiles?.map((p) => <a key={p} href={fileUrl(p)} target="_blank" rel="noreferrer" className="mr-1 text-xs text-brand underline">foto</a>)}</td>
                    <td className="td text-xs">{s ? `${s.enteredBy}` : ''}</td>
                  </tr>
                )
              })}
            </Table>
          </div>
        ))}
      </Section>

      <div className="grid gap-4 lg:grid-cols-3">
        <Section title="Biaya & deliverables">
          <dl className="grid grid-cols-2 gap-y-1 text-sm">
            {[['Fee', b.costs.feeRp], ['Produk', b.costs.productRp], ['Transport', b.costs.transportRp], ['Lainnya', b.costs.otherRp]].map(([k, v]) => <Fragment key={k}><dt className="text-ink/60">{k}</dt><dd className="text-right num">{rp(v || 0)}</dd></Fragment>)}
            {b.costs.commissionPct ? <><dt className="text-ink/60">Komisi</dt><dd className="text-right">{b.costs.commissionPct}% (dari report)</dd></> : null}
            <dt className="font-bold">Total kontrak</dt><dd className="text-right font-bold num">{rp(b.totalCostRp)}</dd>
          </dl>
          <div className="mt-3 space-y-1 text-sm">{b.deliverables.map((d, i) => <div key={i} className="flex justify-between"><span>{d.qty}× {d.format}</span><span className="text-ink/60">due {date(d.dueDate)}</span></div>)}</div>
          <div className="mt-2 text-xs text-ink/60">Hak repost {b.contentRights?.repostDays || 0} hari · Ads: {b.contentRights?.adsUsage ? 'boleh' : 'tidak'}</div>
        </Section>
        <Section title="Pembayaran">
          <dl className="grid grid-cols-2 gap-y-1 text-sm">
            <dt className="text-ink/60">DP</dt><dd className="text-right num">{rp(b.payment?.dpRp || 0)}</dd>
            <dt className="text-ink/60">Pelunasan</dt><dd className="text-right num">{rp(b.payment?.paidRp || 0)}</dd>
            <dt className="text-ink/60">Tanggal lunas</dt><dd className="text-right">{b.payment?.paidAt ? date(b.payment.paidAt) : '–'}</dd>
          </dl>
          {b.payment?.overrideReason && <p className="mt-2 text-xs text-brand">Override Manager: {b.payment.overrideReason}</p>}
          <p className="mt-3 text-xs text-ink/50">Pelunasan hanya bisa dilakukan Finance setelah report H+7 di-approve KOL TL.</p>
        </Section>
        <Section title="Approval & riwayat">
          {b.approvals?.map((a, i) => <div key={i} className="mb-1 text-sm"><Badge tone={a.decision === 'reject' ? 'red' : 'green'}>{a.decision === 'reject' ? 'Ditolak' : 'Disetujui'}</Badge> {a.by} · {dateTime(a.at)}{a.note && ` — ${a.note}`}</div>)}
          <ol className="mt-2 max-h-56 space-y-1 overflow-y-auto text-xs">
            {[...(b.history || [])].reverse().map((h, i) => <li key={i}><b>{STATUS_LABEL[h.to] || h.to}</b> · {h.by} · {dateTime(h.at)}{h.reason && <span className="text-ink/60"> — {h.reason}</span>}</li>)}
          </ol>
        </Section>
      </div>
      <BookingForm open={edit} onClose={() => setEdit(false)} initial={b} onSaved={reload} />
      <ContentForm open={addContent} onClose={() => setAddContent(false)} booking={b} onSaved={reload} />
      <SnapshotForm open={!!snap} onClose={() => setSnap(null)} content={snap} fields={fields} category={b.campaign.category} onSaved={reload} />
      <ReasonModal open={reasonFor === 'cancel'} danger title="Batalkan booking" confirmText="Batalkan" onClose={() => setReasonFor(null)} onSubmit={async (r) => { await go('CANCELLED', r); setReasonFor(null) }} />
      <ReasonModal open={reasonFor === 'reject'} danger title="Tolak booking" confirmText="Tolak" onClose={() => setReasonFor(null)} onSubmit={async (r) => { await approve('reject', r); setReasonFor(null) }} />
      <ReasonModal open={reasonFor === 'rejectReport'} danger title="Kembalikan report ke officer" label="Apa yang perlu diperbaiki?" confirmText="Kembalikan" onClose={() => setReasonFor(null)} onSubmit={async (r) => { await go('POSTED', r); setReasonFor(null) }} />
      <ReasonModal open={reasonFor === 'back'} title={`Mundurkan ke ${STATUS_LABEL[back] || ''}`} confirmText="Mundurkan" onClose={() => setReasonFor(null)} onSubmit={async (r) => { await go(back, r); setReasonFor(null); setBack('') }} />
    </div>
  )
}
