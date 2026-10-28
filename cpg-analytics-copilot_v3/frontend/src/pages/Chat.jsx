import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useNavigate } from 'react-router-dom'
import { Archive, Download, Pencil, Plus, Search, Send, Trash2, ArchiveRestore, ExternalLink, AlertTriangle, Cpu, X, Paperclip, FileText } from 'lucide-react'
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
    {p?.document_chat && <div className="evcard document-answer">
      <div className="row between wrap"><b>{p.compare_database ? 'Source comparison report' : 'Document references'}</b><span className="small muted">{p.latency_ms} ms</span></div>
      <div className="small muted" style={{ marginTop: 4 }}>Source choice: {p.source_selection?.reason}</div>
      {p.documents?.map(d => <div id={`doc-${d.id}`} className="document-reference" key={d.id}><FileText size={13} /><div><b>{d.title}</b><div className="small muted">[DocID:{d.id}] · {d.source || 'shared document'} · updated {d.updated_at || 'date unavailable'}</div></div></div>)}
      {p.source_selection?.candidates?.length > 0 && <div className="small muted" style={{ marginTop: 6 }}>Selected source: {p.source_selection.selected?.source === 'database' ? `CPG data ${p.source_selection.selected.label || ''}` : p.source_selection.selected?.document_id ? `Document ${p.source_selection.selected.document_id}` : 'not ranked'} | ranking confidence {p.source_selection.candidates.find(c => c.document_id === p.source_selection.selected?.document_id || c.label === p.source_selection.selected?.label)?.confidence ?? 'n/a'}</div>}
    </div>}
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
  const [docs, setDocs] = useState([]); const [libraryDocs, setLibraryDocs] = useState([]); const [selectedDocs, setSelectedDocs] = useState([]); const [docBusy, setDocBusy] = useState(false); const [docPanelOpen, setDocPanelOpen] = useState(false); const [activeTab, setActiveTab] = useState('chat'); const [libraryQuery, setLibraryQuery] = useState(''); const [libraryBusy, setLibraryBusy] = useState(false); const [docPreview, setDocPreview] = useState(null); const fileInput = useRef(null); const attachmentRef = useRef(null)
  const [ev, setEv] = useState(null); const [sugg, setSugg] = useState([]); const [modal, setModal] = useState(null); const end = useRef(); const searchInput = useRef()
  const load = () => api(`/conversations?archived=${arch}&q=${encodeURIComponent(q)}`).then(setConvs).catch(setErr)
  useEffect(() => { setBranch(document.getElementById('chat-branch-host')) }, [])
  useEffect(() => { if (searchOpen) searchInput.current?.focus() }, [searchOpen])
  useEffect(() => { load() }, [q, arch])
  useEffect(() => { api('/suggestions').then(r => setSugg(r.suggestions)).catch(() => {}) }, [])
  useEffect(() => {
    const closeMenu = event => { if (!attachmentRef.current?.contains(event.target)) setDocPanelOpen(false) }
    document.addEventListener('mousedown', closeMenu)
    return () => document.removeEventListener('mousedown', closeMenu)
  }, [])
  useEffect(() => {
    if (activeTab !== 'library') return
    setLibraryBusy(true)
    api(`/documents?search=${encodeURIComponent(libraryQuery)}`).then(r => {
      const uploads = (r.items || []).filter(item => item.source === 'upload')
      setLibraryDocs(uploads)
    }).catch(setErr).finally(() => setLibraryBusy(false))
  }, [activeTab, libraryQuery])
  useEffect(() => () => { if (docPreview?.url) URL.revokeObjectURL(docPreview.url) }, [docPreview])
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs, busy])
  const open = async id => { setCid(id); setErr(null); const r = await api('/conversations/' + id); setMsgs(r.messages) }
  const send = async (t) => {
    const msg = (t ?? text).trim(); if (!msg || busy) return
    setText(''); setErr(null); setBusy(true); setMsgs(m => [...m, { id: 'tmp', role: 'user', content: msg }])
    try {
      const r = await api('/chat', { method: 'POST', body: { message: msg, conversation_id: cid, document_ids: selectedDocs, compare_database: selectedDocs.length > 0 } }); setCid(r.conversation.id); setMsgs(m => [...m.filter(x => x.id !== 'tmp'), r.user_message, r.assistant_message]); load()
    }
    catch (e) { setErr(e); setMsgs(m => m.filter(x => x.id !== 'tmp')) } finally { setBusy(false) }
  }
  const uploadPdf = async file => {
    if (!file) return
    setDocBusy(true); setErr(null)
    try { const data = new FormData(); data.append('file', file); const uploaded = await api('/documents/upload', { method: 'POST', body: data }); setDocs(items => [...items.filter(item => item.id !== uploaded.id), uploaded]); setSelectedDocs(ids => [...new Set([...ids, uploaded.id])]); setDocPanelOpen(false) }
    catch (e) { setErr(e) } finally { setDocBusy(false); if (fileInput.current) fileInput.current.value = '' }
  }
  const viewLibraryDocument = async doc => {
    try {
      const response = await api(`/documents/${encodeURIComponent(doc.id)}/file`, { raw: true })
      setDocPreview({ doc, url: URL.createObjectURL(await response.blob()), content: null })
    } catch {
      try { setDocPreview({ doc, url: null, content: (await api(`/documents/${encodeURIComponent(doc.id)}`)).content }) }
      catch (e) { setErr(e) }
    }
  }
  const closePreview = () => { if (docPreview?.url) URL.revokeObjectURL(docPreview.url); setDocPreview(null) }
  const attachLibraryDocument = doc => {
    setDocs(items => [...items.filter(item => item.id !== doc.id), doc])
    setSelectedDocs(ids => [...new Set([...ids, doc.id])])
    setActiveTab('chat')
  }
  const newChat = () => { setCid(null); setMsgs([]); setErr(null) }
  const act = async () => {
    const { kind, c, val } = modal
    if (kind === 'rename') await api('/conversations/' + c.id, { method: 'PATCH', body: { title: val } })
    if (kind === 'delete') { await api('/conversations/' + c.id, { method: 'DELETE' }); if (cid === c.id) newChat() }
    setModal(null); load()
  }
  return <>
    <div className="chat-page">
      <div className="chat-view-tabs" role="tablist" aria-label="Chat and document library">
        <button role="tab" aria-selected={activeTab === 'chat'} className={activeTab === 'chat' ? 'active' : ''} onClick={() => setActiveTab('chat')}>Chat</button>
        <button role="tab" aria-selected={activeTab === 'library'} className={activeTab === 'library' ? 'active' : ''} onClick={() => setActiveTab('library')}>Library</button>
      </div>
      {activeTab === 'library' ? <section className="library-view">
        <div className="row between wrap"><div><h1>Document library</h1><div className="muted">Uploaded PDFs are stored here and available to signed-in users.</div></div><button className="btn pri" onClick={() => { setActiveTab('chat'); setDocPanelOpen(true) }}><Paperclip size={14} />Upload a PDF</button></div>
        <div className="row library-search"><Search size={16} className="muted" /><input aria-label="Search uploaded documents" placeholder="Search uploaded documents" value={libraryQuery} onChange={e => setLibraryQuery(e.target.value)} /></div>
        <ErrorBox e={err} />
        {libraryBusy ? <Spinner text="Loading documents…" /> : <div className="library-grid">{libraryDocs.map(doc => <article className="card library-card" key={doc.id}>
          <div className="row library-file-icon"><FileText size={20} /></div><div className="library-title" title={doc.title}>{doc.title}</div><div className="small muted">PDF · uploaded {doc.updated_at || 'date unavailable'}</div>
          <div className="row wrap"><button className="btn sm" onClick={() => viewLibraryDocument(doc)}>View document</button><button className="btn sm pri" onClick={() => attachLibraryDocument(doc)}>Use in chat</button></div>
        </article>)}</div>}
        {!libraryBusy && libraryDocs.length === 0 && <div className="library-empty"><FileText size={24} /><b>No uploaded documents yet</b><span>Upload a PDF from chat and it will appear here.</span><button className="btn" onClick={() => { setActiveTab('chat'); setDocPanelOpen(true) }}>Go to upload</button></div>}
      </section> : <div className="chat">
      <div className="thread">
        <div className="msgs">
          {msgs.length === 0 && <div className="gap chat-welcome" style={{ margin: 'auto', maxWidth: 760 }}><div><h1>Ask about your business</h1><div className="muted">Ask the CPG data or attach a document for a cited comparison report.</div></div>
            <div className="question-group"><b>CPG data</b><div className="chips">{['Compare South beverage revenue with the prior period.', 'Which region had the highest net revenue last month?'].map(s => <button key={s} className="chip" onClick={() => send(s)}>{s}</button>)}</div></div>
            <div className="question-group"><b>Documents and automatic CPG comparison</b><div className="chips">{['What were North campaign net revenue and gross margin?', 'Which featured product sold the most units, and how many?', 'What action was assigned to Field sales and by when?', 'Compare the report’s North revenue with CPG data. Explain the values and date coverage.'].map((s, i) => <button key={s} className="chip" onClick={() => { setDocPanelOpen(i === 3 || i === 0); setText(s) }}>{s}</button>)}</div></div>
            <div className="small muted">Attach a document to ask about it or compare it with CPG data.</div></div>}
          {msgs.map(m => <Message key={m.id} m={m} convId={cid} onAsk={send} onOpen={l => setEv(l)} />)}
          {busy && <Spinner text="Interpreting, running governed tools, checking evidence…" />}<ErrorBox e={err} /><div ref={end} />
        </div>
        <div className="composer">
          {selectedDocs.length > 0 && <div className="row wrap selected-docs">{selectedDocs.map(id => { const d = docs.find(item => item.id === id); return d && <span className="selected-doc" key={id}><FileText size={12} />{d.title}<button aria-label={`Remove ${d.title}`} onClick={() => setSelectedDocs(ids => ids.filter(item => item !== id))}>×</button></span> })}<span className="compare-report-note">CPG comparison included in report</span></div>}
          <div className="row composer-entry">
          <div className="attachment-wrap" ref={attachmentRef}><button className="btn attachment-trigger" type="button" title="Attach files" aria-label="Attach files" aria-expanded={docPanelOpen} onClick={() => setDocPanelOpen(value => !value)} disabled={docBusy}><Paperclip size={18} /></button>
            {docPanelOpen && <div className="attachment-menu"><b>Add to chat</b><button className="attachment-upload" onClick={() => fileInput.current?.click()} disabled={docBusy}><Paperclip size={15} />Upload a PDF</button><input ref={fileInput} type="file" accept="application/pdf,.pdf" hidden onChange={e => uploadPdf(e.target.files?.[0])} />
              {docBusy && <div className="small muted">Reading PDF…</div>}
            </div>}
          </div>
          <input placeholder="Ask a question…" value={text} onChange={e => setText(e.target.value)} onKeyDown={e => e.key === 'Enter' && send()} disabled={busy} />
          <button className="btn pri" onClick={() => send()} disabled={busy}><Send size={14} />Ask</button>
          {cid && can('export') && <button className="btn" title="Export conversation" onClick={() => download(`/conversations/${cid}/export?format=md`, 'conversation.md')}><Download size={14} /></button>}</div>
        </div>
      </div>
    </div>}
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
    {docPreview && <Modal title={docPreview.doc.title} onClose={closePreview}><div className="small muted">[DocID:{docPreview.doc.id}] · Uploaded {docPreview.doc.updated_at || 'date unavailable'}</div>{docPreview.url ? <iframe className="document-pdf-preview" title={`Preview of ${docPreview.doc.title}`} src={docPreview.url} /> : <pre className="document-preview">{docPreview.content}</pre>}</Modal>}
    {modal && <Modal title={modal.kind === 'rename' ? 'Rename conversation' : 'Delete conversation?'} onClose={() => setModal(null)} actions={<button className={'btn ' + (modal.kind === 'delete' ? 'danger' : 'pri')} onClick={act}>{modal.kind === 'delete' ? 'Delete permanently' : 'Save'}</button>}>
      {modal.kind === 'rename' ? <input value={modal.val} onChange={e => setModal({ ...modal, val: e.target.value })} autoFocus /> : <div>This permanently removes the messages, saved evidence and any investigations created from this conversation. This cannot be undone.</div>}</Modal>}
  </>
}
