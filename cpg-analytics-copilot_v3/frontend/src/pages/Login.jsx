import { useEffect, useState } from 'react'
import { useAuth } from '../auth'
import { api } from '../api'
import { ErrorBox, Pill } from '../ui'

export default function Login() {
  const { login } = useAuth(); const [info, setInfo] = useState(null); const [u, setU] = useState(''); const [p, setP] = useState(''); const [err, setErr] = useState(null); const [h, setH] = useState(null); const [busy, setBusy] = useState(false)
  useEffect(() => { api('/auth/demo-users').then(i => { setInfo(i); if (i.mode === 'local') setU(current => current || 'admin'); if (i.password_hint) setP(i.password_hint) }).catch(() => {}); api('/health').then(setH).catch(() => {}) }, [])
  const go = async (name = u, password = p) => { try { setErr(null); setBusy(true); await login(name, password) } catch (e) { setErr(e) } finally { setBusy(false) } }
  return <div className="login"><div className="card gap">
    <div className="login-heading"><span className="brand-mark">C5i</span><div><div className="eyebrow">Human • AI • Impact</div><h1>Analytics Copilot</h1><div className="muted">Governed, evidence-backed answers and investigations.</div></div></div>
    {h && <div><Pill kind={h.llm === 'groq' ? 'ok' : 'medium'}>{h.llm === 'groq' ? `Groq · ${h.model}` : 'Offline planner (set GROQ_API_KEY for the LLM)'}</Pill></div>}
    <form className="gap" onSubmit={e => { e.preventDefault(); go() }}><input name="username" type="text" autoComplete="username" placeholder={info?.mode === 'local' ? 'Username (for example, admin)' : 'Email or username'} value={u} onChange={e => setU(e.target.value)} autoFocus required /><input name="password" type="password" autoComplete="current-password" placeholder="Password" value={p} onChange={e => setP(e.target.value)} required /><button className="btn pri" style={{ justifyContent: 'center' }} disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button></form>
    <ErrorBox e={err} />
    {info?.mode === 'local' && <div><div className="small muted" style={{ marginBottom: 6 }}>Demo users — click to sign in (password <code>{info.password_hint}</code>)</div>
      <div className="grid g2">{info.users.map(x => <button key={x.username} type="button" className="btn" style={{ justifyContent: 'space-between' }} disabled={busy} onClick={() => go(x.username, info.password_hint || '')}><span>{x.name}</span><Pill kind="info">{x.role}{Object.keys(x.scope).length ? ' · scoped' : ''}</Pill></button>)}</div></div>}
  </div></div>
}

