import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../api'
import { Chart, ErrorBox, Md, Pill } from '../ui'

export default function Shared() {
  const { token } = useParams(); const [d, setD] = useState(null); const [err, setErr] = useState(null)
  useEffect(() => { api('/shared/' + token).then(setD).catch(setErr) }, [token])
  if (err) return <div className="page"><ErrorBox e={err} /></div>
  if (!d) return null
  return <div className="page gap" style={{ maxWidth: 900, margin: '0 auto' }}>
    <div className="notice warn small">Read-only shared insight. Evidence labels refer to the owner's investigation workspace.</div>
    <div className="row between wrap"><h1>{d.title}</h1><Pill kind={d.confidence.level}>confidence {d.confidence.level} · {d.confidence.score}/100</Pill></div>
    <div className="card"><Md text={d.summary.narrative} /><p><b>{d.summary.conclusion}</b></p></div>
    <div className="card"><h3>Hypotheses tested</h3>{d.hypotheses.map(h => <div key={h.key} style={{ marginBottom: 8 }}><Pill kind={h.status}>{h.status}</Pill> <b>{h.statement}</b> <span className="muted small">{h.explained_pct}% of gap</span><div className="small muted">{h.rationale}</div></div>)}</div>
    <div className="card"><h3>Caveats & missing evidence</h3>{d.challenge.contradictions.map((c, i) => <div key={i} className="small">• {c.text}</div>)}{d.challenge.missing_evidence.map((c, i) => <div key={i} className="small muted">• {c.text}</div>)}</div>
    {d.charts.map(c => <div key={c.label} className="card"><div className="small"><span className="tag">{c.label}</span> {c.headline}</div><Chart chart={c.chart} /></div>)}</div>
}
