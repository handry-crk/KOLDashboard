import { createContext, useContext, useEffect, useState } from 'react'
import { Navigate, NavLink, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { api, auth } from './api'
import { ToastProvider, Loading, FloatingReactions } from './components/ui'
import Login from './pages/Login'
import Ringkasan from './pages/Ringkasan'
import Campaigns, { CampaignDetail } from './pages/Campaigns'
import Pipeline from './pages/Pipeline'
import BookingPage from './pages/Booking'
import InputKonten from './pages/InputKonten'
import Kols, { KolDetail } from './pages/Kols'
import Budget from './pages/Budget'
import Pembayaran from './pages/Pembayaran'
import Laporan from './pages/Laporan'
import Pengaturan from './pages/Pengaturan'
import Tugas from './pages/Tugas'

const Ctx = createContext({})
export const useApp = () => useContext(Ctx)

const NAV = [
  { to: '/', label: 'Ringkasan', icon: '📊', roles: ['Manager', 'KOL TL', 'Direksi', 'Finance'] },
  { to: '/tugas', label: 'Tugas', icon: '✅', roles: ['KOL Officer', 'KOL TL', 'Manager', 'Finance'] },
  { to: '/campaign', label: 'Campaign', icon: '🎯', roles: ['Manager', 'KOL TL', 'KOL Officer', 'Direksi'] },
  { to: '/pipeline', label: 'Pipeline', icon: '🗂️', roles: ['Manager', 'KOL TL', 'KOL Officer'] },
  { to: '/input', label: 'Input', icon: '➕', roles: ['Manager', 'KOL TL', 'KOL Officer'] },
  { to: '/kol', label: 'KOL', icon: '👤', roles: ['Manager', 'KOL TL', 'KOL Officer', 'Direksi'] },
  { to: '/budget', label: 'Budget', icon: '💰', roles: ['Manager', 'KOL TL', 'Finance', 'Direksi'] },
  { to: '/pembayaran', label: 'Pembayaran', icon: '🧾', roles: ['Manager', 'KOL TL', 'Finance'] },
  { to: '/laporan', label: 'Laporan', icon: '📄', roles: ['Manager', 'KOL TL', 'KOL Officer', 'Direksi'] },
  { to: '/pengaturan', label: 'Pengaturan', icon: '⚙️', roles: ['Manager', 'KOL TL'] },
]
const MOBILE = { 'KOL Officer': ['/tugas', '/input', '/pipeline', '/kol'], 'KOL TL': ['/', '/tugas', '/input', '/pipeline'],
  Manager: ['/', '/tugas', '/campaign', '/pipeline'], Finance: ['/pembayaran', '/', '/budget', '/tugas'], Direksi: ['/', '/campaign', '/kol', '/laporan'] }
export const HOME = { 'KOL Officer': '/tugas', Finance: '/pembayaran' }

function Shell({ children }) {
  const { user, logout } = useApp()
  const [menu, setMenu] = useState(false)
  const loc = useLocation()
  useEffect(() => { setMenu(false); window.scrollTo(0, 0) }, [loc.pathname])
  const nav = NAV.filter((n) => n.roles.includes(user.role))
  const mob = MOBILE[user.role].map((p) => NAV.find((n) => n.to === p))
  const rest = nav.filter((n) => !MOBILE[user.role].includes(n.to))
  const restActive = rest.some((n) => (n.to === '/' ? loc.pathname === '/' : loc.pathname.startsWith(n.to)))
  return (
    <div className="min-h-screen pb-24 sm:pb-8">
      <header className="no-print px-3 pt-3 sm:px-6">
        <div className="hdr-gradient relative mx-auto max-w-7xl overflow-hidden rounded-2xl bg-brand px-4 py-3 text-white shadow-sm">
          <FloatingReactions count={9} />
          <div className="relative flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white text-lg font-black text-brand">AA</div>
              <div>
                <div className="text-[11px] font-semibold uppercase tracking-widest text-white/80">Cimol Bojot AA · CRK</div>
                <div className="flex items-center gap-2 text-lg font-extrabold leading-tight">KOL Ledger <span className="inline-flex items-center gap-1 rounded-full bg-white/20 px-2 py-0.5 text-[10px] font-bold tracking-widest"><span className="live-dot" />LIVE</span></div>
              </div>
            </div>
            <div className="flex items-center gap-2 text-right">
              <div className="hidden sm:block"><div className="text-sm font-bold">{user.name}</div><div className="text-[11px] text-white/80">{user.role}</div></div>
              <button onClick={logout} className="rounded-xl bg-white/15 px-3 py-2 text-xs font-semibold hover:bg-white/25">Keluar</button>
            </div>
          </div>
          <nav className="relative mt-3 hidden flex-wrap gap-1 sm:flex">
            {nav.map((n) => (
              <NavLink key={n.to} to={n.to} end={n.to === '/'} className={({ isActive }) => `rounded-lg px-3 py-1.5 text-sm font-semibold transition ${isActive ? 'bg-white text-brand shadow-sm' : 'text-white/90 hover:-translate-y-0.5 hover:bg-white/15'}`}>{n.label}</NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-3 py-4 sm:px-6">{children}</main>
      <nav className="no-print fixed inset-x-0 bottom-0 z-40 grid border-t border-brand-line bg-white pb-[env(safe-area-inset-bottom)] sm:hidden" style={{ gridTemplateColumns: `repeat(${mob.length + 1}, 1fr)` }}>
        {mob.map((n) => (
          <NavLink key={n.to} to={n.to} end={n.to === '/'} className={({ isActive }) => `flex min-h-[60px] flex-col items-center justify-center text-[11px] font-semibold ${isActive ? 'nav-active text-brand' : 'text-ink/60'}`}>
            <span className="nav-ico text-lg leading-none">{n.icon}</span>{n.label}
          </NavLink>
        ))}
        <button onClick={() => setMenu(true)} className={`flex min-h-[60px] flex-col items-center justify-center text-[11px] font-semibold ${restActive ? 'text-brand' : 'text-ink/60'}`} aria-label="Menu lainnya">
          <span className="text-lg leading-none">☰</span>Lainnya
        </button>
      </nav>
      {menu && (
        <div className="no-print fixed inset-0 z-50 flex items-end bg-black/40 sm:hidden" onClick={() => setMenu(false)}>
          <div className="w-full rounded-t-3xl bg-white p-4 pb-[calc(1rem+env(safe-area-inset-bottom))]" onClick={(e) => e.stopPropagation()}>
            <div className="mb-3 flex items-center justify-between">
              <div><div className="font-bold">{user.name}</div><div className="text-xs text-ink/60">{user.role === 'KOL TL' ? 'KOL Team Leader' : user.role}</div></div>
              <button onClick={() => setMenu(false)} className="h-10 w-10 rounded-full text-2xl leading-none hover:bg-brand-soft" aria-label="Tutup">×</button>
            </div>
            <div className="grid grid-cols-3 gap-2">
              {rest.map((n) => (
                <NavLink key={n.to} to={n.to} end={n.to === '/'} className={({ isActive }) => `flex min-h-[72px] flex-col items-center justify-center gap-1 rounded-2xl border text-xs font-semibold ${isActive ? 'border-brand bg-brand-soft text-brand' : 'border-brand-line'}`}>
                  <span className="text-xl leading-none">{n.icon}</span>{n.label}
                </NavLink>
              ))}
            </div>
            <button onClick={logout} className="btn-ghost mt-3 w-full text-brand">Keluar</button>
          </div>
        </div>
      )}
    </div>
  )
}

function Guard({ roles, children }) {
  const { user } = useApp()
  if (roles && !roles.includes(user.role)) return <Navigate to={HOME[user.role] || '/'} replace />
  return children
}

export default function App() {
  const [user, setUser] = useState(auth.user())
  const [meta, setMeta] = useState(null)
  const [settings, setSettings] = useState(null)
  const nav = useNavigate()
  const loc = useLocation()
  useEffect(() => {
    if (!user) return
    Promise.all([api('/api/meta'), api('/api/settings')]).then(([m, s]) => { setMeta(m); setSettings(s) }).catch(() => {})
  }, [user])
  const logout = () => { auth.clear(); setUser(null); nav('/login') }
  if (!user) return <ToastProvider><Routes><Route path="*" element={<Login onLogin={(u) => { setUser(u); nav(HOME[u.role] || '/') }} />} /></Routes></ToastProvider>
  if (loc.pathname === '/login') return <Navigate to={HOME[user.role] || '/'} replace />
  if (!meta || !settings) return <Loading />
  const can = (...roles) => roles.includes(user.role)
  const R = (roles, el) => <Guard roles={roles}>{el}</Guard>
  return (
    <Ctx.Provider value={{ user, meta, settings, setSettings, logout, can }}>
      <ToastProvider>
        <Shell>
          <Routes>
            <Route path="/" element={R(['Manager', 'KOL TL', 'Direksi', 'Finance'], <Ringkasan />)} />
            <Route path="/tugas" element={<Tugas />} />
            <Route path="/campaign" element={R(['Manager', 'KOL TL', 'KOL Officer', 'Direksi'], <Campaigns />)} />
            <Route path="/campaign/:id" element={R(['Manager', 'KOL TL', 'KOL Officer', 'Direksi'], <CampaignDetail />)} />
            <Route path="/pipeline" element={R(['Manager', 'KOL TL', 'KOL Officer'], <Pipeline />)} />
            <Route path="/booking/:id" element={<BookingPage />} />
            <Route path="/input" element={R(['Manager', 'KOL TL', 'KOL Officer'], <InputKonten />)} />
            <Route path="/kol" element={R(['Manager', 'KOL TL', 'KOL Officer', 'Direksi'], <Kols />)} />
            <Route path="/kol/:id" element={R(['Manager', 'KOL TL', 'KOL Officer', 'Direksi'], <KolDetail />)} />
            <Route path="/budget" element={R(['Manager', 'KOL TL', 'Finance', 'Direksi'], <Budget />)} />
            <Route path="/pembayaran" element={R(['Manager', 'KOL TL', 'Finance'], <Pembayaran />)} />
            <Route path="/laporan" element={R(['Manager', 'KOL TL', 'KOL Officer', 'Direksi'], <Laporan />)} />
            <Route path="/pengaturan" element={R(['Manager', 'KOL TL'], <Pengaturan />)} />
            <Route path="*" element={<Navigate to={HOME[user.role] || '/'} replace />} />
          </Routes>
        </Shell>
      </ToastProvider>
    </Ctx.Provider>
  )
}
