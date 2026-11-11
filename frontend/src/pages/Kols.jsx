import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api'
import { RATE_ITEMS } from '../components/forms'
import { useApp } from '../App'
import { Badge, Empty, ErrorBox, Field, Loading, Modal, MoneyInput, ReviewBadge, Section, StatusBadge, Table, TierBadge, Tile, useApi, useToast } from '../components/ui'
import { num, pct, rp, rpShort, short, times } from '../fmt'

const NICHES = ['Kuliner', 'Lifestyle', 'Mom', 'Mahasiswa', 'Komedi', 'Review jujur', 'Lokal Bandung', 'Lokal Jabodetabek']

export default function Kols() {
  const { meta, can } = useApp()
  const { data, error, loading, reload } = useApi('/api/kols')
  const [q, setQ] = useState('')
  const [tier, setTier] = useState('')
  const [status, setStatus] = useState('')
  const [open, setOpen] = useState(false)
  const nav = useNavigate()
  const rows = useMemo(() => (data || []).filter((k) => (!tier || k.tier === tier) && (!status || k.status === status) &&
    `${k.name} ${Object.values(k.handles || {}).join(' ')} ${k.city} ${(k.niche || []).join(' ')}`.toLowerCase().includes(q.toLowerCase())), [data, q, tier, status])
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-xl font-extrabold">Database KOL <span className="text-base font-semibold text-ink/50">{data?.length || ''}</span></h1>
        {can('Manager', 'KOL TL', 'KOL Officer') && <button className="btn-primary" onClick={() => setOpen(true)}>+ KOL</button>}
      </div>
      <div className="flex flex-wrap gap-2">
        <input className="input max-w-xs" placeholder="Cari nama, handle, kota, niche…" value={q} onChange={(e) => setQ(e.target.value)} />
        <select className="input w-auto" value={tier} onChange={(e) => setTier(e.target.value)}><option value="">Semua tier</option>{meta.tiers.map((t) => <option key={t}>{t}</option>)}</select>
        <select className="input w-auto" value={status} onChange={(e) => setStatus(e.target.value)}><option value="">Semua status</option>{['Aktif', 'Watchlist', 'Blacklist'].map((t) => <option key={t}>{t}</option>)}</select>
      </div>
      <ErrorBox msg={error} />
      {loading && !data ? <Loading /> : !rows.length ? <Empty>Tidak ada KOL yang cocok.</Empty> : (
        <>
          <div className="grid gap-2 md:hidden">
            {rows.map((k) => (
              <button key={k.id} onClick={() => nav(`/kol/${k.id}`)} className="card p-3 text-left">
                <div className="flex items-center justify-between"><span className="font-bold">{k.name}</span><TierBadge t={k.tier} /></div>
                <div className="text-xs text-ink/60">@{k.handles?.tiktok} · {short(k.followers?.[k.primaryPlatform])} · {k.city}</div>
                <div className="mt-1 flex flex-wrap items-center gap-1.5 text-xs">{k.status !== 'Aktif' && <Badge tone={k.status === 'Blacklist' ? 'red' : 'amber'}>{k.status}</Badge>}<ReviewBadge r={k.recommendation} /><span className="text-ink/60">{k.stats.bookings} booking · CPV {rp(k.stats.avgCpv)}</span></div>
              </button>
            ))}
          </div>
          <div className="hidden md:block">
            <Table head={['KOL', 'Tier', { label: 'Follower', right: 1 }, 'Kota / niche', { label: 'Booking', right: 1 }, { label: 'Spend', right: 1 }, { label: 'Avg CPV', right: 1 }, { label: 'Avg ER', right: 1 }, { label: 'Rev. DIRECT', right: 1 }, 'Rekomendasi', 'Catatan']}>
              {rows.map((k) => (
                <tr key={k.id} className="cursor-pointer hover:bg-brand-soft" onClick={() => nav(`/kol/${k.id}`)}>
                  <td className="td"><div className="font-semibold">{k.name}</div><div className="text-xs text-ink/50">@{k.handles?.tiktok || k.handles?.instagram}</div></td>
                  <td className="td"><TierBadge t={k.tier} />{k.tierOverride && <span className="ml-1 text-[10px] text-ink/50">override</span>}</td>
                  <td className="td text-right num">{short(k.followers?.[k.primaryPlatform])}</td>
                  <td className="td text-xs">{k.city}<div className="text-ink/50">{(k.niche || []).join(', ')}</div></td>
                  <td className="td text-right num">{k.stats.bookings}</td><td className="td text-right num">{rpShort(k.stats.spend)}</td>
                  <td className="td text-right num">{rp(k.stats.avgCpv)}</td><td className="td text-right num">{pct(k.stats.avgEr)}</td>
                  <td className="td text-right num">{rpShort(k.stats.revenueDirect)}</td>
                  <td className="td">{k.status === 'Blacklist' ? <Badge tone="red">Blacklist</Badge> : <ReviewBadge r={k.recommendation} />}</td>
                  <td className="td text-xs text-amber-700">{[k.stats.lateReports ? `${k.stats.lateReports} report telat` : '', ...k.stats.flags.filter((f) => !f.startsWith('Report')).slice(0, 2)].filter(Boolean).join(' · ')}</td>
                </tr>
              ))}
            </Table>
          </div>
        </>
      )}
      <KolForm open={open} onClose={() => setOpen(false)} onSaved={(k) => { reload(); nav(`/kol/${k.id}`) }} />
    </div>
  )
}

export function KolDetail() {
  const { id } = useParams()
  const { can, meta } = useApp()
  const { data: k, error, reload } = useApi(`/api/kols/${id}`)
  const [edit, setEdit] = useState(false)
  const nav = useNavigate()
  if (error) return <ErrorBox msg={error} />
  if (!k) return <Loading />
  const live = k.history.filter((h) => h.booking.status !== 'CANCELLED')
  const spend = live.reduce((a, h) => a + h.metrics.cost, 0)
  const views = live.reduce((a, h) => a + h.metrics.views, 0)
  const flags = [...new Set(live.flatMap((h) => h.metrics.flags.map((f) => f.label)))]
  return (
    <div className="space-y-4">
      <Link to="/kol" className="text-sm font-semibold text-brand">‹ Database KOL</Link>
      <div className="card p-4">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <div className="flex flex-wrap items-center gap-2"><h1 className="text-xl font-extrabold">{k.name}</h1><TierBadge t={k.tier} />{k.status !== 'Aktif' && <Badge tone={k.status === 'Blacklist' ? 'red' : 'amber'}>{k.status}</Badge>}</div>
            <div className="mt-1 flex flex-wrap gap-3 text-sm text-ink/70">
              {Object.entries(k.handles || {}).filter(([, h]) => h).map(([p, h]) => <span key={p}>{p}: <b>@{h}</b> ({short(k.followers?.[p])})</span>)}
            </div>
            <div className="mt-1 text-xs text-ink/60">{k.city} · {(k.niche || []).join(', ')}{k.agency && ` · ${k.agency}`}{k.contactWa && ` · WA ${k.contactWa}`}</div>
            {k.tierOverride && <p className="mt-1 text-xs text-amber-700">Tier di-override: {k.tierOverrideReason}</p>}
            {k.status === 'Blacklist' && <p className="mt-1 text-sm font-semibold text-brand">Blacklist: {k.blacklistReason}</p>}
          </div>
          <div className="flex items-center gap-2"><div className="text-right"><div className="text-[11px] font-semibold uppercase text-ink/50">Rekomendasi</div><ReviewBadge r={k.recommendation} />{k.recommendationOverride && <div className="text-[10px] text-ink/50">auto: {k.recommendationAuto || '–'}</div>}</div>
            {can('Manager', 'KOL TL', 'KOL Officer') && <button className="btn-ghost" onClick={() => setEdit(true)}>Edit</button>}</div>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <Tile label="Booking" value={num(live.length)} />
        <Tile label="Total spend" value={rpShort(spend)} />
        <Tile label="Total views" value={short(views)} sub={`CPV ${rp(views ? spend / views : null)}`} />
        <Tile label="Rev. DIRECT" value={rpShort(live.reduce((a, h) => a + h.metrics.revenueDirect, 0))} />
      </div>
      {flags.length > 0 && <div className="flex flex-wrap gap-1.5">{flags.map((f) => <Badge key={f} tone="amber">⚠ {f}</Badge>)}</div>}
      <div className="grid gap-4 lg:grid-cols-3">
        <Section title="Rate card" className="lg:col-span-1">
          {[...RATE_ITEMS, ...Object.keys(k.rateCard || {}).filter((x) => !RATE_ITEMS.includes(x))].filter((x) => k.rateCard?.[x]).map((x) => [x, k.rateCard[x]]).map(([f, v]) => <div key={f} className="flex justify-between text-sm"><span>{f}</span><span className="num">{rp(v)}</span></div>)}
          <div className="mt-3 text-xs text-ink/60">Rekening: {k.bankAccount || '–'}{k.npwp && ` · NPWP ${k.npwp}`}</div>
          {k.notes && <p className="mt-2 text-sm">{k.notes}</p>}
        </Section>
        <Section title="Histori campaign" className="lg:col-span-2">
          {!k.history.length ? <p className="text-sm text-ink/50">Belum pernah dibooking.</p> : (
            <Table head={['Campaign', 'Status', { label: 'Biaya', right: 1 }, { label: 'Views', right: 1 }, { label: 'ER', right: 1 }, 'Outcome', { label: 'Cost/outcome (bench)', right: 1 }, { label: 'ROI DIRECT', right: 1 }]}>
              {k.history.map((h) => (
                <tr key={h.booking.id} className="cursor-pointer hover:bg-brand-soft" onClick={() => nav(`/booking/${h.booking.id}`)}>
                  <td className="td"><div className="font-semibold">{h.campaign.name}</div><div className="text-xs text-ink/50">{h.campaign.month} · {h.campaign.category}</div></td>
                  <td className="td"><StatusBadge s={h.booking.status} /></td>
                  <td className="td text-right num">{rpShort(h.metrics.cost)}</td><td className="td text-right num">{short(h.metrics.views)}</td>
                  <td className="td text-right num">{pct(h.metrics.er)}</td><td className="td text-xs"><b className="num">{num(h.metrics.outcome)}</b> {h.metrics.outcomeLabel}</td>
                  <td className="td text-right num">{rp(h.metrics.costPerOutcome)} <span className="text-ink/40">({rp(h.metrics.benchmark.cpo)})</span></td>
                  <td className="td text-right num">{meta.categories[h.campaign.category]?.evidence.includes('DIRECT') ? times(h.metrics.roiDirect) : '–'}</td>
                </tr>
              ))}
            </Table>
          )}
        </Section>
      </div>
      <KolForm open={edit} onClose={() => setEdit(false)} initial={k} onSaved={reload} />
    </div>
  )
}

export function KolForm({ open, onClose, initial, onSaved }) {
  const { can } = useApp()
  const toast = useToast()
  const [f, setF] = useState(null)
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  useEffect(() => {
    if (!open) return
    setErr('')
    setF(initial ? JSON.parse(JSON.stringify(initial)) : { name: '', handles: { tiktok: '', instagram: '', youtube: '' }, primaryPlatform: 'tiktok', followers: {}, city: '', niche: [], contactWa: '', agency: '', rateCard: {}, bankAccount: '', npwp: '', status: 'Aktif', blacklistReason: '', notes: '', tierOverride: null, tierOverrideReason: '', recommendationOverride: null, audienceCityTop3: [] })
  }, [open, initial])
  if (!f) return null
  const set = (k, v) => setF((x) => ({ ...x, [k]: v }))
  const save = async () => {
    setBusy(true); setErr('')
    const body = { ...f }
    ;['id', 'tier', 'stats', 'history', 'recommendation', 'recommendationAuto', 'createdAt', 'createdBy'].forEach((k) => delete body[k])
    body.handles = Object.fromEntries(Object.entries(body.handles || {}).map(([p, h]) => [p, (h || '').replace(/^@/, '').trim()]))
    try {
      const r = initial ? await api(`/api/kols/${initial.id}`, { method: 'PUT', body }) : await api('/api/kols', { method: 'POST', body })
      toast('KOL tersimpan'); onSaved?.(initial || r); onClose()
    } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }
  const lead = can('Manager', 'KOL TL')
  return (
    <Modal open={open} onClose={onClose} wide title={initial ? `Edit ${initial.name}` : 'KOL baru'} footer={<><button className="btn-ghost" onClick={onClose}>Batal</button><button className="btn-primary" disabled={busy} onClick={save}>Simpan</button></>}>
      <div className="grid gap-3 sm:grid-cols-3">
        <Field label="Nama" className="sm:col-span-2"><input className="input" value={f.name} onChange={(e) => set('name', e.target.value)} /></Field>
        <Field label="Platform utama (dasar tier)"><select className="input" value={f.primaryPlatform} onChange={(e) => set('primaryPlatform', e.target.value)}>{['tiktok', 'instagram', 'youtube'].map((p) => <option key={p}>{p}</option>)}</select></Field>
        {['tiktok', 'instagram', 'youtube'].map((p) => (
          <div key={p} className="grid grid-cols-2 gap-2">
            <Field label={`Handle ${p}`}><input className="input" value={f.handles?.[p] || ''} onChange={(e) => set('handles', { ...f.handles, [p]: e.target.value })} placeholder="@" /></Field>
            <Field label="Follower"><input className="input num" inputMode="numeric" value={f.followers?.[p] || ''} onChange={(e) => set('followers', { ...f.followers, [p]: Number(e.target.value.replace(/\D/g, '')) })} /></Field>
          </div>
        ))}
        <Field label="Kota domisili"><input className="input" value={f.city} onChange={(e) => set('city', e.target.value)} /></Field>
        <Field label="Kontak WA"><input className="input" inputMode="tel" value={f.contactWa || ''} onChange={(e) => set('contactWa', e.target.value)} /></Field>
        <Field label="Agency / manager"><input className="input" value={f.agency || ''} onChange={(e) => set('agency', e.target.value)} /></Field>
        <Field label="Niche" className="sm:col-span-3">
          <div className="flex flex-wrap gap-1.5">{NICHES.map((n) => { const on = f.niche?.includes(n); return <button type="button" key={n} onClick={() => set('niche', on ? f.niche.filter((x) => x !== n) : [...(f.niche || []), n])} className={`rounded-full border px-3 py-1.5 text-xs font-semibold ${on ? 'border-brand bg-brand text-white' : 'border-brand-line'}`}>{n}</button> })}</div>
        </Field>
        <div className="sm:col-span-3 grid grid-cols-2 gap-2 rounded-2xl bg-brand-soft p-3 sm:grid-cols-4">
          <div className="col-span-2 text-sm font-bold sm:col-span-4">Rate card</div>
          {RATE_ITEMS.map((r) => <Field key={r} label={r}><MoneyInput value={f.rateCard?.[r] || 0} onChange={(v) => set('rateCard', { ...f.rateCard, [r]: v })} /></Field>)}
        </div>
        <Field label="Rekening bank"><input className="input" value={f.bankAccount || ''} onChange={(e) => set('bankAccount', e.target.value)} /></Field>
        <Field label="NPWP"><input className="input" value={f.npwp || ''} onChange={(e) => set('npwp', e.target.value)} /></Field>
        <Field label="Status"><select className="input" value={f.status} onChange={(e) => set('status', e.target.value)}>{['Aktif', 'Watchlist', 'Blacklist'].map((s) => <option key={s}>{s}</option>)}</select></Field>
        {f.status === 'Blacklist' && <Field label="Alasan blacklist *" className="sm:col-span-3"><input className="input" value={f.blacklistReason || ''} onChange={(e) => set('blacklistReason', e.target.value)} /></Field>}
        {lead && <>
          <Field label="Override tier (KOL TL)"><select className="input" value={f.tierOverride || ''} onChange={(e) => set('tierOverride', e.target.value || null)}><option value="">Otomatis dari follower</option>{['Nano', 'Micro', 'Macro', 'Mega'].map((t) => <option key={t}>{t}</option>)}</select></Field>
          <Field label="Alasan override" className="sm:col-span-2"><input className="input" value={f.tierOverrideReason || ''} onChange={(e) => set('tierOverrideReason', e.target.value)} disabled={!f.tierOverride} /></Field>
          <Field label="Rekomendasi manual"><select className="input" value={f.recommendationOverride || ''} onChange={(e) => set('recommendationOverride', e.target.value || null)}><option value="">Otomatis dari histori</option>{['SCALE', 'KEEP', 'STOP'].map((t) => <option key={t}>{t}</option>)}</select></Field>
        </>}
        <Field label="Catatan" className="sm:col-span-3"><textarea className="input min-h-[64px] py-2" value={f.notes || ''} onChange={(e) => set('notes', e.target.value)} /></Field>
      </div>
      <div className="mt-3"><ErrorBox msg={err} /></div>
    </Modal>
  )
}
