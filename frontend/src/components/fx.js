// Efek perayaan ringan (tanpa library): ledakan ikon reaksi KOL dari titik tertentu
const ICONS = ['❤️', '⭐', '👍', '🎉', '🔥', '💬', '▶️']
const COLORS = ['#D7191F', '#E8A317', '#1E8E3E', '#2F6DB5', '#F7D4D5']
export const reducedMotion = () => typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

export function celebrate(x, y, n = 34) {
  if (reducedMotion() || typeof document === 'undefined') return
  const cx = x ?? window.innerWidth / 2, cy = y ?? window.innerHeight / 2
  for (let i = 0; i < n; i++) {
    const el = document.createElement('span')
    el.className = 'fx-particle'
    const ang = Math.random() * Math.PI * 2, dist = 90 + Math.random() * 180
    el.style.left = cx + 'px'; el.style.top = cy + 'px'
    el.style.setProperty('--dx', Math.cos(ang) * dist + 'px')
    el.style.setProperty('--dy', Math.sin(ang) * dist - 60 + 'px')
    el.style.setProperty('--rot', (Math.random() * 540 - 270) + 'deg')
    el.style.animationDelay = Math.random() * 0.08 + 's'
    if (i % 2) { el.textContent = ICONS[i % ICONS.length]; el.style.fontSize = 14 + Math.random() * 12 + 'px' }
    else { el.style.width = el.style.height = 6 + Math.random() * 6 + 'px'; el.style.borderRadius = i % 4 ? '2px' : '999px'; el.style.background = COLORS[i % COLORS.length] }
    document.body.appendChild(el)
    setTimeout(() => el.remove(), 1500)
  }
}

export function celebrateFrom(ev, n) {
  const r = ev?.currentTarget?.getBoundingClientRect?.()
  celebrate(r ? r.left + r.width / 2 : undefined, r ? r.top + r.height / 2 : undefined, n)
}
