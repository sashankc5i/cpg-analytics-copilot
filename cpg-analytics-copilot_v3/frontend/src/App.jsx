import { useEffect, useState } from 'react'
import { NavLink, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { Activity, BookOpen, Bell, ChevronDown, LogOut, MessageSquare, Search, ShieldCheck, Radar } from 'lucide-react'
import { useAuth } from './auth'
import { api } from './api'
import Login from './pages/Login'
import Chat from './pages/Chat'
import Pulse from './pages/Pulse'
import { InvestigationList, InvestigationDetail } from './pages/Investigations'
import Knowledge from './pages/Knowledge'
import Governance from './pages/Governance'
import Operations from './pages/Operations'
import Shared from './pages/Shared'

function Notifications() {
  const [open, setOpen] = useState(false); const [items, setItems] = useState([]); const nav = useNavigate()
  const load = () => api('/notifications').then(setItems).catch(() => {})
  useEffect(() => { load(); const t = setInterval(load, 30000); return () => clearInterval(t) }, [])
  const unread = items.filter(i => !i.read).length
  return <div style={{ position: 'relative' }}>
    <button className="nav" style={{ width: '100%', background: 'none', border: 'none' }} onClick={() => { setOpen(!open); if (!open && unread) api('/notifications/read', { method: 'POST' }).then(load) }}><Bell size={16} />Notifications{unread > 0 && <span className="pill high">{unread}</span>}</button>
    {open && <div className="card" style={{ position: 'fixed', left: 230, bottom: 70, width: 320, maxHeight: 380, overflow: 'auto', zIndex: 30, color: 'var(--ink)' }}>
      {items.length === 0 && <div className="muted small">Nothing yet.</div>}
      {items.map(n => <div key={n.id} style={{ padding: '6px 0', borderBottom: '1px solid var(--line)', cursor: 'pointer' }} onClick={() => { setOpen(false); nav(n.link) }}><span className="pill info">{n.kind}</span> <span className="small">{n.body}</span></div>)}</div>}
  </div>
}

function Shell() {
  const { user, logout, can } = useAuth()
  const links = [['/pulse', Radar, 'Business Pulse', 'chat'], ['/investigations', Search, 'Investigations', 'investigate'], ['/knowledge', BookOpen, 'Knowledge Base', 'chat'], ['/governance', ShieldCheck, 'Governance', null], ['/operations', Activity, 'Operations', null]]
  return <div className="app"><aside className="side"><div className="brand"><span className="brand-mark">C5i</span><span className="brand-name">Analytics Copilot<small>Human • AI • Impact</small></span></div>
    <NavLink to="/" end className={({ isActive }) => 'nav' + (isActive ? ' active' : '')}><MessageSquare size={16} />Copilot Chat<ChevronDown size={14} className="nav-branch-icon" /></NavLink>
    <div id="chat-branch-host" className="chat-branch-host" />
    {links.filter(l => !l[3] || can(l[3]) || l[3] === 'investigate').map(([to, I, n]) => <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => 'nav' + (isActive ? ' active' : '')}><I size={16} />{n}</NavLink>)}
    <Notifications />
    <div className="who"><b>{user.display_name}</b><small>{user.role}{Object.keys(user.scope).length ? ` · scope ${Object.entries(user.scope).map(([k, v]) => k + '=' + v.join('/')).join(', ')}` : ''}</small>
      <button className="btn sm" style={{ marginTop: 8 }} onClick={logout}><LogOut size={12} />Sign out</button></div></aside>
    <main className="main"><Routes>
      <Route path="/" element={<Chat />} /><Route path="/pulse" element={<Pulse />} />
      <Route path="/investigations" element={<InvestigationList />} /><Route path="/investigations/:id" element={<InvestigationDetail />} />
      <Route path="/knowledge" element={<Knowledge />} /><Route path="/governance" element={<Governance />} /><Route path="/operations" element={<Operations />} />
      <Route path="*" element={<Navigate to="/" />} /></Routes></main></div>
}

export default function App() {
  const { user, ready } = useAuth(); const loc = useLocation()
  if (loc.pathname.startsWith('/shared/')) return <Routes><Route path="/shared/:token" element={<Shared />} /></Routes>
  if (!ready) return null
  if (!user) return loc.pathname === '/login' ? <Login /> : <Navigate to="/login" />
  if (loc.pathname === '/login') return <Navigate to="/" />
  return <Shell />
}
