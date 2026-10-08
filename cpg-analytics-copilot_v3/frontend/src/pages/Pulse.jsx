import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Line, LineChart, ResponsiveContainer } from 'recharts'
import { RefreshCw, Zap } from 'lucide-react'
import { api } from '../api'
import { useAuth } from '../auth'
import { Chart, ErrorBox, Pill, Spinner, fv, pctTxt } from '../ui'

const good = (k, d) => (k.hib === null ? 'info' : (d >= 0) === !!k.hib ? 'ok' : 'high')

export default function Pulse() {
  const nav = useNavigate(); const { can } = useAuth()
  const [ov, setOv] = useState(null); const [issues, setIssues] = useState(null); const [tl, setTl] = useState(null); const [err, setErr] = useState(null); const [busy, setBusy] = useState(false); const [exp, setExp] = useState(null)
  const load = () => { api('/pulse/overview').then(setOv).catch(setErr); api('/pulse/issues').then(r => setIssues(r.issues)).catch(setErr); api('/tools/business_timeline', { method: 'POST', body: { metric: 'revenue', period: 'last_26_weeks' } }).then(setTl).catch(() => {}) }
  useEffect(load, [])
  const scan = async (auto) => { setBusy(true); try { const r = await api('/pulse/scan?auto_create=' + auto, { method: 'POST' }); setIssues(r.issues) } catch (e) { setErr(e) } finally { setBusy(false) } }
  const inv = async (i) => { const r = await api(`/pulse/issues/${i.id}/investigate`, { method: 'POST' }); nav('/investigations/' + r.id) }
  const k = ov?.facts
  return <div className="page gap">
    <div className="row between"><div><h1>Business Pulse</h1><div className="muted">Proactive health, issue radar and the events behind KPI movement.</div></div>
      <div className="row"><button className="btn" onClick={load}><RefreshCw size={14} />Refresh</button>{can('investigate') && <button className="btn pri" disabled={busy} onClick={() => scan(true)}><Zap size={14} />{busy ? 'Scanning…' : 'Scan & auto-investigate'}</button>}</div></div>
    <ErrorBox e={err} />{!ov && <Spinner />}
    {k && <><div className="notice ok small">{ov.headline}</div>
      <div className="grid g3">{k.kpis.map(x => <div key={x.metric} className="card kpi"><div className="small muted">{x.name}</div><div className="v">{fv(x.unit, x.current)}</div>
        <div className={'small delta ' + (good(x, x.delta) === 'ok' ? 'up' : good(x, x.delta) === 'high' ? 'dn' : '')}>{x.unit === 'pct' ? `${x.delta > 0 ? '+' : ''}${x.delta?.toFixed(1)} pp` : pctTxt(x.pct)} vs prior period</div></div>)}</div>
      <div className="grid g2"><div className="card"><Chart chart={ov.chart} height={200} /></div>
        <div className="card"><h3>Biggest movers</h3>{Object.entries(k.movers).map(([d, rows]) => <div key={d} style={{ marginBottom: 8 }}><div className="small muted">By {d}</div>{rows.map(r => <div key={r.member} className="row between small"><span>{r.member}</span><span className={r.delta < 0 ? 'delta dn' : 'delta up'}>{fv('currency', r.delta)} ({pctTxt(r.pct)})</span></div>)}</div>)}</div></div></>}
    <div className="card"><h3>Business Issue Radar</h3><div className="small muted" style={{ marginBottom: 8 }}>Ranked by materiality: magnitude, persistence, importance and cross-domain breadth. Correlated signals are clustered into one issue.</div>
      {!issues && <Spinner />}{issues?.length === 0 && <div className="muted">No material issues detected.</div>}
      {issues?.filter(i => i.status !== 'dismissed').map(i => <div key={i.id} style={{ borderTop: '1px solid var(--line)', padding: '10px 0' }}>
        <div className="row between wrap"><div className="row"><Pill kind={i.severity}>{i.severity}</Pill><b style={{ cursor: 'pointer' }} onClick={() => setExp(exp === i.id ? null : i.id)}>{i.title}</b></div>
          <div className="row"><span className="small muted">materiality</span><div className="bar" style={{ width: 80 }}><i style={{ width: i.score + '%', background: i.severity === 'high' ? 'var(--red)' : 'var(--amber)' }} /></div><b>{i.score}</b>
            {i.investigation_id ? <button className="btn sm" onClick={() => nav('/investigations/' + i.investigation_id)}>Open investigation</button> : can('investigate') && <button className="btn pri sm" onClick={() => inv(i)}>Investigate</button>}
            <button className="btn sm" onClick={async () => { await api(`/pulse/issues/${i.id}/dismiss`, { method: 'POST' }); load() }}>Dismiss</button></div></div>
        <div className="row wrap small muted" style={{ gap: 6, marginTop: 4 }}>{i.domains.map(d => <Pill key={d} kind="info">{d}</Pill>)}<span>{i.n_signals} correlated signal(s) since {i.start_week}</span>{i.status === 'investigating' && <Pill kind="medium">investigating</Pill>}</div>
        {exp === i.id && <div className="small" style={{ marginTop: 8 }}>{i.signals.map((s, j) => <div key={j}>• <Pill kind="info">{s.domain}</Pill> {s.title} <span className="muted">(score {s.score})</span></div>)}
          <div className="muted" style={{ marginTop: 4 }}>Components — magnitude {i.components.magnitude}, persistence {i.components.persistence}, importance {i.components.importance}, breadth {i.components.breadth}</div></div>}</div>)}</div>
    {tl && <div className="card"><h3>Business timeline (last 26 weeks)</h3><Chart chart={tl.chart} height={240} /><div className="small">{tl.rows.map((e, i) => <div key={i}><span className="mono muted">{e.date}</span> <Pill kind="info">{e.kind}</Pill> {e.label}</div>)}</div></div>}
  </div>
}
