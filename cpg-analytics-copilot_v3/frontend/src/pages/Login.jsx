import { useEffect, useState } from 'react'
import { useAuth } from '../auth'
import { api } from '../api'
import { ErrorBox, Pill } from '../ui'

export default function Login() {
  const { login } = useAuth(); const [info, setInfo] = useState(null); const [u, setU] = useState(''); const [p, setP] = useState(''); const [err, setErr] = useState(null); const [h, setH] = useState(null)
  useEffect(() => { api('/auth/demo-users').then(i => { setInfo(i); setP(i.password_hint || '') }).catch(() => {}); api('/health').then(setH).catch(() => {}) }, [])
  const go = async (name) => { try { setErr(null); await login(name || u, p) } catch (e) { setErr(e) } }
  return <div className="login"><div className="card gap">
    <div className="login-heading"><span className="brand-mark">C5i</span><div><div className="eyebrow">Human • AI • Impact</div><h1>Analytics Copilot</h1><div className="muted">Governed, evidence-backed answers and investigations.</div></div></div>
    {h && <div><Pill kind={h.llm === 'groq' ? 'ok' : 'medium'}>{h.llm === 'groq' ? `Groq · ${h.model}` : 'Offline planner (set GROQ_API_KEY for the LLM)'}</Pill></div>}
    <form className="gap" onSubmit={e => { e.preventDefault(); go() }}><input placeholder="Username" value={u} onChange={e => setU(e.target.value)} autoFocus /><input type="password" placeholder="Password" value={p} onChange={e => setP(e.target.value)} /><button className="btn pri" style={{ justifyContent: 'center' }}>Sign in</button></form>
    <ErrorBox e={err} />
    {info?.mode === 'local' && <div><div className="small muted" style={{ marginBottom: 6 }}>Demo users — click to sign in (password <code>{info.password_hint}</code>)</div>
      <div className="grid g2">{info.users.map(x => <button key={x.username} className="btn" style={{ justifyContent: 'space-between' }} onClick={() => go(x.username)}><span>{x.name}</span><Pill kind="info">{x.role}{Object.keys(x.scope).length ? ' · scoped' : ''}</Pill></button>)}</div></div>}
  </div></div>
}

