import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useNavigate } from 'react-router-dom'
import { Archive, Download, Pencil, Plus, Search, Send, Trash2, ArchiveRestore, ExternalLink, AlertTriangle, Cpu, X } from 'lucide-react'
import { api, download } from '../api'
import { useAuth } from '../auth'
import { Chart, ErrorBox, EvidenceDrawer, Md, Modal, Pill, Spinner, Table, Trust } from '../ui'

function Evidence({ b, onOpen }) {
  const [open, setOpen] = useState(false)
  return <div className="evcard"><div className="row between wrap"><div className="small"><button className="cite" onClick={() => onOpen(b.label)}>{b.label}</button> <b>{b.tool}</b> <span className="muted">{b.runtime_ms}ms</span></div>
    <div className="row"><button className="btn sm" onClick={() => setOpen(!open)}>{open ? 'Hide' : 'Show'} chart & data</button><button className="btn sm" onClick={() => onOpen(b.label)}>Evidence</button></div></div>
    <div className="small" style={{ margin: '4px 0' }}>{b.headline}</div><Trust freshness={b.freshness} dq={b.data_quality} policy={b.policy} warnings={b.warnings} />
    {open && <div style={{ marginTop: 8 }}><Chart chart={b.chart} height={220} /><Table rows={b.rows} max={10} />{b.limitations.map((l, i) => <div key={i} className="small muted">• {l}</div>)}</div>}</div>
}

function Message({ m, convId, onAsk, onOpen }) {
  const nav = useNavigate(); const p = m.payload
  if (m.role === 'user') return <div className="bubble user">{m.content}</div>
  return <div className="bubble bot card flat">
    <Md text={m.content} onCite={onOpen} />
    {p?.clarification && <div className="chips" style={{ marginTop: 8 }}>{p.clarification.options.map(o => <button key={o} className="chip" onClick={() => onAsk(o)}>{o}</button>)}</div>}
    {p?.investigation && <div className="evcard" style={{ borderLeftColor: 'var(--amber)' }}><div className="row between wrap"><b>Investigation</b><Pill kind={p.investigation.confidence.level}>confidence {p.investigation.confidence.level} · {p.investigation.confidence.score}</Pill></div>
      <div className="small" style={{ margin: '4px 0' }}>{p.investigation.title}</div>
      <div className="row wrap" style={{ gap: 6 }}>{p.investigation.hypotheses.map(h => <Pill key={h.key} kind={h.status}>{h.key} · {h.status}{h.explained_pct ? ` · ${h.explained_pct}%` : ''}</Pill>)}</div>
      <button className="btn pri sm" style={{ marginTop: 8 }} onClick={() => nav('/investigations/' + p.investigation.id)}><ExternalLink size={12} />Open full investigation</button></div>}
    {p?.evidence?.map(b => <Evidence key={b.label} b={b} onOpen={onOpen} />)}
    {p?.grounding?.unverified?.length > 0 && <div className="notice warn small" style={{ marginTop: 8 }}><AlertTriangle size={12} /> Numbers not found in tool evidence: {p.grounding.unverified.join(', ')} — verify before relying on them.</div>}
    {p && <div className="row small muted wrap" style={{ marginTop: 8, gap: 8 }}><Cpu size={12} />{p.mode}{p.grounding && ` · ${p.grounding.checked} numbers checked`}{p.tools?.length > 0 && ` · tools: ${p.tools.map(t => t.name).join(', ')}`}{p.request_id && ` · ref ${p.request_id}`}</div>}
    {p?.suggestions?.length > 0 && <div className="chips" style={{ marginTop: 8 }}>{p.suggestions.map(s => <button key={s} className="chip" onClick={() => onAsk(s)}>{s}</button>)}</div>}
  </div>
}

export default function Chat() {
  const { can } = useAuth(); const [convs, setConvs] = useState([]); const [q, setQ] = useState(''); const [arch, setArch] = useState(false)
  const [branch, setBranch] = useState(null)
  const [searchOpen, setSearchOpen] = useState(false)
  const [cid, setCid] = useState(null); const [msgs, setMsgs] = useState([]); const [text, setText] = useState(''); const [busy, setBusy] = useState(false); const [err, setErr] = useState(null)
  const [ev, setEv] = useState(null); const [sugg, setSugg] = useState([]); const [modal, setModal] = useState(null); const end = useRef(); const searchInput = useRef()
  const load = () => api(`/conversations?archived=${arch}&q=${encodeURIComponent(q)}`).then(setConvs).catch(setErr)
  useEffect(() => { setBranch(document.getElementById('chat-branch-host')) }, [])
  useEffect(() => { if (searchOpen) searchInput.current?.focus() }, [searchOpen])
  useEffect(() => { load() }, [q, arch])
  useEffect(() => { api('/suggestions').then(r => setSugg(r.suggestions)).catch(() => {}) }, [])
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs, busy])
  const open = async id => { setCid(id); setErr(null); const r = await api('/conversations/' + id); setMsgs(r.messages) }
  const send = async (t) => {
    const msg = (t ?? text).trim(); if (!msg || busy) return
    setText(''); setErr(null); setBusy(true); setMsgs(m => [...m, { id: 'tmp', role: 'user', content: msg }])
    try { const r = await api('/chat', { method: 'POST', body: { message: msg, conversation_id: cid } }); setCid(r.conversation.id); setMsgs(m => [...m.filter(x => x.id !== 'tmp'), r.user_message, r.assistant_message]); load() }
    catch (e) { setErr(e); setMsgs(m => m.filter(x => x.id !== 'tmp')) } finally { setBusy(false) }
  }
  const newChat = () => { setCid(null); setMsgs([]); setErr(null) }
  const act = async () => {
    const { kind, c, val } = modal
    if (kind === 'rename') await api('/conversations/' + c.id, { method: 'PATCH', body: { title: val } })
    if (kind === 'delete') { await api('/conversations/' + c.id, { method: 'DELETE' }); if (cid === c.id) newChat() }
    setModal(null); load()
  }
  return <>
    <div className="chat">
      <div className="thread">
        <div className="msgs">
          {msgs.length === 0 && <div className="gap" style={{ margin: 'auto', maxWidth: 720 }}><div><h1>Ask about your business</h1><div className="muted">Every number comes from governed analytics tools and is traceable to evidence. Ask a question, or start with one of these:</div></div>
            <div className="chips">{sugg.map(s => <button key={s} className="chip" onClick={() => send(s)}>{s}</button>)}</div></div>}
          {msgs.map(m => <Message key={m.id} m={m} convId={cid} onAsk={send} onOpen={l => setEv(l)} />)}
          {busy && <Spinner text="Interpreting, running governed tools, checking evidence…" />}<ErrorBox e={err} /><div ref={end} />
        </div>
        <div className="composer"><input placeholder="e.g. Why did revenue drop in South last month?" value={text} onChange={e => setText(e.target.value)} onKeyDown={e => e.key === 'Enter' && send()} disabled={busy} />
          <button className="btn pri" onClick={() => send()} disabled={busy}><Send size={14} />Send</button>
          {cid && can('export') && <button className="btn" title="Export conversation" onClick={() => download(`/conversations/${cid}/export?format=md`, 'conversation.md')}><Download size={14} /></button>}</div>
      </div>
    </div>
    {branch && createPortal(<div className="chat-branch">
      <div className="branch-title">CONVERSATIONS</div>
      <button className="btn pri branch-new" onClick={newChat}><Plus size={14} />New conversation</button>
      <div className={'branch-tools' + (searchOpen ? ' search-open' : '')}>
        <div className={'branch-search' + (searchOpen ? ' open' : '')}>
          <button className="branch-search-toggle" type="button" aria-label="Search conversations" aria-expanded={searchOpen} title="Search conversations" onClick={() => setSearchOpen(true)}><Search size={15} /></button>
          {searchOpen && <><input ref={searchInput} id="branch-history-search" placeholder="Search history" value={q} onChange={e => setQ(e.target.value)} />
            <button className="branch-search-close" type="button" aria-label="Close search" title="Close search" onClick={() => { setQ(''); setSearchOpen(false) }}><X size={14} /></button></>}
        </div>
        <div className="branch-filters"><button className={'branch-filter' + (!arch ? ' on' : '')} onClick={() => setArch(false)}>Active</button><button className={'branch-filter' + (arch ? ' on' : '')} onClick={() => setArch(true)}>Archived</button></div>
      </div>
      <div className="branch-list">
      {convs.map(c => <div key={c.id} className={'conv' + (c.id === cid ? ' on' : '')} onClick={() => open(c.id)}><span title={c.title}>{c.title}</span>
        <span className="row" style={{ gap: 2 }} onClick={e => e.stopPropagation()}>
          <button className="btn sm" title="Rename" onClick={() => setModal({ kind: 'rename', c, val: c.title })}><Pencil size={11} /></button>
          <button className="btn sm" title={arch ? 'Restore' : 'Archive'} onClick={async () => { await api('/conversations/' + c.id, { method: 'PATCH', body: { archived: !arch } }); load() }}>{arch ? <ArchiveRestore size={11} /> : <Archive size={11} />}</button>
          <button className="btn sm danger" title="Delete" onClick={() => setModal({ kind: 'delete', c })}><Trash2 size={11} /></button></span></div>)}
      {convs.length === 0 && <div className="muted small branch-empty">No conversations.</div>}
      </div>
    </div>, branch)}
    {ev && cid && <EvidenceDrawer ownerType="conversation" ownerId={cid} label={ev} onClose={() => setEv(null)} />}
    {modal && <Modal title={modal.kind === 'rename' ? 'Rename conversation' : 'Delete conversation?'} onClose={() => setModal(null)} actions={<button className={'btn ' + (modal.kind === 'delete' ? 'danger' : 'pri')} onClick={act}>{modal.kind === 'delete' ? 'Delete permanently' : 'Save'}</button>}>
      {modal.kind === 'rename' ? <input value={modal.val} onChange={e => setModal({ ...modal, val: e.target.value })} autoFocus /> : <div>This permanently removes the messages, saved evidence and any investigations created from this conversation. This cannot be undone.</div>}</Modal>}
  </>
}
