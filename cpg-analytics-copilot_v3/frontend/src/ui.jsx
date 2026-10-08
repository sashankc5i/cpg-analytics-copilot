import { useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Bar, BarChart, CartesianGrid, Cell, ComposedChart, Legend, Line, LineChart, ReferenceDot, ResponsiveContainer, Tooltip, XAxis, YAxis, Area } from 'recharts'
import { X, Database, ShieldCheck, GitBranch, AlertTriangle } from 'lucide-react'
import { api } from './api'

const PAL = ['#57238b', '#94600d', '#5d45a5', '#ae344e', '#8e66b4', '#746a80']
export const fv = (unit, v) => {
  if (v === null || v === undefined || Number.isNaN(v)) return '–'
  const a = Math.abs(v), s = v < 0 ? '-' : ''
  const sc = x => (x >= 1e6 ? (x / 1e6).toFixed(2) + 'M' : x >= 1e4 ? (x / 1e3).toFixed(1) + 'K' : x >= 1e3 ? x.toLocaleString(undefined, { maximumFractionDigits: 0 }) : x.toFixed(x < 10 ? 2 : 0))
  if (unit === 'currency') return s + '$' + sc(a)
  if (unit === 'pct') return v.toFixed(1) + '%'
  if (unit === 'price') return '$' + v.toFixed(2)
  if (unit === 'ratio') return v.toFixed(2)
  return s + sc(a)
}
export const short = s => (String(s).length > 12 ? String(s).slice(0, 11) + '…' : s)
export const pctTxt = v => (v === null || v === undefined ? '–' : `${v > 0 ? '+' : ''}${v.toFixed(1)}%`)

export function Pill({ kind, children }) { return <span className={`pill ${kind || ''}`}>{children ?? kind}</span> }
export const Spinner = ({ text = 'Working…' }) => <div className="muted row small" style={{ padding: 12 }}><span className="pill info">●</span>{text}</div>
export const ErrorBox = ({ e }) => e ? <div className="notice err">{String(e.message || e)}</div> : null

export function Chart({ chart, height = 240 }) {
  if (!chart) return null
  const { type, unit, data = [], series = [], title } = chart
  const common = { data, margin: { top: 8, right: 12, bottom: 4, left: 0 } }
  const ax = <><CartesianGrid stroke="#eae3f0" vertical={false} /><XAxis dataKey={chart.x || 'name'} tickFormatter={short} tick={{ fontSize: 11 }} interval="preserveStartEnd" /><YAxis tickFormatter={v => fv(unit, v)} tick={{ fontSize: 11 }} width={58} domain={type === 'line' || type === 'timeline' ? ['auto', 'auto'] : [0, 'auto']} /></>
  const tip = <Tooltip formatter={(v, n) => [fv(unit, v), n]} />
  let body
  if (type === 'bar') body = (
    <BarChart {...common}>{ax}{tip}{series.length > 1 && <Legend wrapperStyle={{ fontSize: 12 }} />}
      {series.map((s, i) => <Bar key={s.key} dataKey={s.key} name={s.name} fill={PAL[(i + (series.length > 1 ? 5 - 4 : 0)) % PAL.length]} radius={[3, 3, 0, 0]}>
        {chart.signed && series.length === 1 && data.map((d, j) => <Cell key={j} fill={d[s.key] < 0 ? '#ae344e' : '#57238b'} />)}</Bar>)}
    </BarChart>)
  else if (type === 'waterfall') body = (
    <BarChart {...common}>{ax}<Tooltip formatter={(v, n) => [fv(unit, v), n]} />
      <Bar dataKey="base" stackId="a" fill="transparent" /><Bar dataKey="up" stackId="a" name="Increase / total" fill="#57238b">{data.map((d, i) => <Cell key={i} fill={d.kind === 'total' ? '#51455e' : '#247553'} />)}</Bar><Bar dataKey="down" stackId="a" name="Decrease" fill="#ae344e" />
    </BarChart>)
  else if (type === 'timeline') {
    const col = { promotion: '#5d45a5', stockout: '#ae344e', price: '#94600d', competitor: '#8e66b4' }
    const pts = (chart.events || []).map(e => ({ ...e, v: data.find(d => d.name === e.date)?.value })).filter(e => e.v !== undefined)
    body = <LineChart {...common}>{ax}{tip}<Line dataKey="value" name="KPI" stroke="#57238b" dot={false} strokeWidth={2} />{pts.map((e, i) => <ReferenceDot key={i} x={e.date} y={e.v} r={5} fill={col[e.kind] || '#333'} stroke="#fff" />)}</LineChart>
  } else {
    const d2 = chart.band ? data.map(d => ({ ...d, _band: d[chart.band.lo] != null ? [d[chart.band.lo], d[chart.band.hi]] : null })) : data
    body = <ComposedChart data={d2} margin={common.margin}>{ax}{tip}{series.length > 1 && <Legend wrapperStyle={{ fontSize: 12 }} />}
      {chart.band && <Area dataKey="_band" name={chart.band.label || 'Interval'} stroke="none" fill="#57238b" fillOpacity={0.15} />}
      {series.map((s, i) => <Line key={s.key} dataKey={s.key} name={s.name} stroke={PAL[i % PAL.length]} dot={false} strokeWidth={2} connectNulls />)}</ComposedChart>
  }
  return <div><div className="small muted" style={{ marginBottom: 2 }}>{title}</div><ResponsiveContainer width="100%" height={height}>{body}</ResponsiveContainer>
    {type === 'timeline' && <div className="row wrap small" style={{ gap: 10 }}>{Object.entries({ promotion: '#5d45a5', stockout: '#ae344e', price: '#94600d', competitor: '#8e66b4' }).map(([k, c]) => <span key={k}><span style={{ color: c }}>●</span> {k}</span>)}</div>}</div>
}

export function Table({ rows, cols, max = 50 }) {
  if (!rows?.length) return <div className="muted small">No rows.</div>
  const keys = cols || Object.keys(rows[0]).filter(k => typeof rows[0][k] !== 'object' || rows[0][k] === null)
  const f = (k, v) => v === null || v === undefined ? '–' : typeof v === 'number' ? (/pct|share|growth|rate|deviation|change|pp$/.test(k) ? v.toFixed(1) : Math.abs(v) >= 1000 ? v.toLocaleString(undefined, { maximumFractionDigits: 0 }) : v.toLocaleString(undefined, { maximumFractionDigits: 2 })) : Array.isArray(v) ? v.join(', ') : String(v)
  return <div className="tw"><table><thead><tr>{keys.map(k => <th key={k} className={typeof rows[0][k] === 'number' ? 'num' : ''}>{k.replace(/_/g, ' ')}</th>)}</tr></thead>
    <tbody>{rows.slice(0, max).map((r, i) => <tr key={i}>{keys.map(k => <td key={k} className={typeof r[k] === 'number' ? 'num' : ''}>{f(k, r[k])}</td>)}</tr>)}</tbody></table></div>
}

export function Md({ text, onCite }) {
  const t = (text || '').replace(/\[(E\d+)\]/g, '[$1](cite:$1)')
  return <div className="md"><ReactMarkdown remarkPlugins={[remarkGfm]} urlTransform={u => u}
    components={{ a: ({ href, children }) => href?.startsWith('cite:') ? <button className="cite" onClick={() => onCite?.(href.slice(5))}>{children}</button> : <a href={href} target="_blank" rel="noreferrer">{children}</a> }}>{t}</ReactMarkdown></div>
}

export function Trust({ freshness, dq = [], policy, warnings = [] }) {
  const stale = (freshness?.sources || []).filter(s => s.stale)
  return <div className="row wrap" style={{ gap: 6 }}>
    {freshness && <Pill kind={stale.length ? 'stale' : 'ok'}>{stale.length ? `stale: ${stale.map(s => s.table.replace('fact_', '')).join(', ')}` : 'fresh'} · data through {freshness.data_through}</Pill>}
    {dq.length > 0 && <Pill kind="medium"><AlertTriangle size={11} />{dq.length} data-quality note{dq.length > 1 ? 's' : ''}</Pill>}
    {policy?.row_level_security && <Pill kind="info"><ShieldCheck size={11} />scoped: {Object.entries(policy.scope).map(([k, v]) => `${k}=${v.join('/')}`).join(', ')}</Pill>}
    {warnings.length > 0 && <Pill kind="medium">{warnings.length} note(s)</Pill>}</div>
}

export function Modal({ title, children, onClose, actions }) {
  return <><div className="scrim" onClick={onClose} /><div className="modal"><h3>{title}</h3><div style={{ margin: '10px 0 16px' }}>{children}</div><div className="row" style={{ justifyContent: 'flex-end' }}>{actions}<button className="btn" onClick={onClose}>Cancel</button></div></div></>
}

export function EvidenceDrawer({ ownerType, ownerId, label, onClose }) {
  const [d, setD] = useState(null); const [err, setErr] = useState(null); const [tab, setTab] = useState('data')
  useEffect(() => { setD(null); setErr(null); api(`/evidence/${ownerType}/${ownerId}/${label}`).then(setD).catch(setErr) }, [ownerType, ownerId, label])
  const r = d?.result, m = r?.meta
  return <><div className="scrim" onClick={onClose} /><div className="drawer">
    <div className="row between" style={{ padding: '12px 16px', borderBottom: '1px solid var(--line)' }}><div><span className="tag">{label}</span> <b>{d?.tool}</b></div><button className="btn sm" onClick={onClose}><X size={14} /></button></div>
    <div className="body">{err && <ErrorBox e={err} />}{!d && !err && <Spinner />}
      {r && <div className="gap">
        <div><b>{r.headline}</b></div><Trust freshness={m?.freshness} dq={m?.data_quality} policy={m?.policy} warnings={m?.warnings} />
        {(r.limitations?.length > 0 || m?.warnings?.length > 0) && <div className="notice warn">{[...(r.limitations || []), ...(m?.warnings || [])].map((l, i) => <div key={i}>• {l}</div>)}</div>}
        <Chart chart={r.chart} />
        <div className="tabs" style={{ margin: 0 }}>{[['data', 'Data'], ['sql', 'SQL & parameters'], ['lineage', 'Lineage'], ['quality', 'Quality & policy']].map(([k, n]) => <button key={k} className={'tab ' + (tab === k ? 'on' : '')} onClick={() => setTab(k)}>{n}</button>)}</div>
        {tab === 'data' && <Table rows={r.rows} max={100} />}
        {tab === 'sql' && <div><div className="small muted"><Database size={12} /> Generated from the governed semantic layer — never by the LLM. {m?.runtime_ms}ms.</div>{m?.sql?.map((s, i) => <div key={i}><pre>{s.sql}</pre><pre>{JSON.stringify(s.params, null, 1)}</pre></div>)}<div className="small muted">Arguments</div><pre>{JSON.stringify(d.args, null, 1)}</pre></div>}
        {tab === 'lineage' && <div className="gap"><div className="small"><GitBranch size={12} /> Sources</div><Table rows={m?.lineage?.sources} /><div className="small">Transformations</div><ul>{m?.lineage?.transformations?.map((t, i) => <li key={i}>{t}</li>)}</ul><div className="small">Periods</div><Table rows={m?.periods} /></div>}
        {tab === 'quality' && <div className="gap"><div className="small">Data freshness</div><Table rows={m?.freshness?.sources} /><div className="small">Data-quality findings</div>{m?.data_quality?.length ? <Table rows={m.data_quality} /> : <div className="muted small">None overlapping this result.</div>}<div className="small">Access policy</div><pre>{JSON.stringify(m?.policy, null, 1)}</pre><div className="small">Effective filters</div><pre>{JSON.stringify(m?.filters, null, 1)}</pre></div>}
      </div>}</div></div></>
}

