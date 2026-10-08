import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import { ErrorBox, Pill, Table } from '../ui'

export default function Operations() {
  const { can } = useAuth(); const nav = useNavigate(); const [tab, setTab] = useState('integrations'); const [d, setD] = useState({}); const [err, setErr] = useState(null); const [test, setTest] = useState(null)
  const set = (k, v) => setD(x => ({ ...x, [k]: v }))
  useEffect(() => {
    api('/integrations').then(v => set('int', v)).catch(setErr); api('/data/freshness').then(v => set('fresh', v)).catch(setErr); api('/data/quality').then(v => set('dq', v)).catch(setErr); api('/actions').then(v => set('actions', v)).catch(setErr)
    if (can('telemetry_view')) api('/admin/telemetry').then(v => set('tel', v)).catch(setErr)
  }, [])
  const tabs = [['integrations', 'Integrations'], ['data', 'Data freshness & quality'], ['actions', 'Action tracker'], ...(can('telemetry_view') ? [['telemetry', 'LLM & tool telemetry']] : [])]
  return <div className="page gap"><div><h1>Operations</h1><div className="muted">Connectors, data health, action tracking and observability.</div></div><ErrorBox e={err} />
    <div className="tabs">{tabs.map(([k, n]) => <button key={k} className={'tab ' + (tab === k ? 'on' : '')} onClick={() => setTab(k)}>{n}</button>)}</div>
    {tab === 'integrations' && d.int && <div className="gap"><div className="grid g2">{d.int.connectors.map(c => <div key={c.id} className="card"><div className="row between"><h3>{c.name}</h3><Pill kind={/active|configured/.test(c.status) ? 'ok' : 'medium'}>{c.status}</Pill></div><div className="small muted">{c.detail}</div></div>)}</div>
      {can('integrations') && <div className="row"><button className="btn" onClick={async () => setTest(await api('/integrations/test-connection', { method: 'POST' }))}>Test data connection</button>{test && <Pill kind={test.ok ? 'ok' : 'high'}>{test.ok ? `OK · ${test.rows_in_fact_sales.toLocaleString()} rows · ${test.dialect}` : test.error}</Pill>}</div>}</div>}
    {tab === 'data' && <div className="gap">{d.fresh && <div className="card"><h3>Source freshness</h3><div className="small muted">Data through {d.fresh.data_through}</div><Table rows={d.fresh.sources.map(s => ({ source: s.source, system: s.system, refreshed: s.last_refreshed, age_hours: s.age_hours, cadence_hours: s.cadence_hours, status: s.stale ? 'STALE' : 'fresh' }))} /></div>}
      {d.dq && <div className="card"><div className="row between"><h3>Data-quality checks</h3><button className="btn sm" onClick={() => api('/data/quality?refresh=true').then(v => set('dq', v))}>Re-run checks</button></div><Table rows={d.dq.checks.map(c => ({ check: c.check_name, severity: c.severity, status: c.status, detail: c.detail, weeks: c.week_from ? `${String(c.week_from).slice(0, 10)} → ${String(c.week_to).slice(0, 10)}` : '' }))} /></div>}</div>}
    {tab === 'actions' && <div className="card"><h3>Actions across investigations</h3><table><thead><tr><th>Action</th><th>Investigation</th><th>Owner</th><th>Due</th><th>Status</th></tr></thead><tbody>{d.actions?.map(a => <tr key={a.id}><td>{a.title}</td><td><a href="#" onClick={e => { e.preventDefault(); nav('/investigations/' + a.investigation_id) }}>{a.investigation_title}</a></td><td>{a.owner || '–'}</td><td>{a.due_date || '–'}</td><td><Pill kind={a.status === 'done' ? 'done' : 'medium'}>{a.status}</Pill></td></tr>)}</tbody></table>{!d.actions?.length && <div className="muted">No actions yet.</div>}</div>}
    {tab === 'telemetry' && d.tel && <div className="gap"><div className="grid g4">{[['LLM calls', d.tel.llm.total_calls], ['LLM failures', d.tel.llm.failures], ['Tokens (in/out)', `${d.tel.llm.prompt_tokens}/${d.tel.llm.completion_tokens}`], ['Tool calls', d.tel.tools.total_calls]].map(([n, v]) => <div key={n} className="card kpi"><div className="small muted">{n}</div><div className="v">{v}</div></div>)}</div>
      <div className="card"><h3>By tool</h3><Table rows={d.tel.tools.by_tool} /></div><div className="card"><h3>By LLM model / purpose</h3><Table rows={[...d.tel.llm.by_model, ...d.tel.llm.by_purpose]} /></div>
      {[...d.tel.llm.recent_errors, ...d.tel.tools.recent_errors].length > 0 && <div className="card"><h3>Recent errors</h3><Table rows={[...d.tel.llm.recent_errors, ...d.tel.tools.recent_errors]} cols={['ts', 'request_id', 'model', 'tool', 'status', 'error']} /></div>}</div>}
  </div>
}
