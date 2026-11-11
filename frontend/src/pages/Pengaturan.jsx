import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { useApp } from '../App'
import { ErrorBox, Field, Loading, Modal, MoneyInput, Section, Table, useApi, useToast, Badge, ReasonModal } from '../components/ui'
import { dateTime } from '../fmt'
import { celebrate } from '../components/fx'

const ROLE_LABEL = { 'KOL TL': 'KOL Team Leader', 'KOL Officer': 'KOL Officer' }

export default function Pengaturan() {
  const { can } = useApp()
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-extrabold">Pengaturan</h1>
      {can('Manager') && <Pending />}
      {can('Manager') && <SettingsForm />}
      <DataImport />
      {can('Manager') && <Benchmarks />}
      {can('Manager') && <Users />}
      {can('Manager') && <Maintenance />}
    </div>
  )
}

function SettingsForm() {
  const { settings, setSettings } = useApp()
  const toast = useToast()
  const [f, setF] = useState(settings)
  const [err, setErr] = useState('')
  const set = (k, v) => setF((x) => ({ ...x, [k]: v }))
  const save = async () => { try { const s = await api('/api/settings', { method: 'PUT', body: f }); setSettings(s); toast('Pengaturan disimpan') } catch (e) { setErr(e.message) } }
  return (
    <Section title="Aturan & batas" right={<button className="btn-primary btn-sm" onClick={save}>Simpan</button>}>
      <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-4">
        <Field label="Pagu KOL bulanan"><MoneyInput value={f.monthlyKolPagu} onChange={(v) => set('monthlyKolPagu', v)} /></Field>
        <Field label="Batas approval Manager" hint="Booking ≥ nilai ini wajib approval; campaign ≥ nilai ini wajib Gate GO/GWC"><MoneyInput value={f.approvalThresholdRp} onChange={(v) => set('approvalThresholdRp', v)} /></Field>
        <Field label="GM blended (%)" hint="Dari Price Structure"><input className="input" inputMode="decimal" value={Math.round(f.gmBlended * 1000) / 10} onChange={(e) => set('gmBlended', Number(e.target.value) / 100)} /></Field>
        <Field label="AOV outlet (Rp)" hint="Revenue DIRECT Regular Visit = redemption × AOV"><MoneyInput value={f.aovRp} onChange={(v) => set('aovRp', v)} /></Field>
        {['Micro', 'Macro', 'Mega'].map((t) => <Field key={t} label={`Follower min. ${t}`}><input className="input num" inputMode="numeric" value={f.tierThresholds[t]} onChange={(e) => set('tierThresholds', { ...f.tierThresholds, [t]: Number(e.target.value.replace(/\D/g, '')) })} /></Field>)}
        <Field label="Report submit (hari)"><input className="input" inputMode="numeric" value={f.reportSubmitDays} onChange={(e) => set('reportSubmitDays', Number(e.target.value))} /></Field>
        <Field label="Report final / lock (hari)"><input className="input" inputMode="numeric" value={f.reportFinalDays} onChange={(e) => set('reportFinalDays', Number(e.target.value))} /></Field>
        <Field label="Flag ER rendah (%)"><input className="input" inputMode="decimal" value={f.erFlagLow * 100} onChange={(e) => set('erFlagLow', Number(e.target.value) / 100)} /></Field>
        <Field label="Flag ER tinggi (%)"><input className="input" inputMode="decimal" value={f.erFlagHigh * 100} onChange={(e) => set('erFlagHigh', Number(e.target.value) / 100)} /></Field>
        <Field label="Flag views < % follower"><input className="input" inputMode="decimal" value={f.viewsFlagRatio * 100} onChange={(e) => set('viewsFlagRatio', Number(e.target.value) / 100)} /></Field>
        <Field label="Penerima digest (email, koma)" className="sm:col-span-2"><input className="input" value={f.digestRecipients || ''} onChange={(e) => set('digestRecipients', e.target.value)} /></Field>
      </div>
      <div className="mt-2"><ErrorBox msg={err} /></div>
    </Section>
  )
}

function Benchmarks() {
  const { settings, setSettings, meta } = useApp()
  const toast = useToast()
  const [b, setB] = useState(settings.benchmarks)
  const save = async () => { const s = await api('/api/settings', { method: 'PUT', body: { benchmarks: b } }); setSettings(s); toast('Benchmark disimpan') }
  const up = (cat, tier, k, v) => setB((x) => ({ ...x, [cat]: { ...x[cat], [tier]: { ...x[cat][tier], [k]: v === '' ? null : Number(v) } } }))
  return (
    <Section title="Benchmark per kategori & tier (*angka ilustrasi — kalibrasi setelah 8 minggu)" right={<button className="btn-primary btn-sm" onClick={save}>Simpan</button>}>
      <Table head={['Kategori', 'Tier', 'CPV (Rp)', 'ER (desimal)', 'Cost per outcome (Rp)', 'ROAS']}>
        {Object.keys(meta.categories).flatMap((cat) => meta.tiers.map((t, i) => (
          <tr key={cat + t}>
            <td className="td font-semibold text-xs">{i === 0 ? cat : ''}</td><td className="td text-xs">{t}</td>
            {['cpv', 'er', 'cpo', 'roas'].map((k) => <td key={k} className="td py-1"><input className="input min-h-[34px] w-24 text-sm" value={b[cat]?.[t]?.[k] ?? ''} disabled={k === 'roas' && !['Frozen', 'Keranjang Kuning', 'TikTok GO'].includes(cat)} onChange={(e) => up(cat, t, k, e.target.value)} /></td>)}
          </tr>
        )))}
      </Table>
    </Section>
  )
}

function DataImport() {
  const toast = useToast()
  const { data: outlets, reload } = useApi('/api/outlets')
  const oRef = useRef(); const sRef = useRef()
  const [res, setRes] = useState(null)
  const send = async (path, file) => {
    const fd = new FormData(); fd.append('file', file)
    try { const r = await api(path, { method: 'POST', body: fd }); setRes(r); toast(`${r.imported} baris diimport`); reload() } catch (e) { toast(e.message, 'err') }
  }
  return (
    <Section title="Data outlet & penjualan (untuk uplift ASSISTED)">
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <p className="mb-2 text-sm">Import outlet: CSV kolom <code className="rounded bg-brand-soft px-1">code, name, area</code></p>
          <button className="btn-ghost" onClick={() => oRef.current.click()}>Upload CSV outlet</button>
          <input ref={oRef} type="file" accept=".csv,text/csv" hidden onChange={(e) => { e.target.files[0] && send('/api/outlets/import', e.target.files[0]); e.target.value = '' }} />
          <div className="mt-2 max-h-40 overflow-y-auto text-xs text-ink/70">{(outlets || []).map((o) => <div key={o.code}>{o.code} · {o.name} · {o.area}</div>)}</div>
        </div>
        <div>
          <p className="mb-2 text-sm">Import penjualan harian per outlet (export Metabase): <code className="rounded bg-brand-soft px-1">date, outletCode, revenueRp, transactions</code> + opsional kolom <code className="rounded bg-brand-soft px-1">sku:MOZZA</code> (unit). Pemisah koma atau titik koma.</p>
          <button className="btn-ghost" onClick={() => sRef.current.click()}>Upload CSV penjualan</button>
          <input ref={sRef} type="file" accept=".csv,text/csv" hidden onChange={(e) => { e.target.files[0] && send('/api/outlet-sales/import', e.target.files[0]); e.target.value = '' }} />
          {res?.errors?.length > 0 && <div className="mt-2 text-xs text-brand">{res.errors.join(' · ')}</div>}
        </div>
      </div>
    </Section>
  )
}

function Users() {
  const { meta } = useApp()
  const toast = useToast()
  const { data, reload } = useApi('/api/users')
  const [f, setF] = useState(null)
  const [err, setErr] = useState('')
  const save = async () => {
    try { f.id ? await api(`/api/users/${f.id}`, { method: 'PUT', body: f }) : await api('/api/users', { method: 'POST', body: f }); toast('User disimpan'); setF(null); reload() } catch (e) { setErr(e.message) }
  }
  return (
    <Section title="User & role" right={<button className="btn-primary btn-sm" onClick={() => { setF({ name: '', role: 'KOL Officer', pin: '', email: '', active: true }); setErr('') }}>+ User</button>}>
      {!data ? <Loading /> : (
        <Table head={['Nama', 'Role', 'Email', 'Status', 'Login terakhir', '']}>
          {data.map((u) => <tr key={u.id}><td className="td font-semibold">{u.name}{u.source === 'self' && <span className="ml-1 text-[10px] text-ink/50">daftar mandiri</span>}</td><td className="td text-sm">{ROLE_LABEL[u.role] || u.role}</td><td className="td text-xs">{u.email}</td><td className="td">{u.active ? <Badge tone="green">Aktif</Badge> : <Badge>Nonaktif</Badge>}</td><td className="td text-xs">{dateTime(u.lastLogin)}</td>
            <td className="td"><button className="btn-ghost btn-sm" onClick={() => { setF({ ...u, pin: '' }); setErr('') }}>Edit / reset PIN</button></td></tr>)}
        </Table>
      )}
      <Modal open={!!f} onClose={() => setF(null)} title={f?.id ? 'Edit user' : 'User baru'} footer={<><button className="btn-ghost" onClick={() => setF(null)}>Batal</button><button className="btn-primary" onClick={save}>Simpan</button></>}>
        {f && <div className="space-y-3">
          <Field label="Nama"><input className="input" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></Field>
          <Field label="Role"><select className="input" value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })}>{meta.roles.map((r) => <option key={r}>{r}</option>)}</select></Field>
          <Field label="Email (untuk reminder)"><input className="input" value={f.email || ''} onChange={(e) => setF({ ...f, email: e.target.value })} /></Field>
          <Field label={f.id ? 'PIN baru (kosongkan bila tidak diganti)' : 'PIN (min. 4 digit)'}><input className="input" inputMode="numeric" value={f.pin} onChange={(e) => setF({ ...f, pin: e.target.value.replace(/\D/g, '') })} /></Field>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" className="h-5 w-5" checked={f.active} onChange={(e) => setF({ ...f, active: e.target.checked })} /> Aktif</label>
          <ErrorBox msg={err} />
        </div>}
      </Modal>
    </Section>
  )
}

function Maintenance() {
  const toast = useToast()
  const run = async (fn, msg) => { try { await fn(); toast(msg) } catch (e) { toast(e.message, 'err') } }
  return (
    <Section title="Pemeliharaan">
      <div className="flex flex-wrap gap-2">
        <button className="btn-ghost" onClick={() => run(async () => { await api('/api/admin/seed', { method: 'POST' }); setTimeout(() => window.location.reload(), 600) }, 'Data contoh dibuat (PIN user contoh: 1234)')}>Isi data contoh (DB kosong)</button>
        <button className="btn-ghost" onClick={() => run(async () => { const r = await api('/api/admin/backup', { method: 'POST', raw: true }); const b = await r.blob(); const a = document.createElement('a'); a.href = URL.createObjectURL(b); a.download = 'kol-ledger-backup.json'; a.click() }, 'Backup diunduh')}>Backup sekarang</button>
        <button className="btn-ghost" onClick={() => run(() => api('/api/admin/jobs/refresh', { method: 'POST' }), 'Status booking diperbarui')}>Jalankan cek status</button>
        <button className="btn-ghost" onClick={() => run(() => api('/api/admin/jobs/weekly', { method: 'POST' }), 'Digest mingguan dibuat')}>Kirim digest mingguan</button>
      </div>
      <p className="mt-2 text-xs text-ink/50">Job otomatis (WIB): cek status & kunci metrik 00.10 · reminder officer 09.00 · digest Senin 08.00 · draft Review M+1 tgl 3 · backup Minggu 02.00.</p>
    </Section>
  )
}

function Pending() {
  const toast = useToast()
  const { data, reload } = useApi('/api/users/pending')
  const [roles, setRoles] = useState({})
  const [rej, setRej] = useState(null)
  useEffect(() => { if (window.location.hash === '#pendaftar') document.getElementById('pendaftar')?.scrollIntoView() }, [data])
  const approve = async (u) => {
    try { await api(`/api/users/${u.id}/approve`, { method: 'POST', body: { role: roles[u.id] || u.role } }); toast(`${u.name} disetujui`); celebrate(); reload() } catch (e) { toast(e.message, 'err') }
  }
  return (
    <Section title={<span id="pendaftar">Pendaftar menunggu approval {data?.length ? <Badge tone="amber">{data.length}</Badge> : null}</span>}>
      {!data ? <Loading /> : !data.length ? <p className="text-sm text-ink/50">Tidak ada pendaftaran baru. Link pendaftaran untuk tim: <b>{window.location.origin}/daftar</b></p> : (
        <Table head={['Nama', 'Email', 'Role diminta', 'Daftar', 'Role disetujui', '']}>
          {data.map((u) => (
            <tr key={u.id}>
              <td className="td font-semibold">{u.name}</td><td className="td text-sm">{u.email}</td>
              <td className="td text-sm">{ROLE_LABEL[u.requestedRole] || u.requestedRole}</td><td className="td text-xs">{dateTime(u.registeredAt)}</td>
              <td className="td"><select className="input min-h-[36px] w-auto text-sm" value={roles[u.id] || u.role} onChange={(e) => setRoles({ ...roles, [u.id]: e.target.value })}>
                <option value="KOL Officer">KOL Officer</option><option value="KOL TL">KOL Team Leader</option></select></td>
              <td className="td whitespace-nowrap"><button className="btn-ok btn-sm" onClick={() => approve(u)}>Approve</button> <button className="btn-ghost btn-sm" onClick={() => setRej(u)}>Tolak</button></td>
            </tr>
          ))}
        </Table>
      )}
      <ReasonModal open={!!rej} danger title={`Tolak pendaftaran ${rej?.name || ''}`} label="Alasan penolakan" confirmText="Tolak"
        onClose={() => setRej(null)} onSubmit={async (r) => { await api(`/api/users/${rej.id}/reject`, { method: 'POST', body: { reason: r } }); toast('Pendaftaran ditolak'); setRej(null); reload() }} />
    </Section>
  )
}
