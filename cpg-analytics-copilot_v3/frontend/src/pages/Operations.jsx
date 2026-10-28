import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { adminApi, api } from '../api'
import { useAuth } from '../auth'
import { ErrorBox, Pill, Table } from '../ui'

export default function Operations() {
  const { can } = useAuth(); const nav = useNavigate(); const [tab, setTab] = useState('integrations'); const [d, setD] = useState({}); const [err, setErr] = useState(null); const [test, setTest] = useState(null)
  const [adminTable, setAdminTable] = useState('knowledge_documents'); const [adminData, setAdminData] = useState(null); const [adminSearch, setAdminSearch] = useState(''); const [conversationFilter, setConversationFilter] = useState('')
  const [adminDatabase, setAdminDatabase] = useState('state'); const [analyticsInfo, setAnalyticsInfo] = useState(null); const [analyticsTable, setAnalyticsTable] = useState(''); const [analyticsSchema, setAnalyticsSchema] = useState(''); const [analyticsSearch, setAnalyticsSearch] = useState(''); const [analyticsData, setAnalyticsData] = useState(null)
  const set = (k, v) => setD(x => ({ ...x, [k]: v }))
  const loadAdmin = async (page = 1) => {
    const params = new URLSearchParams({ page: String(page), page_size: '20' })
    if (adminTable === 'knowledge_documents' && adminSearch.trim()) params.set('search', adminSearch.trim())
    if (adminTable !== 'knowledge_documents' && conversationFilter.trim()) params.set('conversation_id', conversationFilter.trim())
    try { setAdminData(await adminApi(`/admin/data/${adminTable}?${params}`)); setErr(null) } catch (e) { setErr(e) }
  }
  const loadAnalyticsData = async (table = analyticsTable, schema = analyticsSchema, page = 1) => {
    if (!table) return
    const params = new URLSearchParams({ table, page: String(page), page_size: '20' })
    if (schema) params.set('schema', schema)
    if (analyticsSearch.trim()) params.set('search', analyticsSearch.trim())
    try { setAnalyticsData(await adminApi(`/admin/analytics/data?${params}`)); setErr(null) } catch (e) { setErr(e) }
  }
  const loadAnalyticsTables = async () => {
    try {
      const inventory = await adminApi('/admin/analytics/tables')
      setAnalyticsInfo(inventory)
      if (inventory.tables?.length) {
        const first = inventory.tables.find(item => item.name === 'fact_sales') || inventory.tables[0]
        setAnalyticsTable(first.name); setAnalyticsSchema(first.schema || '')
        await loadAnalyticsData(first.name, first.schema || '', 1)
      } else setAnalyticsData(null)
      setErr(null)
    } catch (e) { setErr(e) }
  }
  useEffect(() => {
    api('/integrations').then(v => set('int', v)).catch(setErr); api('/data/freshness').then(v => set('fresh', v)).catch(setErr); api('/data/quality').then(v => set('dq', v)).catch(setErr); api('/actions').then(v => set('actions', v)).catch(setErr)
    if (can('telemetry_view')) api('/admin/telemetry').then(v => set('tel', v)).catch(setErr)
  }, [])
  const tabs = [['integrations', 'Integrations'], ['data', 'Data freshness & quality'], ['actions', 'Action tracker'], ...(can('telemetry_view') ? [['telemetry', 'LLM & tool telemetry']] : []), ...(can('user_admin') ? [['database', 'Database records']] : [])]
  return <div className="page gap"><div><h1>Operations</h1><div className="muted">Connectors, data health, action tracking and observability.</div></div><ErrorBox e={err} />
    <div className="tabs">{tabs.map(([k, n]) => <button key={k} className={'tab ' + (tab === k ? 'on' : '')} onClick={() => { setTab(k); if (k === 'database') loadAdmin(1) }}>{n}</button>)}</div>
    {tab === 'integrations' && d.int && <div className="gap"><div className="grid g2">{d.int.connectors.map(c => <div key={c.id} className="card"><div className="row between"><h3>{c.name}</h3><Pill kind={/active|configured/.test(c.status) ? 'ok' : 'medium'}>{c.status}</Pill></div><div className="small muted">{c.detail}</div></div>)}</div>
      {can('integrations') && <div className="row"><button className="btn" onClick={async () => setTest(await api('/integrations/test-connection', { method: 'POST' }))}>Test data connection</button>{test && <Pill kind={test.ok ? 'ok' : 'high'}>{test.ok ? `OK · ${test.rows_in_fact_sales.toLocaleString()} rows · ${test.dialect}` : test.error}</Pill>}</div>}</div>}
    {tab === 'data' && <div className="gap">{d.fresh && <div className="card"><h3>Source freshness</h3><div className="small muted">Data through {d.fresh.data_through}</div><Table rows={d.fresh.sources.map(s => ({ source: s.source, system: s.system, refreshed: s.last_refreshed, age_hours: s.age_hours, cadence_hours: s.cadence_hours, status: s.stale ? 'STALE' : 'fresh' }))} /></div>}
      {d.dq && <div className="card"><div className="row between"><h3>Data-quality checks</h3><button className="btn sm" onClick={() => api('/data/quality?refresh=true').then(v => set('dq', v))}>Re-run checks</button></div><Table rows={d.dq.checks.map(c => ({ check: c.check_name, severity: c.severity, status: c.status, detail: c.detail, weeks: c.week_from ? `${String(c.week_from).slice(0, 10)} → ${String(c.week_to).slice(0, 10)}` : '' }))} /></div>}</div>}
    {tab === 'actions' && <div className="card"><h3>Actions across investigations</h3><table><thead><tr><th>Action</th><th>Investigation</th><th>Owner</th><th>Due</th><th>Status</th></tr></thead><tbody>{d.actions?.map(a => <tr key={a.id}><td>{a.title}</td><td><a href="#" onClick={e => { e.preventDefault(); nav('/investigations/' + a.investigation_id) }}>{a.investigation_title}</a></td><td>{a.owner || '–'}</td><td>{a.due_date || '–'}</td><td><Pill kind={a.status === 'done' ? 'done' : 'medium'}>{a.status}</Pill></td></tr>)}</tbody></table>{!d.actions?.length && <div className="muted">No actions yet.</div>}</div>}
    {tab === 'telemetry' && d.tel && <div className="gap"><div className="grid g4">{[['LLM calls', d.tel.llm.total_calls], ['LLM failures', d.tel.llm.failures], ['Tokens (in/out)', `${d.tel.llm.prompt_tokens}/${d.tel.llm.completion_tokens}`], ['Tool calls', d.tel.tools.total_calls]].map(([n, v]) => <div key={n} className="card kpi"><div className="small muted">{n}</div><div className="v">{v}</div></div>)}</div>
      <div className="card"><h3>By tool</h3><Table rows={d.tel.tools.by_tool} /></div><div className="card"><h3>By LLM model / purpose</h3><Table rows={[...d.tel.llm.by_model, ...d.tel.llm.by_purpose]} /></div>
      {[...d.tel.llm.recent_errors, ...d.tel.tools.recent_errors].length > 0 && <div className="card"><h3>Recent errors</h3><Table rows={[...d.tel.llm.recent_errors, ...d.tel.tools.recent_errors]} cols={['ts', 'request_id', 'model', 'tool', 'status', 'error']} /></div>}</div>}
    {tab === 'database' && can('user_admin') && <div className="card gap"><div><h3>Database records</h3><div className="small muted">Admin-only read-only access to application records and the CPG analytics database.</div></div>
      <div className="row wrap"><select value={adminDatabase} onChange={e => { const value = e.target.value; setAdminDatabase(value); if (value === 'analytics') { setAnalyticsData(null); loadAnalyticsTables() } else { setAdminData(null); loadAdmin(1) } }}><option value="state">Application database</option><option value="analytics">CPG analytics database (cpg.db)</option></select></div>
      {adminDatabase === 'state' && <><div className="row wrap"><select value={adminTable} onChange={e => { setAdminTable(e.target.value); setAdminData(null) }}><option value="knowledge_documents">Knowledge documents</option><option value="chat_logs">Chat logs</option><option value="evaluation_results">Evaluation results</option></select>
        {adminTable === 'knowledge_documents' ? <input placeholder="Search titles and document content" value={adminSearch} onChange={e => setAdminSearch(e.target.value)} onKeyDown={e => e.key === 'Enter' && loadAdmin(1)} /> : <input placeholder="Filter by conversation ID (optional)" value={conversationFilter} onChange={e => setConversationFilter(e.target.value)} onKeyDown={e => e.key === 'Enter' && loadAdmin(1)} />}
        <button className="btn pri" onClick={() => loadAdmin(1)}>Load records</button></div>
      {adminData && <><div className="small muted">{adminData.total.toLocaleString()} records · page {adminData.page}</div>
        {adminData.items.map((row, index) => <details className="admin-record" key={row.id || index}><summary>{row.title || row.content?.slice(0, 180) || row.message_id || row.id || `Record ${index + 1}`}</summary><pre>{JSON.stringify(row, null, 2)}</pre></details>)}
        {!adminData.items.length && <div className="muted small">No matching records.</div>}
        <div className="row between"><button className="btn" disabled={adminData.page <= 1} onClick={() => loadAdmin(adminData.page - 1)}>Previous</button><button className="btn" disabled={adminData.page * adminData.page_size >= adminData.total} onClick={() => loadAdmin(adminData.page + 1)}>Next</button></div>
      </>}</>}
      {adminDatabase === 'analytics' && <><div className="row wrap"><select value={JSON.stringify([analyticsSchema, analyticsTable])} onChange={e => { const [schema, name] = JSON.parse(e.target.value); setAnalyticsSchema(schema); setAnalyticsTable(name); setAnalyticsData(null) }}>{analyticsInfo?.tables?.map(item => <option key={`${item.schema || ''}:${item.name}`} value={JSON.stringify([item.schema || '', item.name])}>{item.schema ? `${item.schema}.` : ''}{item.name} ({item.kind})</option>)}</select>
        <input placeholder="Search text columns in this table" value={analyticsSearch} onChange={e => setAnalyticsSearch(e.target.value)} onKeyDown={e => e.key === 'Enter' && loadAnalyticsData(analyticsTable, analyticsSchema, 1)} />
        <button className="btn pri" disabled={!analyticsTable} onClick={() => loadAnalyticsData(analyticsTable, analyticsSchema, 1)}>Load records</button></div>
        {analyticsInfo && <div className="small muted">Database: {analyticsInfo.database} · engine: {analyticsInfo.dialect} · {analyticsInfo.tables?.length || 0} tables and views</div>}
        {analyticsData && <><div className="small muted">{analyticsData.total.toLocaleString()} rows · page {analyticsData.page} · columns: {analyticsData.columns.join(', ')}</div><Table rows={analyticsData.items} max={20} />
          {analyticsData.items.map((row, index) => <details className="admin-record" key={index}><summary>Row {((analyticsData.page - 1) * analyticsData.page_size) + index + 1} · {Object.values(row).slice(0, 3).map(value => String(value ?? '')).join(' · ').slice(0, 160)}</summary><pre>{JSON.stringify(row, null, 2)}</pre></details>)}
          {!analyticsData.items.length && <div className="muted small">No matching rows.</div>}
          <div className="row between"><button className="btn" disabled={analyticsData.page <= 1} onClick={() => loadAnalyticsData(analyticsTable, analyticsSchema, analyticsData.page - 1)}>Previous</button><button className="btn" disabled={analyticsData.page * analyticsData.page_size >= analyticsData.total} onClick={() => loadAnalyticsData(analyticsTable, analyticsSchema, analyticsData.page + 1)}>Next</button></div>
        </>}
      </>}
    </div>}
  </div>
}
