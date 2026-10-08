import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search } from 'lucide-react'
import { api } from '../api'
import { ErrorBox, Pill } from '../ui'

export default function Knowledge() {
  const nav = useNavigate(); const [q, setQ] = useState(''); const [rows, setRows] = useState([]); const [err, setErr] = useState(null)
  useEffect(() => { const t = setTimeout(() => api('/memory/issues?q=' + encodeURIComponent(q)).then(setRows).catch(setErr), 250); return () => clearTimeout(t) }, [q])
  return <div className="page gap"><div><h1>Knowledge Base</h1><div className="muted">Institutional memory of past issues: what was found, what was ruled out, what worked.</div></div>
    <div className="row"><Search size={16} className="muted" /><input placeholder="Search past issues, e.g. stockout South beverages" value={q} onChange={e => setQ(e.target.value)} /></div><ErrorBox e={err} />
    {rows.map(r => <div key={r.id} className="card"><div className="row between wrap"><h3>{r.title}</h3><div className="row"><Pill kind="info">{r.source}</Pill><span className="small muted">{r.occurred_on}</span></div></div>
      <div className="small"><b>Root cause:</b> {r.root_cause}</div>
      <div className="row wrap small" style={{ gap: 6, marginTop: 6 }}>{r.signature?.supported?.map(h => <Pill key={h} kind="supported">{h} supported</Pill>)}{r.signature?.contradicted?.map(h => <Pill key={h} kind="contradicted">{h} ruled out</Pill>)}{r.signature?.unresolved?.map(h => <Pill key={h} kind="unresolved">{h} unresolved</Pill>)}</div>
      {r.outcome && <div className="notice ok small" style={{ marginTop: 8 }}><b>Action:</b> {r.outcome.action} — <b>Result:</b> {r.outcome.result}{r.outcome.notes && <div className="muted">{r.outcome.notes}</div>}</div>}
      {r.investigation_id && <button className="btn sm" style={{ marginTop: 8 }} onClick={() => nav('/investigations/' + r.investigation_id)}>Open investigation</button>}</div>)}
    {rows.length === 0 && <div className="muted">No matching issues.</div>}</div>
}
