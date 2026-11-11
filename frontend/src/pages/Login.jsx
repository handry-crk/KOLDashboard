import { useEffect, useRef, useState } from 'react'
import { api, auth } from '../api'
import { ErrorBox, FloatingReactions } from '../components/ui'

export default function Login({ onLogin }) {
  const [mode, setMode] = useState(window.location.pathname === '/daftar' ? 'daftar' : 'login')
  const [users, setUsers] = useState([])
  const [sel, setSel] = useState(null)
  const [pin, setPin] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  useEffect(() => { api('/api/auth/users').then(setUsers).catch((e) => setErr(e.message)) }, [])
  const pinRef = useRef('')
  const busyRef = useRef(false)
  pinRef.current = pin
  const submit = async (p = pinRef.current) => {
    if (!sel || p.length < 4 || busyRef.current) return
    busyRef.current = true
    setBusy(true); setErr('')
    try {
      const r = await api('/api/auth/login', { method: 'POST', body: { userId: sel.id, pin: p } })
      auth.set(r.token, r.user); onLogin(r.user)
    } catch (e) { setErr(e.message); setPin('') } finally { setBusy(false); busyRef.current = false }
  }
  // PIN bisa diketik dari keyboard fisik (angka, numpad, Backspace, Enter, Esc) tanpa harus klik tombol
  useEffect(() => {
    if (!sel || mode !== 'login') return
    const h = (e) => {
      if (e.ctrlKey || e.metaKey || e.altKey) return
      const digit = /^[0-9]$/.test(e.key) ? e.key : (/^Numpad[0-9]$/.test(e.code) ? e.code.slice(-1) : null)
      if (digit) { e.preventDefault(); setErr(''); setPin((p) => (p + digit).slice(0, 8)) }
      else if (e.key === 'Backspace' || e.key === 'Delete') { e.preventDefault(); setPin((p) => p.slice(0, -1)) }
      else if (e.key === 'Enter') { e.preventDefault(); submit(pinRef.current) }
      else if (e.key === 'Escape') { e.preventDefault(); setSel(null); setPin('') }
    }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sel, mode])
  const press = (d) => { setErr(''); if (d === '⌫') return setPin((p) => p.slice(0, -1)); setPin((p) => (p + d).slice(0, 8)) }
  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-brand-soft p-4">
      <FloatingReactions count={16} />
      <div className="relative w-full max-w-md" style={{ animation: 'fadeUp .5s cubic-bezier(.2,.7,.2,1) both' }}>
        <div className="hdr-gradient relative overflow-hidden rounded-3xl bg-brand p-5 text-white">
          <FloatingReactions count={6} />
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
                {Array.from({ length: Math.max(4, pin.length) }).map((_, i) => <span key={i} className={`h-3.5 w-3.5 rounded-full transition ${i < pin.length ? 'pop bg-brand' : 'bg-brand-line'}`} />)}
              </div>
              <p className="-mt-2 mb-3 hidden text-center text-xs text-ink/50 sm:block">Ketik PIN dengan keyboard lalu tekan Enter, atau klik tombol angka</p>
              <div className="grid grid-cols-3 gap-2">
                {['1', '2', '3', '4', '5', '6', '7', '8', '9', '⌫', '0', 'OK'].map((d) => (
                  <button key={d} type="button" tabIndex={-1} disabled={busy} onMouseDown={(e) => e.preventDefault()} onClick={() => (d === 'OK' ? submit() : press(d))}
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
