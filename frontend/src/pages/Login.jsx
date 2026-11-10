import { useEffect, useState } from 'react'
import { api, auth } from '../api'
import { ErrorBox } from '../components/ui'

export default function Login({ onLogin }) {
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
          {!sel ? (
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
