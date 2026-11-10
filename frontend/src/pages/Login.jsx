import { useEffect, useState } from 'react'
import { api, auth } from '../api'
import { ErrorBox } from '../components/ui'

export default function Login({ onLogin }) {
  const [mode, setMode] = useState(window.location.pathname === '/daftar' ? 'daftar' : 'login')
  const [users, setUsers] = useState([])
  const [sel, setSel] = useState(null)
  const [pin, setPin] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  useEffect(() => { api('/api/auth/users').then(setUsers).catch((e) => setErr(e.message)) }, [])
  const submit = async (p = pin) => {
    if (!sel || p.length < 4) return
    setBusy(true); setErr('')
    try {
      const r = await api('/api/auth/login', { method: 'POST', body: { userId: sel.id, pin: p } })
      auth.set(r.token, r.user); onLogin(r.user)
    } catch (e) { setErr(e.message); setPin('') } finally { setBusy(false) }
  }
  const press = (d) => { if (d === '⌫') return setPin((p) => p.slice(0, -1)); const np = (pin + d).slice(0, 8); setPin(np) }
  return (
    <div className="flex min-h-screen items-center justify-center bg-brand-soft p-4">
      <div className="w-full max-w-md">
        <div className="rounded-3xl bg-brand p-5 text-white">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white text-xl font-black text-brand">AA</div>
            <div><div className="text-xs font-semibold uppercase tracking-widest text-white/80">Cimol Bojot AA · CRK</div><div className="text-2xl font-extrabold">KOL Ledger</div></div>
          </div>
          <p className="mt-3 text-sm text-white/85">Budget KOL, report per objective, dan dampaknya — dalam satu tempat.</p>
        </div>
        <div className="mt-3 rounded-3xl bg-white p-5 shadow-sm">
          {mode === 'daftar' ? <Register onBack={() => { setMode('login'); window.history.replaceState(null, '', '/login') }} /> : !sel ? (
            <>
              <h1 className="mb-3 text-base font-bold">Pilih nama</h1>
              <div className="grid grid-cols-2 gap-2">
                {users.map((u) => (
                  <button key={u.id} onClick={() => { setSel(u); setPin(''); setErr('') }} className="rounded-2xl border border-brand-line p-3 text-left hover:border-brand">
                    <div className="text-sm font-bold">{u.name}</div><div className="text-[11px] text-ink/60">{u.role}</div>
                  </button>
                ))}
              </div>
              <div className="mt-3"><ErrorBox msg={err} /></div>
              <div className="mt-4 border-t border-brand-line pt-4 text-center text-sm">
                Belum punya akun? <button className="font-bold text-brand underline" onClick={() => { setMode('daftar'); window.history.replaceState(null, '', '/daftar') }}>Daftar akun baru</button>
                <div className="mt-1 text-xs text-ink/50">Khusus tim KOL dengan email kantor · perlu approval admin</div>
              </div>
            </>
          ) : (
            <>
              <button onClick={() => setSel(null)} className="mb-2 text-sm font-semibold text-brand">‹ Ganti nama</button>
              <div className="text-center"><div className="text-lg font-bold">{sel.name}</div><div className="text-xs text-ink/60">{sel.role}</div></div>
              <div className="my-4 flex justify-center gap-2">
                {Array.from({ length: Math.max(4, pin.length) }).map((_, i) => <span key={i} className={`h-3.5 w-3.5 rounded-full ${i < pin.length ? 'bg-brand' : 'bg-brand-line'}`} />)}
              </div>
              <input type="password" inputMode="numeric" autoFocus className="sr-only" value={pin} onChange={(e) => setPin(e.target.value.replace(/\D/g, '').slice(0, 8))} onKeyDown={(e) => e.key === 'Enter' && submit()} aria-label="PIN" />
              <div className="grid grid-cols-3 gap-2">
                {['1', '2', '3', '4', '5', '6', '7', '8', '9', '⌫', '0', 'OK'].map((d) => (
                  <button key={d} disabled={busy} onClick={() => (d === 'OK' ? submit() : press(d))}
                    className={`h-14 rounded-2xl text-lg font-bold ${d === 'OK' ? 'bg-brand text-white' : 'bg-brand-soft hover:bg-brand-tint'}`}>{d}</button>
                ))}
              </div>
              <div className="mt-3"><ErrorBox msg={err} /></div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

function Register({ onBack }) {
  const [info, setInfo] = useState({ domain: 'citarasakuliner.com', roles: [{ value: 'KOL Officer', label: 'KOL Officer' }, { value: 'KOL TL', label: 'KOL Team Leader' }] })
  const [f, setF] = useState({ name: '', email: '', role: 'KOL Officer', pin: '', pin2: '' })
  const [err, setErr] = useState('')
  const [done, setDone] = useState(false)
  const [busy, setBusy] = useState(false)
  useEffect(() => { api('/api/auth/register-info').then(setInfo).catch(() => {}) }, [])
  const emailOk = f.email.trim().toLowerCase().endsWith('@' + info.domain)
  const submit = async () => {
    setErr('')
    if (f.name.trim().length < 2) return setErr('Nama wajib diisi')
    if (!emailOk) return setErr(`Gunakan email @${info.domain}`)
    if (!/^\d{4,8}$/.test(f.pin)) return setErr('PIN harus 4–8 digit angka')
    if (f.pin !== f.pin2) return setErr('Konfirmasi PIN tidak sama')
    setBusy(true)
    try { await api('/api/auth/register', { method: 'POST', body: { name: f.name, email: f.email, role: f.role, pin: f.pin } }); setDone(true) }
    catch (e) { setErr(e.message) } finally { setBusy(false) }
  }
  if (done) return (
    <div className="text-center">
      <div className="text-4xl">⏳</div>
      <h1 className="mt-2 text-lg font-bold">Pendaftaran terkirim</h1>
      <p className="mt-1 text-sm text-ink/70">Akun <b>{f.email.trim().toLowerCase()}</b> menunggu approval admin. Setelah disetujui, nama Anda muncul di daftar login — masuk dengan PIN yang tadi dibuat.</p>
      <button className="btn-ghost mt-4 w-full" onClick={onBack}>Kembali ke login</button>
    </div>
  )
  return (
    <div>
      <button onClick={onBack} className="mb-2 text-sm font-semibold text-brand">‹ Kembali ke login</button>
      <h1 className="text-base font-bold">Daftar akun tim KOL</h1>
      <p className="mb-3 text-xs text-ink/60">Hanya email @{info.domain}. Akun aktif setelah di-approve admin.</p>
      <div className="space-y-3">
        <label className="block"><span className="label">Nama lengkap</span><input className="input" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} autoComplete="name" /></label>
        <label className="block"><span className="label">Email kantor</span>
          <input className="input" type="email" inputMode="email" autoComplete="email" placeholder={`nama@${info.domain}`} value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} />
          {f.email && !emailOk && <span className="mt-1 block text-xs text-brand">Harus berakhiran @{info.domain}</span>}
        </label>
        <div><span className="label">Role</span>
          <div className="grid grid-cols-2 gap-2">{info.roles.map((r) => <button type="button" key={r.value} onClick={() => setF({ ...f, role: r.value })} className={`btn ${f.role === r.value ? 'bg-brand text-white' : 'border border-brand-line'}`}>{r.label}</button>)}</div>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <label className="block"><span className="label">PIN (4–8 angka)</span><input className="input" type="password" inputMode="numeric" autoComplete="new-password" value={f.pin} onChange={(e) => setF({ ...f, pin: e.target.value.replace(/\D/g, '').slice(0, 8) })} /></label>
          <label className="block"><span className="label">Ulangi PIN</span><input className="input" type="password" inputMode="numeric" autoComplete="new-password" value={f.pin2} onChange={(e) => setF({ ...f, pin2: e.target.value.replace(/\D/g, '').slice(0, 8) })} /></label>
        </div>
        <ErrorBox msg={err} />
        <button className="btn-primary w-full" disabled={busy} onClick={submit}>{busy ? 'Mengirim…' : 'Kirim pendaftaran'}</button>
      </div>
    </div>
  )
}
