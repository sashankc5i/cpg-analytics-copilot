import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ChevronDown, ChevronRight, Download, Link2, Pause, Play, Plus, Send, Share2, Trash2, ExternalLink } from 'lucide-react'
import { api, download } from '../api'
import { useAuth } from '../auth'
import { Chart, ErrorBox, EvidenceDrawer, Md, Modal, Pill, Spinner, Table, fv, pctTxt } from '../ui'

export function InvestigationList() {
  const nav = useNavigate(); const { can } = useAuth(); const [rows, setRows] = useState(null); const [st, setSt] = useState(''); const [q, setQ] = useState(''); const [obs, setObs] = useState(''); const [busy, setBusy] = useState(false); const [err, setErr] = useState(null)
  const load = () => api(`/investigations?status=${st}&q=${encodeURIComponent(q)}`).then(setRows).catch(setErr)
  useEffect(() => { load() }, [st, q])
  const create = async () => { if (!obs.trim()) return; setBusy(true); try { const r = await api('/investigations', { method: 'POST', body: { observation: obs } }); nav('/investigations/' + r.id) } catch (e) { setErr(e); setBusy(false) } }
  return <div className="page gap"><div><h1>Investigations</h1><div className="muted">Plan â†’ hypotheses â†’ evidence â†’ challenge â†’ conclusion. Every step is replayable.</div></div><ErrorBox e={err} />
    {can('investigate') && <div className="card"><h3>Start an investigation</h3><div className="row"><input placeholder='e.g. "Revenue fell in South beverages over the last 4 weeks"' value={obs} onChange={e => setObs(e.target.value)} onKeyDown={e => e.key === 'Enter' && create()} /><button className="btn pri" disabled={busy} onClick={create}><Plus size={14} />{busy ? 'Investigatingâ€¦' : 'Investigate'}</button></div></div>}
    <div className="row"><input placeholder="Search" value={q} onChange={e => setQ(e.target.value)} /><select style={{ width: 180 }} value={st} onChange={e => setSt(e.target.value)}><option value="">All statuses</option>{['open', 'in_progress', 'concluded', 'closed'].map(s => <option key={s}>{s}</option>)}</select></div>
    {!rows && <Spinner />}{rows?.map(r => <div key={r.id} className="card" style={{ cursor: 'pointer' }} onClick={() => nav('/investigations/' + r.id)}>
      <div className="row between wrap"><h3>{r.title}</h3><div className="row"><Pill kind={r.priority}>{r.priority}</Pill><Pill kind="info">{r.status}</Pill><Pill kind={r.confidence}>confidence {r.confidence}</Pill>{r.source === 'radar' && <Pill kind="medium">proactive</Pill>}</div></div>
      <div className="small muted">{r.lead ? `Leading explanation: ${r.lead}` : 'No supported cause yet'} Â· owner: {r.owner || 'unassigned'}{r.due_date && ` Â· due ${r.due_date}`}</div></div>)}
    {rows?.length === 0 && <div className="muted">No investigations yet.</div>}</div>
}

// ---------- driver tree
function TNode({ n, gap, unit, depth }) {
  const [open, setOpen] = useState(depth < 1); const w = Math.min(100, Math.abs((n.delta || 0) / (gap || 1)) * 100)
  return <div className="tnode"><div className="lbl" onClick={() => n.children?.length && setOpen(!open)}>
    {n.children?.length ? (open ? <ChevronDown size={14} /> : <ChevronRight size={14} />) : <span style={{ width: 14 }} />}
    <b style={{ minWidth: 130 }}>{n.label}</b><div className="bar" style={{ width: 120 }}><i style={{ width: w + '%', background: n.delta < 0 ? 'var(--red)' : 'var(--green)' }} /></div>
    <span className={n.delta < 0 ? 'delta dn' : 'delta up'}>{fv(unit, n.delta)}</span><span className="small muted">{n.share_of_gap != null && `${n.share_of_gap.toFixed(0)}% of gap`}{n.pct != null && ` Â· ${pctTxt(n.pct)}`}{n.dim && ` Â· ${n.dim}`}</span></div>
    {open && n.children?.length > 0 && <ul className="tree">{n.children.map((c, i) => <li key={i} style={{ listStyle: 'none' }}><TNode n={c} gap={gap} unit={unit} depth={depth + 1} /></li>)}</ul>}</div>
}
function Drivers({ id, onOpen }) {
  const [d, setD] = useState(null); const [err, setErr] = useState(null)
  useEffect(() => { api(`/investigations/${id}/driver-tree`).then(setD).catch(setErr) }, [id])
  if (err) return <ErrorBox e={err} />; if (!d) return <Spinner />
  const unit = d.metric === 'revenue' ? 'currency' : 'count'
  return <div className="gap"><div className="card"><div className="row between"><h3>Driver tree â€” {d.levels.join(' â†’ ')}</h3><button className="cite" onClick={() => onOpen(d.label)}>{d.label}</button></div><TNode n={d.tree} gap={d.tree.delta} unit={unit} depth={0} /></div>
    <div className="card"><Chart chart={d.chart} height={260} /></div>
    {d.pvm && <div className="card"><h3>Price / volume / mix</h3><div className="grid g4">{[['Volume', d.pvm.volume], ['Mix', d.pvm.mix], ['List price', d.pvm.list_price], ['Promo / discount', d.pvm.promo_discount]].map(([n, v]) => <div key={n} className="kpi"><div className="small muted">{n}</div><div className={'v ' + (v < 0 ? 'delta dn' : 'delta up')}>{fv('currency', v)}</div></div>)}</div></div>}</div>
}

// ---------- evidence graph
const REL = { supports: '#1f7a3f', explains: '#1f7a3f', contradicts: '#b4372c', weakens: '#b4372c', informs: '#9aa7a5', tested: '#9aa7a5', backs: '#5d45a5', asserts: '#57238b' }
function Graph({ id }) {
  const [g, setG] = useState(null); const [sel, setSel] = useState(null)
  useEffect(() => { api(`/investigations/${id}/graph`).then(setG) }, [id])
  const lay = useMemo(() => {
    if (!g) return null; const cols = { evidence: 0, claim: 1, hypothesis: 2, observation: 3 }, X = [20, 290, 560, 830], groups = [[], [], [], []]
    g.nodes.forEach(n => groups[cols[n.type]].push(n)); const pos = {}
    groups.forEach((col, ci) => col.forEach((n, i) => { pos[n.id] = { x: X[ci], y: 20 + i * 46 + (ci === 3 ? (Math.max(...groups.map(c => c.length)) * 46) / 2 - 20 : 0), n } }))
    return { pos, h: Math.max(...groups.map(c => c.length)) * 46 + 40 }
  }, [g])
  if (!g) return <Spinner />
  const conn = sel ? new Set(g.edges.filter(e => e.from === sel || e.to === sel).flatMap(e => [e.from, e.to])) : null
  const col = n => n.type === 'hypothesis' ? ({ supported: '#e0f2e6', contradicted: '#fbe4e1', unresolved: '#fcefd6', untestable: '#eceff0' }[n.status] || '#eee') : n.type === 'claim' ? '#eeeafb' : n.type === 'observation' ? '#241b30' : '#f0e8f8'
  const selNode = sel && lay.pos[sel]?.n
  return <div className="card"><div className="row small wrap" style={{ gap: 12, marginBottom: 6 }}><b>Evidence â†’ Claims â†’ Hypotheses â†’ Observation.</b>{Object.entries({ supports: 'supports', contradicts: 'contradicts / weakens', backs: 'backs claim' }).map(([k, n]) => <span key={k}><span style={{ color: REL[k] }}>â”</span> {n}</span>)}<span className="muted">Click a node to trace its connections.</span></div>
    <div style={{ overflow: 'auto' }}><svg width={1030} height={lay.h} style={{ minWidth: 1030 }}>
      {g.edges.map((e, i) => { const a = lay.pos[e.from], b = lay.pos[e.to]; if (!a || !b) return null; const x1 = a.x + 190, y1 = a.y + 15, x2 = b.x, y2 = b.y + 15; const on = !sel || e.from === sel || e.to === sel
        return <path key={i} d={`M${x1},${y1} C${x1 + 50},${y1} ${x2 - 50},${y2} ${x2},${y2}`} fill="none" stroke={REL[e.relation] || '#aaa'} strokeWidth={on ? 1.6 : .6} opacity={on ? .85 : .15} strokeDasharray={e.relation === 'weakens' ? '4 3' : ''} /> })}
      {Object.values(lay.pos).map(({ x, y, n }) => <g key={n.id} transform={`translate(${x},${y})`} onClick={() => setSel(sel === n.id ? null : n.id)} style={{ cursor: 'pointer' }} opacity={!conn || conn.has(n.id) || sel === n.id ? 1 : .3}>
        <rect width={190} height={30} rx={6} fill={col(n)} stroke={sel === n.id ? '#57238b' : '#cfd8d5'} strokeWidth={sel === n.id ? 2 : 1} /><text x={8} y={19} fontSize={11} fill={n.type === 'observation' ? '#fff' : '#241b30'}>{(n.label || '').slice(0, 30)}</text></g>)}
    </svg></div>
    {selNode && <div className="notice ok small" style={{ marginTop: 8 }}><b>{selNode.type}</b>: {selNode.label}{selNode.detail && <div className="muted">{selNode.detail}</div>}{selNode.status && <div>Status: {selNode.status}{selNode.score != null && ` Â· score ${selNode.score}`}</div>}</div>}</div>
}

// ---------- replay
function Replay({ id, onOpen }) {
  const [d, setD] = useState(null); const [i, setI] = useState(0); const [play, setPlay] = useState(false); const [err, setErr] = useState(null)
  useEffect(() => { api(`/investigations/${id}/replay`).then(setD).catch(setErr) }, [id])
  useEffect(() => { if (!play || !d) return; const t = setInterval(() => setI(x => { if (x >= d.steps.length - 1) { setPlay(false); return x } return x + 1 }), 1300); return () => clearInterval(t) }, [play, d])
  if (err) return <ErrorBox e={err} />; if (!d) return <Spinner />
  const s = d.steps[i]; const icon = { observe: 'ðŸ‘', test: 'ðŸ§ª', hypothesize: 'ðŸ’¡', rank: 'ðŸ“Š', challenge: 'âš–', conclude: 'âœ…' }
  return <div className="gap"><div className="row"><button className="btn pri sm" onClick={() => { if (i >= d.steps.length - 1) setI(0); setPlay(!play) }}>{play ? <Pause size={12} /> : <Play size={12} />}{play ? 'Pause' : 'Replay'}</button><span className="small muted">Step {i + 1} of {d.steps.length} â€” reconstructs how the conclusion was reached; nothing is re-computed.</span></div>
    <div className="replay"><div className="card flat" style={{ maxHeight: 520, overflow: 'auto' }}>{d.steps.map((x, j) => <div key={j} className={'step' + (j === i ? ' on' : '')} onClick={() => { setPlay(false); setI(j) }}><span className="small muted">{x.n}.</span> {icon[x.kind]} <span className="small">{x.title}</span></div>)}</div>
      <div className="card"><div className="row between"><h3>{icon[s.kind]} {s.title}</h3><Pill kind="info">{s.kind}</Pill></div><div className="small muted">{s.ts.replace('T', ' ').slice(0, 19)}{s.duration_ms != null && ` Â· ${s.duration_ms}ms`}</div>
        {s.detail && <p>{s.detail}</p>}{s.tool && <><div className="small muted">Tool & arguments</div><pre>{s.tool}({JSON.stringify(s.args, null, 1)})</pre></>}{s.evidence?.map(l => <button key={l} className="cite" onClick={() => onOpen(l)}>{l}</button>)}</div></div></div>
}

// ---------- tabs
function Summary({ inv, onOpen }) {
  const s = inv.summary; const c = inv.confidence
  return <div className="gap"><div className="card"><div className="row between wrap"><h3>Executive summary</h3><Pill kind={c.level}>confidence {c.level} Â· {c.score}/100</Pill></div><Md text={s.narrative} onCite={onOpen} /><div className="notice ok" style={{ marginTop: 8 }}><b>{s.conclusion}</b></div></div>
    <div className="grid g2"><div className="card"><h3>Claims â†’ evidence</h3>{s.claims.map(cl => <div key={cl.id} style={{ marginBottom: 8 }}><Pill kind={cl.kind === 'finding' ? 'ok' : 'medium'}>{cl.kind}</Pill> <span className="small">{cl.text}</span> {cl.evidence.map(l => <button key={l} className="cite" onClick={() => onOpen(l)}>{l}</button>)}</div>)}</div>
      <div className="card"><h3>Confidence factors</h3><table><tbody>{c.factors.map((f, i) => <tr key={i}><td>{f.label}<div className="small muted">{f.detail}</div></td><td className={'num ' + (f.effect < 0 ? 'delta dn' : 'delta up')}>{f.effect > 0 ? '+' : ''}{f.effect}</td></tr>)}<tr><td><b>Total</b></td><td className="num"><b>{c.score}</b></td></tr></tbody></table></div></div>
    <div className="card"><h3>Recommended actions <span className="small muted">â€” kept separate from evidence</span></h3>{s.recommendations.map((r, i) => <div key={i} style={{ borderTop: i ? '1px solid var(--line)' : 'none', padding: '8px 0' }}><b>{r.action}</b><div className="small"><b>Why:</b> {r.rationale} {r.evidence.map(l => <button key={l} className="cite" onClick={() => onOpen(l)}>{l}</button>)}</div>{r.assumptions.length > 0 && <div className="small muted"><b>Assumptions:</b> {r.assumptions.join(' Â· ')}</div>}<div className="small"><b>Expected impact:</b> {r.expected_impact}</div></div>)}</div>
    {s.limitations.length > 0 && <div className="notice warn small"><b>Data limitations:</b> {s.limitations.join(' Â· ')}</div>}</div>
}

function Ledger({ inv, onOpen }) {
  const [open, setOpen] = useState(null); const cause = inv.hypotheses.filter(h => h.category === 'Cause'), loc = inv.hypotheses.filter(h => h.category !== 'Cause')
  const Row = h => <div key={h.key} className="card flat" style={{ marginBottom: 8 }}><div className="row between wrap" style={{ cursor: 'pointer' }} onClick={() => setOpen(open === h.key ? null : h.key)}>
    <div className="row"><Pill kind={h.status}>{h.status}</Pill><b>{h.statement}</b></div><div className="row small">{h.rank && <span className="tag">#{h.rank}</span>}<span className="muted">{h.explained_pct}% of gap Â· score {h.score}</span></div></div>
    <div className="small" style={{ marginTop: 4 }}>{h.rationale} {h.evidence.map(l => <button key={l} className="cite" onClick={() => onOpen(l)}>{l}</button>)}</div>
    {open === h.key && <div style={{ marginTop: 8 }}><div className="grid g4 small">{Object.entries(h.criteria).map(([k, v]) => <div key={k}><div className="muted">{k}</div><div className="bar"><i style={{ width: v * 100 + '%' }} /></div><b>{v}</b></div>)}</div>
      {h.contradictions.map((c, i) => <div key={i} className="notice warn small" style={{ marginTop: 6 }}>âš  {c.text}</div>)}{h.limitations.map((l, i) => <div key={i} className="small muted">â€¢ {l}</div>)}{h.data_needed && <div className="small muted">Data needed: {h.data_needed}</div>}
      <div className="small muted" style={{ marginTop: 4 }}>score = 0.45Â·materiality + 0.25Â·strength + 0.20Â·consistency + 0.10Â·coverage</div></div>}</div>
  return <div className="gap"><div className="card"><h3>Hypothesis ledger â€” causes</h3>{cause.map(Row)}</div><div className="card"><h3>Where is it happening? <span className="small muted">(localisation, not cause)</span></h3>{loc.map(Row)}</div></div>
}

function Challenge({ inv, onOpen }) {
  const c = inv.challenge
  return <div className="grid g3">
    <div className="card"><h3>âš  Contradictions</h3>{c.contradictions.length ? c.contradictions.map((x, i) => <div key={i} className="small" style={{ marginBottom: 6 }}>{x.text} {x.evidence?.map(l => <button key={l} className="cite" onClick={() => onOpen(l)}>{l}</button>)}</div>) : <div className="muted small">None found against the leading explanation.</div>}</div>
    <div className="card"><h3>â†” Alternative explanations</h3>{c.alternatives.length ? c.alternatives.map((a, i) => <div key={i} className="small" style={{ marginBottom: 6 }}><Pill kind={a.status}>{a.status}</Pill> {a.statement}{a.explained_pct != null && <b> Â· {a.explained_pct}%</b>} {a.evidence.map(l => <button key={l} className="cite" onClick={() => onOpen(l)}>{l}</button>)}</div>) : <div className="muted small">None.</div>}</div>
    <div className="card"><h3>? Missing evidence</h3>{c.missing_evidence.map((m, i) => <div key={i} className="small" style={{ marginBottom: 6 }}>{m.text}<div className="muted">Needed: {m.data_needed}</div></div>)}</div></div>
}

function Team({ inv, reload }) {
  const { can, user } = useAuth(); const [err, setErr] = useState(null); const [c, setC] = useState(''); const [a, setA] = useState(''); const [own, setOwn] = useState(inv.owner || ''); const [due, setDue] = useState(inv.due_date || '')
  const [out, setOut] = useState({ action: '', result: '', notes: '' }); const [mon, setMon] = useState(null); const [bi, setBi] = useState(null); const [msg, setMsg] = useState(null); const [users, setUsers] = useState('')
  const run = async fn => { try { setErr(null); await fn(); reload() } catch (e) { setErr(e) } }
  return <div className="gap"><ErrorBox e={err} />{msg && <div className="notice ok small">{msg}</div>}
    <div className="grid g2"><div className="card"><h3>Ownership</h3>{can('assign') ? <div className="gap"><div className="row"><input placeholder="owner username (e.g. analyst)" value={own} onChange={e => setOwn(e.target.value)} /><input type="date" value={due} onChange={e => setDue(e.target.value)} /></div><button className="btn pri sm" onClick={() => run(() => api(`/investigations/${inv.id}/assign`, { method: 'POST', body: { owner: own, due_date: due || null } }))}>Assign</button></div> : <div className="small">Owner: {inv.owner || 'unassigned'} {inv.due_date && `Â· due ${inv.due_date}`}<div className="muted">Your role cannot assign.</div></div>}</div>
      <div className="card"><h3>Share & integrate</h3><div className="row wrap">{can('share') && <button className="btn sm" onClick={() => run(async () => { const r = await api(`/investigations/${inv.id}/share`, { method: 'POST', body: { mode: 'link', expires_hours: 72 } }); setMsg('Read-only link (72h): ' + location.origin + r.path) })}><Link2 size={12} />Create share link</button>}
        <button className="btn sm" onClick={() => run(async () => { const r = await api(`/investigations/${inv.id}/workflow`, { method: 'POST' }); setMsg(`Workflow task ${r.id} ${r.status} (${r.system})`) })}><Send size={12} />Create workflow task</button>
        <button className="btn sm" onClick={async () => setBi(await api('/integrations/bi-links?investigation_id=' + inv.id))}><ExternalLink size={12} />Open in BI</button></div>
        {can('share') && <div className="row" style={{ marginTop: 8 }}><input placeholder="share with usernames, comma-separated" value={users} onChange={e => setUsers(e.target.value)} /><button className="btn sm" onClick={() => run(async () => { await api(`/investigations/${inv.id}/share`, { method: 'POST', body: { mode: 'users', users: users.split(',').map(s => s.trim()).filter(Boolean) } }); setUsers(''); setMsg('Shared.') })}><Share2 size={12} />Share</button></div>}
        {inv.shares.filter(s => !s.revoked).map(s => <div key={s.token} className="small" style={{ marginTop: 6 }}>ðŸ”— /shared/{s.token.slice(0, 10)}â€¦ exp {s.expires_at.slice(0, 10)} <button className="btn sm danger" onClick={() => run(() => api(`/investigations/${inv.id}/share/${s.token}`, { method: 'DELETE' }))}>Revoke</button></div>)}
        {bi && <div className="small" style={{ marginTop: 6 }}>{bi.map(b => <div key={b.name}><a href={b.url} target="_blank" rel="noreferrer">{b.name}</a></div>)}</div>}
        {inv.workflow_tasks.map(t => <div key={t.id} className="small muted">Task {t.id} Â· {t.system} Â· {t.status}</div>)}</div></div>
    <div className="card"><h3>Actions</h3>{inv.actions.map(x => <div key={x.id} className="row between small" style={{ padding: '4px 0', borderBottom: '1px solid var(--line)' }}><span>{x.title} <span className="muted">{x.owner && `Â· ${x.owner}`}</span></span><select style={{ width: 130 }} value={x.status} onChange={e => run(() => api('/actions/' + x.id, { method: 'PATCH', body: { status: e.target.value } }))}><option>open</option><option>in_progress</option><option>done</option></select></div>)}
      <div className="row" style={{ marginTop: 8 }}><input placeholder="New action, e.g. Expedite replenishment in South" value={a} onChange={e => setA(e.target.value)} /><button className="btn pri sm" onClick={() => a && run(async () => { await api(`/investigations/${inv.id}/actions`, { method: 'POST', body: { title: a, owner: inv.owner } }); setA('') })}>Add</button></div></div>
    <div className="grid g2"><div className="card"><h3>Outcome tracking</h3>{inv.outcomes.map(o => <div key={o.id} className="small notice ok" style={{ marginBottom: 4 }}><b>{o.action}</b> â†’ {o.result}</div>)}
      <div className="gap"><input placeholder="Action taken" value={out.action} onChange={e => setOut({ ...out, action: e.target.value })} /><input placeholder="Result observed" value={out.result} onChange={e => setOut({ ...out, result: e.target.value })} /><button className="btn pri sm" onClick={() => out.action && out.result && run(async () => { await api(`/investigations/${inv.id}/outcomes`, { method: 'POST', body: out }); setOut({ action: '', result: '', notes: '' }) })}>Record outcome</button></div>
      <button className="btn sm" style={{ marginTop: 8 }} onClick={async () => setMon(await api(`/investigations/${inv.id}/outcome-monitor`))}>Monitor recovery</button>
      {mon && <div className="small" style={{ marginTop: 8 }}><Pill kind={mon.status === 'recovered' ? 'ok' : 'medium'}>{mon.status}</Pill> baseline {fv('currency', mon.baseline_weekly_avg)}/wk â†’ issue {fv('currency', mon.issue_weekly_avg)}/wk{mon.recovery_pct != null && ` â†’ recovery ${mon.recovery_pct.toFixed(0)}%`}<Chart chart={mon.chart} height={180} /></div>}</div>
      <div className="card"><h3>Discussion</h3><div style={{ maxHeight: 240, overflow: 'auto' }}>{inv.comments.map(m => <div key={m.id} className="small" style={{ marginBottom: 6 }}><b>{m.author}</b> <span className="muted">{m.created_at.slice(0, 16).replace('T', ' ')}</span><div>{m.body.split(/(@\w+)/).map((p, i) => p.startsWith('@') ? <span key={i} className="tag">{p}</span> : p)}</div></div>)}{!inv.comments.length && <div className="muted small">No comments. Mention teammates with @username.</div>}</div>
        {can('comment') && <div className="row" style={{ marginTop: 8 }}><input placeholder="Add a commentâ€¦ @analyst" value={c} onChange={e => setC(e.target.value)} onKeyDown={e => e.key === 'Enter' && c && run(async () => { await api(`/investigations/${inv.id}/comments`, { method: 'POST', body: { body: c } }); setC('') })} /><button className="btn pri sm" onClick={() => c && run(async () => { await api(`/investigations/${inv.id}/comments`, { method: 'POST', body: { body: c } }); setC('') })}>Post</button></div>}</div></div></div>
}

function Memory({ inv }) {
  const nav = useNavigate(); const s = inv.similar || [], r = inv.recall || {}
  return <div className="gap"><div className="card"><h3>Similar past issues</h3>{!s.length && <div className="muted small">No similar issues in memory yet.</div>}{s.map(x => <div key={x.id} style={{ borderTop: '1px solid var(--line)', padding: '8px 0' }}><div className="row between wrap"><b>{x.title}</b><div className="row"><Pill kind="info">similarity {(x.similarity * 100).toFixed(0)}%</Pill><span className="small muted">{x.occurred_on}</span></div></div>
    <div className="small">Root cause then: {x.root_cause}</div><div className="row wrap small" style={{ gap: 6, marginTop: 4 }}>{x.shared.supported.map(h => <Pill key={h} kind="supported">same: {h}</Pill>)}{x.differs.this_only_supported.map(h => <Pill key={h} kind="medium">new now: {h}</Pill>)}{x.differs.past_only_supported.map(h => <Pill key={h} kind="low">only then: {h}</Pill>)}{x.shared.entities.map(e => <span key={e} className="tag">{e}</span>)}</div>
    {x.outcome && <div className="small notice ok" style={{ marginTop: 4 }}><b>What worked:</b> {x.outcome.action} â€” {x.outcome.result}</div>}{x.investigation_id && <button className="btn sm" style={{ marginTop: 4 }} onClick={() => nav('/investigations/' + x.investigation_id)}>Open</button>}</div>)}</div>
    {Object.keys(r).length > 0 && <div className="card"><h3>Hypothesis recall across similar issues</h3><table><thead><tr><th>Hypothesis</th><th>Supported</th><th>Ruled out</th><th>Unresolved</th></tr></thead><tbody>{Object.entries(r).map(([k, v]) => <tr key={k}><td><b>{k}</b></td><td>{v.supported}</td><td>{v.contradicted}</td><td>{v.unresolved}</td></tr>)}</tbody></table></div>}</div>
}

export function InvestigationDetail() {
  const { id } = useParams(); const nav = useNavigate(); const { can } = useAuth(); const [inv, setInv] = useState(null); const [err, setErr] = useState(null); const [tab, setTab] = useState('summary'); const [ev, setEv] = useState(null); const [del, setDel] = useState(false)
  const load = () => api('/investigations/' + id).then(setInv).catch(setErr)
  useEffect(() => { setInv(null); load() }, [id])
  if (err && !inv) return <div className="page"><ErrorBox e={err} /></div>; if (!inv) return <div className="page"><Spinner /></div>
  const setStatus = async s => { await api('/investigations/' + id, { method: 'PATCH', body: { status: s } }); load() }
  const tabs = [['summary', 'Summary'], ['ledger', 'Hypotheses'], ['challenge', 'Challenge'], ['drivers', 'Drivers'], ['graph', 'Evidence graph'], ['replay', 'Replay'], ['plan', 'Plan'], ['evidence', `Evidence (${inv.evidence.length})`], ['team', 'Team & actions'], ['memory', 'Memory']]
  return <div className="page">
    <div className="row between wrap"><div><div className="row"><Pill kind={inv.priority}>{inv.priority}</Pill>{inv.source === 'radar' && <Pill kind="medium">proactive</Pill>}<span className="small muted">{inv.id}</span></div><h1 style={{ marginTop: 4 }}>{inv.title}</h1><div className="muted small">{inv.observation}</div></div>
      <div className="row wrap">{can('investigate') && <select style={{ width: 140 }} value={inv.status} onChange={e => setStatus(e.target.value)}>{['open', 'in_progress', 'concluded', 'closed'].map(s => <option key={s}>{s}</option>)}</select>}
        {can('export') && ['md', 'html', 'json'].map(f => <button key={f} className="btn sm" onClick={() => download(`/investigations/${id}/export?format=${f}`, `investigation-${id}.${f}`)}><Download size={12} />{f}</button>)}
        {can('investigate') && <button className="btn sm danger" onClick={() => setDel(true)}><Trash2 size={12} /></button>}</div></div>
    <div className="grid g4" style={{ margin: '14px 0' }}>{[['Current', fv(inv.gap.metric === 'revenue' ? 'currency' : 'count', inv.gap.current), inv.gap.current_label], ['Prior', fv(inv.gap.metric === 'revenue' ? 'currency' : 'count', inv.gap.prior), inv.gap.prior_label], ['Change', pctTxt(inv.gap.pct), fv(inv.gap.metric === 'revenue' ? 'currency' : 'count', inv.gap.delta)], ['Confidence', inv.confidence.level, `${inv.confidence.score}/100`]].map(([n, v, s]) => <div key={n} className="card kpi"><div className="small muted">{n}</div><div className={'v ' + (n === 'Change' && inv.gap.delta < 0 ? 'delta dn' : '')}>{v}</div><div className="small muted">{s}</div></div>)}</div>
    <ErrorBox e={err} /><div className="tabs">{tabs.map(([k, n]) => <button key={k} className={'tab ' + (tab === k ? 'on' : '')} onClick={() => setTab(k)}>{n}</button>)}</div>
    {tab === 'summary' && <Summary inv={inv} onOpen={setEv} />}{tab === 'ledger' && <Ledger inv={inv} onOpen={setEv} />}{tab === 'challenge' && <Challenge inv={inv} onOpen={setEv} />}{tab === 'drivers' && <Drivers id={id} onOpen={setEv} />}
    {tab === 'graph' && <Graph id={id} />}{tab === 'replay' && <Replay id={id} onOpen={setEv} />}
    {tab === 'plan' && <div className="card"><h3>Investigation plan</h3><table><thead><tr><th>#</th><th>Step</th><th>Question</th><th>Tool</th></tr></thead><tbody>{inv.plan.map(p => <tr key={p.id}><td>{p.id}</td><td><b>{p.step}</b></td><td>{p.question}</td><td className="mono">{p.tool}</td></tr>)}</tbody></table></div>}
    {tab === 'evidence' && <div className="card"><h3>Evidence collected</h3>{inv.evidence.map(e => <div key={e.label} className="row" style={{ padding: '6px 0', borderBottom: '1px solid var(--line)' }}><button className="cite" onClick={() => setEv(e.label)}>{e.label}</button><b className="small" style={{ minWidth: 150 }}>{e.tool}</b><span className="small">{e.headline}</span></div>)}</div>}
    {tab === 'team' && <Team inv={inv} reload={load} />}{tab === 'memory' && <Memory inv={inv} />}
    {ev && <EvidenceDrawer ownerType="investigation" ownerId={id} label={ev} onClose={() => setEv(null)} />}
    {del && <Modal title="Delete investigation?" onClose={() => setDel(false)} actions={<button className="btn danger" onClick={async () => { await api('/investigations/' + id, { method: 'DELETE' }); nav('/investigations') }}>Delete permanently</button>}>Removes the investigation, its evidence, comments, actions and memory entry.</Modal>}
  </div>
}
