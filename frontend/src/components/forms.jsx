import { useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import { useApp } from '../App'
import { ErrorBox, Field, Modal, MoneyInput, TierBadge, useToast } from './ui'
import { rp, thisMonth } from '../fmt'

export const RATE_ITEMS = ['Video TikTok', 'Reels', 'Story', 'Live', 'Visit', 'Mirroring', 'Visit Mirroring']
const defaultRate = (k, cat) => (['Regular Visit', 'Info Lokasi'].includes(cat) && (k.rateCard?.['Visit Mirroring'] || k.rateCard?.Visit)) || k.rateCard?.['Video TikTok'] || 0

const lastDay = (m) => { const [y, mo] = m.split('-').map(Number); return `${m}-${String(new Date(y, mo, 0).getDate()).padStart(2, '0')}` }

export function CampaignForm({ open, onClose, initial, onSaved }) {
  const { meta, user } = useApp()
  const toast = useToast()
  const [f, setF] = useState(null)
  const [outlets, setOutlets] = useState([])
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  useEffect(() => {
    if (!open) return
    const m = thisMonth()
    setF(initial ? JSON.parse(JSON.stringify(initial)) : { name: '', category: 'Regular Visit', objective: '', month: m, start: `${m}-01`, end: lastDay(m), budgetRp: 0, target: { outlets: [] }, kpiTargets: {}, gateStatus: 'PENDING', gateNote: '', linkedInitiativeCode: '', promoCodePrefix: '' })
    setErr('')
    api('/api/outlets').then(setOutlets).catch(() => {})
  }, [open, initial])
  if (!f) return null
  const set = (k, v) => setF((x) => ({ ...x, [k]: v }))
  const setT = (k, v) => setF((x) => ({ ...x, target: { ...x.target, [k]: v } }))
  const setK = (k, v) => setF((x) => ({ ...x, kpiTargets: { ...x.kpiTargets, [k]: v === '' ? null : Number(v) } }))
  const cfg = meta.categories[f.category]
  const save = async () => {
    setBusy(true); setErr('')
    try {
      const body = { ...f, objective: f.objective || cfg.objective }
      ;['id', 'code', 'createdAt', 'ownerId', 'ownerName', 'review', 'reviewNote', 'reviewedBy', 'reviewedAt', 'whatWorked', 'whatDidnt', 'nextAction', 'rows', 'agg', 'committed', 'config', 'bookingCount'].forEach((k) => delete body[k])
      const r = initial ? await api(`/api/campaigns/${initial.id}`, { method: 'PUT', body }) : await api('/api/campaigns', { method: 'POST', body })
      toast(initial ? 'Campaign diperbarui' : 'Campaign dibuat'); onSaved?.(r); onClose()
    } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }
  const outcomeKpi = { 'Regular Visit': 'Redemption kode', Frozen: 'Order', NPL: null, 'Info Lokasi': 'Klik Maps', 'Keranjang Kuning': 'Order', 'TikTok GO': 'Voucher ditukar' }[f.category]
  return (
    <Modal open={open} onClose={onClose} wide title={initial ? 'Edit campaign' : 'Campaign baru'} footer={<><button className="btn-ghost" onClick={onClose}>Batal</button><button className="btn-primary" disabled={busy} onClick={save}>Simpan</button></>}>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Nama campaign" className="sm:col-span-2"><input className="input" value={f.name} onChange={(e) => set('name', e.target.value)} placeholder="mis. Launch Mozza Duo" /></Field>
        <Field label="Kategori KOL" hint={cfg.objective}>
          <select className="input" value={f.category} onChange={(e) => set('category', e.target.value)} disabled={!!initial?.bookingCount}>
            {Object.keys(meta.categories).map((c) => <option key={c}>{c}</option>)}
          </select>
        </Field>
        <Field label="Bulan budget"><input type="month" className="input" value={f.month} onChange={(e) => { set('month', e.target.value); if (!initial) { set('start', `${e.target.value}-01`); set('end', lastDay(e.target.value)) } }} /></Field>
        <Field label="Mulai"><input type="date" className="input" value={f.start} onChange={(e) => set('start', e.target.value)} /></Field>
        <Field label="Selesai"><input type="date" className="input" value={f.end} onChange={(e) => set('end', e.target.value)} /></Field>
        <Field label="Budget campaign (Rp)" hint="Dicek terhadap sisa plan kategori bulan ini"><MoneyInput value={f.budgetRp} onChange={(v) => set('budgetRp', v)} /></Field>
        <Field label="Kode inisiatif (Skema Bulanan)"><input className="input" value={f.linkedInitiativeCode} onChange={(e) => set('linkedInitiativeCode', e.target.value)} placeholder="mis. N01" /></Field>
        <Field label="Objective (1 kalimat)" className="sm:col-span-2"><input className="input" value={f.objective} onChange={(e) => set('objective', e.target.value)} placeholder={cfg.objective} /></Field>
        {cfg.assisted && (
          <Field label="Outlet target (untuk uplift ASSISTED)" className="sm:col-span-2" hint="Penjualan outlet ini dibandingkan baseline 4 minggu sebelumnya">
            <div className="flex flex-wrap gap-1.5">
              {outlets.map((o) => {
                const on = (f.target.outlets || []).includes(o.code)
                return <button type="button" key={o.code} onClick={() => setT('outlets', on ? f.target.outlets.filter((x) => x !== o.code) : [...(f.target.outlets || []), o.code])}
                  className={`rounded-full border px-3 py-1.5 text-xs font-semibold ${on ? 'border-brand bg-brand text-white' : 'border-brand-line'}`}>{o.code} · {o.name}</button>
              })}
              {!outlets.length && <span className="text-xs text-ink/50">Belum ada outlet. Import di Pengaturan.</span>}
            </div>
          </Field>
        )}
        {f.category === 'NPL' && <Field label="Kode SKU baru (dari export Metabase)"><input className="input" value={f.target.sku || ''} onChange={(e) => setT('sku', e.target.value.toUpperCase())} placeholder="MOZZA" /></Field>}
        {['Frozen', 'Keranjang Kuning'].includes(f.category) && <Field label="Toko / channel"><input className="input" value={f.target.store || ''} onChange={(e) => setT('store', e.target.value)} /></Field>}
        <div className="sm:col-span-2 mt-1 rounded-2xl bg-brand-soft p-3">
          <div className="mb-2 text-sm font-bold">Target KPI</div>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            <Field label="Views"><input className="input" inputMode="numeric" value={f.kpiTargets.views ?? ''} onChange={(e) => setK('views', e.target.value)} /></Field>
            <Field label="CPV maks (Rp)"><input className="input" inputMode="numeric" value={f.kpiTargets.cpv ?? ''} onChange={(e) => setK('cpv', e.target.value)} /></Field>
            {outcomeKpi && <Field label={outcomeKpi}><input className="input" inputMode="numeric" value={f.kpiTargets.outcome ?? ''} onChange={(e) => setK('outcome', e.target.value)} /></Field>}
            {outcomeKpi && <Field label="Cost per outcome maks"><input className="input" inputMode="numeric" value={f.kpiTargets.costPerOutcome ?? ''} onChange={(e) => setK('costPerOutcome', e.target.value)} /></Field>}
            {['Frozen', 'Keranjang Kuning', 'TikTok GO'].includes(f.category) && <Field label="ROAS min"><input className="input" inputMode="decimal" value={f.kpiTargets.roas ?? ''} onChange={(e) => setK('roas', e.target.value)} /></Field>}
            {['Frozen', 'Keranjang Kuning', 'TikTok GO', 'Regular Visit'].includes(f.category) && <Field label="Revenue DIRECT"><input className="input" inputMode="numeric" value={f.kpiTargets.revenueDirect ?? ''} onChange={(e) => setK('revenueDirect', e.target.value)} /></Field>}
          </div>
        </div>
        <Field label="Status Activity Gate" hint={user.role !== 'Manager' ? 'Diputuskan Manager' : 'GO/GWC wajib untuk campaign ≥ batas approval'}>
          <select className="input" value={f.gateStatus} onChange={(e) => set('gateStatus', e.target.value)} disabled={user.role !== 'Manager'}>
            {['PENDING', 'GO', 'GWC', 'HOLD', 'SELESAI'].map((g) => <option key={g} value={g}>{g === 'GWC' ? 'GO WITH CONDITION' : g}</option>)}
          </select>
        </Field>
        <Field label="Catatan gate"><input className="input" value={f.gateNote} onChange={(e) => set('gateNote', e.target.value)} /></Field>
      </div>
      <div className="mt-3"><ErrorBox msg={err} /></div>
    </Modal>
  )
}

export function BookingForm({ open, onClose, initial, campaignId, onSaved }) {
  const { meta } = useApp()
  const toast = useToast()
  const [f, setF] = useState(null)
  const [kols, setKols] = useState([])
  const [camps, setCamps] = useState([])
  const [q, setQ] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  useEffect(() => {
    if (!open) return
    setErr(''); setQ('')
    setF(initial ? JSON.parse(JSON.stringify(initial)) : { campaignId: campaignId || '', kolId: '', platform: 'tiktok', deliverables: [{ format: 'Video TikTok', qty: 1, dueDate: '' }], costs: { feeRp: 0, productRp: 0, transportRp: 0, otherRp: 0 }, trackingLink: '', uniqueCode: '', contentRights: { repostDays: 30, adsUsage: false }, notes: '' })
    api('/api/kols').then(setKols).catch(() => {})
    api('/api/campaigns').then((c) => setCamps(c.filter((x) => !['HOLD', 'SELESAI'].includes(x.gateStatus) || x.id === initial?.campaignId))).catch(() => {})
  }, [open, initial, campaignId])
  const camp = camps.find((c) => c.id === f?.campaignId)
  const kol = kols.find((k) => k.id === f?.kolId)
  const filtered = useMemo(() => kols.filter((k) => k.status !== 'Blacklist' && (`${k.name} ${Object.values(k.handles || {}).join(' ')} ${k.city}`).toLowerCase().includes(q.toLowerCase())).slice(0, 30), [kols, q])
  if (!f) return null
  const set = (k, v) => setF((x) => ({ ...x, [k]: v }))
  const setC = (k, v) => setF((x) => ({ ...x, costs: { ...x.costs, [k]: v } }))
  const total = ['feeRp', 'productRp', 'transportRp', 'otherRp'].reduce((a, k) => a + (Number(f.costs[k]) || 0), 0)
  const remaining = camp ? camp.budgetRp - camp.committed + (initial?.dealAt ? total : 0) : null
  const save = async () => {
    setBusy(true); setErr('')
    try {
      const body = { campaignId: f.campaignId, kolId: f.kolId, platform: f.platform, deliverables: f.deliverables, costs: f.costs, trackingLink: f.trackingLink, uniqueCode: f.uniqueCode, contentRights: f.contentRights, notes: f.notes }
      const r = initial ? await api(`/api/bookings/${initial.id}`, { method: 'PUT', body }) : await api('/api/bookings', { method: 'POST', body })
      toast(initial ? 'Booking diperbarui' : 'Booking dibuat (Shortlist)'); onSaved?.(r); onClose()
    } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }
  return (
    <Modal open={open} onClose={onClose} wide title={initial ? 'Edit booking' : 'Booking KOL baru'} footer={<><button className="btn-ghost" onClick={onClose}>Batal</button><button className="btn-primary" disabled={busy || !f.campaignId || !f.kolId} onClick={save}>Simpan</button></>}>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Campaign" className="sm:col-span-2">
          <select className="input" value={f.campaignId} onChange={(e) => set('campaignId', e.target.value)} disabled={!!initial}>
            <option value="">Pilih campaign…</option>
            {camps.map((c) => <option key={c.id} value={c.id}>{c.month} · {c.category} · {c.name} (sisa {rp(c.budgetRp - c.committed)})</option>)}
          </select>
        </Field>
        <div className="sm:col-span-2">
          <span className="label">KOL</span>
          {kol ? (
            <div className="flex items-center justify-between rounded-xl border border-brand-line p-3">
              <div><div className="font-semibold">{kol.name} <TierBadge t={kol.tier} /></div><div className="text-xs text-ink/60">@{kol.handles?.tiktok || kol.handles?.instagram} · {kol.city}</div></div>
              {!initial && <button className="btn-ghost btn-sm" onClick={() => set('kolId', '')}>Ganti</button>}
            </div>
          ) : (
            <>
              <input className="input" placeholder="Cari nama / handle / kota…" value={q} onChange={(e) => setQ(e.target.value)} />
              <div className="mt-1 max-h-48 overflow-y-auto rounded-xl border border-brand-line">
                {filtered.map((k) => (
                  <button key={k.id} type="button" onClick={() => setF((x) => ({ ...x, kolId: k.id, costs: { ...x.costs, feeRp: x.costs.feeRp || defaultRate(k, camp?.category) } }))} className="flex w-full items-center justify-between border-b border-brand-line px-3 py-2 text-left text-sm last:border-0 hover:bg-brand-soft">
                    <span><b>{k.name}</b> <span className="text-ink/50">@{k.handles?.tiktok}</span></span>
                    <span className="flex items-center gap-2"><span className="text-xs text-ink/50">{k.city}</span><TierBadge t={k.tier} />{k.recommendation && <span className="text-[10px] font-bold text-ink/60">{k.recommendation}</span>}</span>
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
        <Field label="Platform"><select className="input" value={f.platform} onChange={(e) => set('platform', e.target.value)}>{['tiktok', 'instagram', 'youtube'].map((p) => <option key={p}>{p}</option>)}</select></Field>
        <Field label="Kode unik / voucher KOL" hint="Kosongkan untuk dibuat otomatis (mis. RV-RARAJAJAN)"><input className="input uppercase" value={f.uniqueCode} onChange={(e) => set('uniqueCode', e.target.value.toUpperCase())} /></Field>
        <div className="sm:col-span-2 rounded-2xl bg-brand-soft p-3">
          <div className="mb-2 flex items-center justify-between text-sm font-bold"><span>Biaya</span><span className="num">Total {rp(total)}</span></div>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <Field label="Fee KOL"><MoneyInput value={f.costs.feeRp} onChange={(v) => setC('feeRp', v)} /></Field>
            <Field label="Produk"><MoneyInput value={f.costs.productRp} onChange={(v) => setC('productRp', v)} /></Field>
            <Field label="Transport"><MoneyInput value={f.costs.transportRp} onChange={(v) => setC('transportRp', v)} /></Field>
            <Field label="Lainnya"><MoneyInput value={f.costs.otherRp} onChange={(v) => setC('otherRp', v)} /></Field>
            {camp?.category === 'Keranjang Kuning' && <Field label="Komisi affiliate (%)" hint="Nominal komisi diambil dari report"><input className="input" inputMode="decimal" value={f.costs.commissionPct ?? ''} onChange={(e) => setC('commissionPct', Number(e.target.value))} /></Field>}
          </div>
          {kol && RATE_ITEMS.some((r) => kol.rateCard?.[r]) && (
            <div className="mt-2">
              <div className="text-[11px] font-semibold text-ink/60">Rate card KOL — ketuk untuk isi fee:</div>
              <div className="mt-1 flex flex-wrap gap-1.5">
                {RATE_ITEMS.filter((r) => kol.rateCard?.[r]).map((r) => (
                  <button type="button" key={r} onClick={() => setC('feeRp', kol.rateCard[r])}
                    className={`rounded-full border px-2.5 py-1 text-xs ${f.costs.feeRp === kol.rateCard[r] ? 'border-brand bg-brand text-white' : 'border-brand-line bg-white'}`}>{r} · {rp(kol.rateCard[r])}</button>
                ))}
              </div>
            </div>
          )}
          {remaining !== null && <p className={`mt-2 text-xs ${total > remaining ? 'font-semibold text-brand' : 'text-ink/60'}`}>Sisa budget campaign: {rp(remaining)}{total > remaining ? ' — biaya melebihi sisa budget' : ''}</p>}
          {kol && ['Macro', 'Mega'].includes(kol.tier) && <p className="mt-1 text-xs font-semibold text-amber-700">Tier {kol.tier}: wajib approval Manager sebelum DEAL.</p>}
        </div>
        <div className="sm:col-span-2">
          <span className="label">Deliverables</span>
          {f.deliverables.map((d, i) => (
            <div key={i} className="mb-2 grid grid-cols-[1fr_70px_1fr_44px] gap-2">
              <select className="input" value={d.format} onChange={(e) => set('deliverables', f.deliverables.map((x, j) => j === i ? { ...x, format: e.target.value } : x))}>
                {['Video TikTok', 'Reels', 'Story', 'Feed', 'Live', 'Visit', 'Mirroring', 'Visit Mirroring', 'YouTube Shorts', 'Bundle'].map((o) => <option key={o}>{o}</option>)}
              </select>
              <input className="input" inputMode="numeric" value={d.qty} onChange={(e) => set('deliverables', f.deliverables.map((x, j) => j === i ? { ...x, qty: Number(e.target.value) || 1 } : x))} />
              <input type="date" className="input" value={d.dueDate} onChange={(e) => set('deliverables', f.deliverables.map((x, j) => j === i ? { ...x, dueDate: e.target.value } : x))} />
              <button type="button" className="btn-ghost px-0" onClick={() => set('deliverables', f.deliverables.filter((_, j) => j !== i))} aria-label="Hapus">×</button>
            </div>
          ))}
          <button type="button" className="btn-ghost btn-sm" onClick={() => set('deliverables', [...f.deliverables, { format: 'Story', qty: 1, dueDate: '' }])}>+ Deliverable</button>
        </div>
        <Field label="Link tracking (UTM / affiliate)"><input className="input" value={f.trackingLink} onChange={(e) => set('trackingLink', e.target.value)} /></Field>
        <div className="grid grid-cols-2 gap-2">
          <Field label="Hak repost (hari)"><input className="input" inputMode="numeric" value={f.contentRights.repostDays ?? ''} onChange={(e) => set('contentRights', { ...f.contentRights, repostDays: Number(e.target.value) })} /></Field>
          <Field label="Boleh untuk ads"><select className="input" value={f.contentRights.adsUsage ? '1' : '0'} onChange={(e) => set('contentRights', { ...f.contentRights, adsUsage: e.target.value === '1' })}><option value="0">Tidak</option><option value="1">Ya</option></select></Field>
        </div>
        <Field label="Catatan" className="sm:col-span-2"><textarea className="input min-h-[64px] py-2" value={f.notes} onChange={(e) => set('notes', e.target.value)} /></Field>
      </div>
      <div className="mt-3"><ErrorBox msg={err} /></div>
    </Modal>
  )
}
