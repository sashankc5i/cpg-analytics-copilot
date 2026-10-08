import { useEffect, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../auth'
import { ErrorBox, Modal, Pill, Table } from '../ui'

export default function Governance() {
  const { can, user } = useAuth(); const [tab, setTab] = useState('metrics'); const [d, setD] = useState({}); const [err, setErr] = useState(null); const [edit, setEdit] = useState(null); const [f, setF] = useState({ user: '', action: '' })
  const set = (k, v) => setD(x => ({ ...x, [k]: v }))
  const load = () => { api('/governance/metrics').then(v => set('metrics', v)).catch(setErr); api('/governance/rbac').then(v => set('rbac', v)).catch(setErr); api('/governance/lineage').then(v => set('lin', v)).catch(setErr) }
  const audit = () => can('audit_view') && api(`/governance/audit?user=${f.user}&action=${f.action}&limit=150`).then(v => set('audit', v)).catch(setErr)
  useEffect(load, []); useEffect(() => { audit() }, [f.user, f.action])
  const save = async () => { try { await api('/governance/metrics/' + edit.key, { method: 'PUT', body: { description: edit.description, status: edit.status } }); setEdit(null); load() } catch (e) { setErr(e) } }
  const tabs = [['metrics', 'Metric catalog'], ['access', 'Access & RBAC'], ['lineage', 'Lineage'], ...(can('audit_view') ? [['audit', 'Audit trail']] : [])]
  return <div className="page gap"><div><h1>Governance</h1><div className="muted">Certified definitions, role-based access, row-level security, lineage and audit.</div></div><ErrorBox e={err} />
    <div className="tabs">{tabs.map(([k, n]) => <button key={k} className={'tab ' + (tab === k ? 'on' : '')} onClick={() => setTab(k)}>{n}</button>)}</div>
    {tab === 'metrics' && <div className="grid g2">{d.metrics?.map(m => <div key={m.key} className="card"><div className="row between"><h3>{m.name}</h3><div className="row"><Pill kind={m.status}>{m.status}</Pill><span className="tag">v{m.version}</span></div></div>
      <div className="small">{m.description}</div><div className="mono muted" style={{ margin: '6px 0' }}>{m.formula}</div><div className="small muted">Owner: {m.owner} · updated {m.updated_at?.slice(0, 10)} by {m.updated_by}</div>
      {m.history?.length > 1 && <details className="small"><summary>History</summary>{m.history.map(h => <div key={h.id}>v{h.version} · {h.ts.slice(0, 10)} · {h.changed_by} · {h.status}</div>)}</details>}
      {can('metric_admin') && <button className="btn sm" style={{ marginTop: 8 }} onClick={() => setEdit({ ...m })}>Edit definition</button>}</div>)}</div>}
    {tab === 'access' && d.rbac && <div className="gap"><div className="card"><h3>Your access</h3><div className="small">Role <Pill kind="info">{user.role}</Pill> · Row-level scope: {Object.keys(user.scope).length ? Object.entries(user.scope).map(([k, v]) => <Pill key={k} kind="medium">{k} = {v.join(', ')}</Pill>) : <Pill kind="ok">unrestricted</Pill>}</div><div className="small muted" style={{ marginTop: 6 }}>Tools: {user.tools.join(', ') || 'none'}</div></div>
      <div className="card"><h3>Roles</h3><table><thead><tr><th>Role</th><th>Features</th><th>#Tools</th></tr></thead><tbody>{Object.entries(d.rbac.roles).map(([r, v]) => <tr key={r}><td><b>{r}</b></td><td className="small">{v.features.join(', ')}</td><td>{v.tools.length}</td></tr>)}</tbody></table></div>
      {d.rbac.users.length > 0 && <div className="card"><h3>Users & scopes</h3><Table rows={d.rbac.users.map(u => ({ ...u, scope: Object.keys(u.scope).length ? JSON.stringify(u.scope) : 'unrestricted' }))} /></div>}</div>}
    {tab === 'lineage' && d.lin && <div className="gap"><div className="card"><h3>Metric lineage</h3><Table rows={d.lin.metrics.map(m => ({ metric: m.name, formula: m.formula, table: m.source_table, system: m.system, refreshed: m.last_refreshed }))} /><div className="small muted" style={{ marginTop: 8 }}>Transformations on every result: {d.lin.metrics[0]?.transformations.join(' → ')}</div></div></div>}
    {tab === 'audit' && <div className="card"><div className="row" style={{ marginBottom: 8 }}><input placeholder="Filter by user id" value={f.user} onChange={e => setF({ ...f, user: e.target.value })} /><input placeholder="Filter by action (e.g. chat, metric.update)" value={f.action} onChange={e => setF({ ...f, action: e.target.value })} /></div>
      <div className="tw" style={{ maxHeight: 520 }}><table><thead><tr><th>Time</th><th>User</th><th>Action</th><th>Detail</th><th>Ref</th></tr></thead><tbody>{d.audit?.map(a => <tr key={a.id}><td className="mono">{a.ts.replace('T', ' ').slice(0, 19)}</td><td>{a.user_id.replace('u_', '')} <span className="muted small">{a.role}</span></td><td><Pill kind="info">{a.action}</Pill></td><td className="mono" style={{ maxWidth: 420, wordBreak: 'break-all' }}>{JSON.stringify(a.detail).slice(0, 220)}</td><td className="mono muted">{a.request_id}</td></tr>)}</tbody></table></div></div>}
    {edit && <Modal title={`Edit ${edit.name}`} onClose={() => setEdit(null)} actions={<button className="btn pri" onClick={save}>Save new version</button>}><div className="gap"><textarea rows={4} value={edit.description} onChange={e => setEdit({ ...edit, description: e.target.value })} /><select value={edit.status} onChange={e => setEdit({ ...edit, status: e.target.value })}><option>certified</option><option>draft</option><option>deprecated</option></select><div className="small muted">Changing the description creates a new version. Deprecated metrics are blocked from analysis.</div></div></Modal>}
  </div>
}
