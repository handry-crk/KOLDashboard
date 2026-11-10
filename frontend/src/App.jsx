import { createContext, useContext, useEffect, useState } from 'react'
import { Navigate, NavLink, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { api, auth } from './api'
import { ToastProvider, Loading } from './components/ui'
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
const MOBILE = { 'KOL Officer': ['/tugas', '/input', '/pipeline', '/kol', '/campaign'], 'KOL TL': ['/', '/tugas', '/input', '/pipeline', '/kol'],
  Manager: ['/', '/tugas', '/campaign', '/pipeline', '/laporan'], Finance: ['/pembayaran', '/', '/budget', '/tugas'], Direksi: ['/', '/campaign', '/kol', '/laporan'] }
export const HOME = { 'KOL Officer': '/tugas', Finance: '/pembayaran' }

function Shell({ children }) {
  const { user, logout } = useApp()
  const nav = NAV.filter((n) => n.roles.includes(user.role))
  const mob = MOBILE[user.role].map((p) => NAV.find((n) => n.to === p))
  return (
    <div className="min-h-screen pb-24 sm:pb-8">
      <header className="no-print px-3 pt-3 sm:px-6">
        <div className="mx-auto max-w-7xl rounded-2xl bg-brand px-4 py-3 text-white shadow-sm">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white text-lg font-black text-brand">AA</div>
              <div>
                <div className="text-[11px] font-semibold uppercase tracking-widest text-white/80">Cimol Bojot AA · CRK</div>
                <div className="text-lg font-extrabold leading-tight">KOL Ledger</div>
              </div>
            </div>
            <div className="flex items-center gap-2 text-right">
              <div className="hidden sm:block"><div className="text-sm font-bold">{user.name}</div><div className="text-[11px] text-white/80">{user.role}</div></div>
              <button onClick={logout} className="rounded-xl bg-white/15 px-3 py-2 text-xs font-semibold hover:bg-white/25">Keluar</button>
            </div>
          </div>
          <nav className="mt-3 hidden flex-wrap gap-1 sm:flex">
            {nav.map((n) => (
              <NavLink key={n.to} to={n.to} end={n.to === '/'} className={({ isActive }) => `rounded-lg px-3 py-1.5 text-sm font-semibold ${isActive ? 'bg-white text-brand' : 'text-white/90 hover:bg-white/15'}`}>{n.label}</NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-3 py-4 sm:px-6">{children}</main>
      <nav className="no-print fixed inset-x-0 bottom-0 z-40 grid border-t border-brand-line bg-white sm:hidden" style={{ gridTemplateColumns: `repeat(${mob.length}, 1fr)` }}>
        {mob.map((n) => (
          <NavLink key={n.to} to={n.to} end={n.to === '/'} className={({ isActive }) => `flex min-h-[60px] flex-col items-center justify-center text-[11px] font-semibold ${isActive ? 'text-brand' : 'text-ink/60'}`}>
            <span className="text-lg leading-none">{n.icon}</span>{n.label}
          </NavLink>
        ))}
      </nav>
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
