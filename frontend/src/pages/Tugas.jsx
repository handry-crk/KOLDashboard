import { Link } from 'react-router-dom'
import { useApp } from '../App'
import { Badge, ErrorBox, Loading, Section, useApi } from '../components/ui'
import { date, rpShort } from '../fmt'

function Item({ to, title, sub, badge, tone }) {
  return (
    <Link to={to} className="flex items-center gap-3 border-b border-brand-line py-3 last:border-0 hover:bg-brand-soft">
      <div className="min-w-0 flex-1"><div className="truncate text-sm font-bold">{title}</div><div className="truncate text-xs text-ink/60">{sub}</div></div>
      {badge && <Badge tone={tone}>{badge}</Badge>}<span className="text-ink/40">›</span>
    </Link>
  )
}

export default function Tugas() {
  const { user } = useApp()
  const { data: t, error, loading } = useApi('/api/tasks')
  if (error) return <ErrorBox msg={error} />
  if (loading && !t) return <Loading />
  const regs = t.registrations || []
  const total = t.snapshots.length + t.deliverables.length + t.approvals.length + t.reports.length + t.payments.length + regs.length
  return (
    <div className="space-y-4">
      <div><h1 className="text-xl font-extrabold">Halo, {user.name.split(' ')[0]} 👋</h1><p className="text-sm text-ink/60">{total ? `${total} hal perlu ditindaklanjuti hari ini` : 'Semua beres untuk hari ini.'}</p></div>
      {regs.length > 0 && (
        <Section title={`Pendaftar baru menunggu approval (${regs.length})`}>
          {regs.map((r) => <Item key={r.id} to="/pengaturan#pendaftar" title={`${r.name} · ${r.role === 'KOL TL' ? 'KOL Team Leader' : r.role}`} sub={`${r.email} · ${date(r.registeredAt)}`} badge="Approval" tone="amber" />)}
        </Section>
      )}
      {t.snapshots.length > 0 && (
        <Section title={`Isi metrik (${t.snapshots.length})`}>
          {t.snapshots.map((s) => <Item key={s.contentId + s.day} to={`/input?b=${s.bookingId}&c=${s.contentId}&d=${s.day}`} title={`${s.kol} · ${s.day.replace('H', 'H+')}`} sub={`${s.campaign} · due ${date(s.dueDate)}`} badge={s.late ? 'Terlambat' : 'Hari ini'} tone={s.late ? 'red' : 'amber'} />)}
        </Section>
      )}
      {t.deliverables.length > 0 && (
        <Section title={`Deliverable mendekati due (${t.deliverables.length})`}>
          {t.deliverables.map((d, i) => <Item key={i} to={`/booking/${d.bookingId}`} title={`${d.kol} · ${d.format}`} sub={`${d.campaign} · due ${date(d.dueDate)}`} badge={d.late ? 'Lewat due' : 'Segera'} tone={d.late ? 'red' : 'amber'} />)}
        </Section>
      )}
      {t.approvals.length > 0 && (
        <Section title={`Menunggu approval Anda (${t.approvals.length})`}>
          {t.approvals.map((a) => <Item key={a.bookingId} to={`/booking/${a.bookingId}`} title={`${a.kol} (${a.tier})`} sub={`${a.campaign} · ${rpShort(a.cost)}`} badge="Approval" tone="amber" />)}
        </Section>
      )}
      {t.reports.length > 0 && (
        <Section title={`Report perlu di-approve (${t.reports.length})`}>
          {t.reports.map((a) => <Item key={a.bookingId} to={`/booking/${a.bookingId}`} title={a.kol} sub={`${a.campaign} · ${a.category}`} badge="Review" tone="amber" />)}
        </Section>
      )}
      {t.payments.length > 0 && (
        <Section title={`Siap dilunasi (${t.payments.length})`}>
          {t.payments.map((a) => <Item key={a.bookingId} to="/pembayaran" title={a.kol} sub={`${a.campaign} · ${rpShort(a.cost)}`} badge="Lunasi" tone="green" />)}
        </Section>
      )}
      {!total && <div className="card p-8 text-center text-sm text-ink/60">✅ Tidak ada tugas tertunda.</div>}
    </div>
  )
}
