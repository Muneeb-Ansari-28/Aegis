import { useCallback, useEffect, useState, type ReactNode } from 'react';
import { AlertTriangle, ArrowUpRight, Bot, Check, CircleHelp, Command, Globe2, History, LoaderCircle, Radio, Search, Settings2, Shield, ShieldAlert, ShieldCheck, SlidersHorizontal, Sparkles, Square, UserRound, X } from 'lucide-react';
import { api, assist, type ScanRecord, type ScanTurn, type Target } from './api/client';
import { useScanSocket, type ScanEvent } from './hooks/useScanSocket';
import Overview from './components/Overview';
import NewAssessment from './components/NewAssessment';
import ApplicationShell, { type AppPage as Page } from './components/ApplicationShell';
import FindingsInspector from './views/FindingsInspector';

import type { ChatMessage } from './types';
type LocalScan = ScanRecord & { targetName?: string; createdAt: string };
const HISTORY_KEY = 'aegis.scan-history';
const PROFILE_KEY = 'aegis.profile';
const OWASP = [
  ['LLM01', 'Prompt Injection'], ['LLM02', 'Sensitive Information Disclosure'], ['LLM03', 'Excessive Agency'], ['LLM04', 'Supply Chain'], ['LLM05', 'Data and Model Poisoning'], ['LLM06', 'Unbounded Consumption'], ['LLM07', 'Misinformation'], ['LLM08', 'Hidden Context Exposure'], ['LLM09', 'Vector and Embedding Weaknesses'], ['LLM10', 'Improper Output Handling'],
];

function readHistory(): LocalScan[] { try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]') as LocalScan[]; } catch { return []; } }
function errorText(e: unknown): string { return e instanceof Error ? e.message : 'Something went wrong. Check that the Aegis engine is running.'; }
function cx(...v: Array<string | false | null | undefined>): string { return v.filter(Boolean).join(' '); }
export default function App() {
  const [page, setPage] = useState<Page>('overview');
  const [engineOnline, setEngineOnline] = useState<boolean | null>(null);
  const [ollamaOnline, setOllamaOnline] = useState<boolean | null>(null);
  const [targets, setTargets] = useState<Target[]>([]);
  const [history, setHistory] = useState<LocalScan[]>(readHistory);
  const [activeScan, setActiveScan] = useState<ScanRecord | null>(null);
  const [selectedScanId, setSelectedScanId] = useState<string | null>(null);
  const [profileName, setProfileName] = useState(() => localStorage.getItem(PROFILE_KEY) || 'Security analyst');
  const [toast, setToast] = useState('');

  async function refresh() {
    try { const health = await api.health(); setEngineOnline(true); setOllamaOnline(Boolean(health.ollama_connected)); }
    catch { setEngineOnline(false); setOllamaOnline(false); }
    try { setTargets(await api.targets()); } catch { /* Engine status is shown separately. */ }
  }
  useEffect(() => { void refresh(); const id = window.setInterval(() => { void refresh(); }, 12000); return () => window.clearInterval(id); }, []);
  useEffect(() => { if (!toast) return; const id = window.setTimeout(() => setToast(''), 4200); return () => window.clearTimeout(id); }, [toast]);
  const onScanStarted = (scan: ScanRecord, target?: Target) => {
    setActiveScan(scan);
    setSelectedScanId(scan.scan_id);
    const next = [{ ...scan, targetName: target?.name, createdAt: new Date().toISOString() }, ...readHistory()].slice(0, 100);
    setHistory(next); localStorage.setItem(HISTORY_KEY, JSON.stringify(next));
    setPage('live'); setToast('Scan started. The target is open in the Playwright browser.');
  };
  const onScanStatus = useCallback((status: string) => {
    setActiveScan(current => current ? { ...current, status } : current);
    setHistory(current => {
      const updated = current.map(item => item.scan_id === activeScan?.scan_id ? { ...item, status } : item);
      localStorage.setItem(HISTORY_KEY, JSON.stringify(updated));
      return updated;
    });
  }, [activeScan?.scan_id]);

  const openResults = (scanId: string) => {
    setSelectedScanId(scanId);
    setPage('results');
  };

  return <><ApplicationShell page={page} onNavigate={setPage} hasActiveScan={Boolean(activeScan)}
    profileName={profileName} engineOnline={engineOnline} ollamaOnline={ollamaOnline} onRefresh={refresh}>
      {page === 'overview' && <Overview history={history} activeScan={activeScan} onNavigate={setPage} engineOnline={engineOnline} ollamaOnline={ollamaOnline} profileName={profileName} onRefresh={refresh} onSelectScan={openResults}/>}
      {page === 'scan' && <NewAssessment targets={targets} refresh={refresh} onStarted={onScanStarted} notify={setToast}/>}
      {page === 'live' && activeScan && <LiveScanPage scan={activeScan} targetName={history.find(item => item.scan_id === activeScan.scan_id)?.targetName || 'Local target'} onStatus={onScanStatus} onInspectResults={openResults}/>}
      {page === 'results' && <FindingsInspector scanId={selectedScanId || activeScan?.scan_id || history[0]?.scan_id} history={history} onSelectScan={setSelectedScanId} onNavigate={setPage}/>}
      {page === 'history' && <HistoryPage history={history} onRefresh={() => { const h = readHistory(); setHistory(h); }} onSelectScan={openResults}/>}
      {page === 'assistant' && <Assistant history={history}/>}
      {page === 'profile' && <Profile onSaveName={setProfileName}/>}
    </ApplicationShell>{toast && <div className="toast"><Check size={17}/>{toast}<button onClick={() => setToast('')}><X size={15}/></button></div>}
  </>;
}

function Heading({ eyebrow, title, sub, action }: { eyebrow: string; title: string; sub: string; action?: ReactNode }) { return <div className="page-heading"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{sub}</p></div>{action}</div>; }

function HistoryPage({history, onRefresh, onSelectScan}: {history: LocalScan[]; onRefresh: () => void; onSelectScan?: (scanId: string) => void}) {
  const [query, setQuery] = useState('');
  const filtered = history.filter(x => (x.targetName || '').toLowerCase().includes(query.toLowerCase()) || x.category.toLowerCase().includes(query.toLowerCase()));
  return <div className="page-content"><Heading eyebrow="ASSESSMENT RECORDS" title="Scan history" sub="Review scan requests started from this desktop workspace." action={<button className="button secondary" onClick={onRefresh}><Radio size={15}/>Refresh</button>}/><section className="panel history-panel"><div className="history-toolbar"><div className="history-count"><strong>{history.length}</strong> assessment{history.length===1?'':'s'}</div><div className="search-box"><Search size={15}/><input placeholder="Search target or category" value={query} onChange={e=>setQuery(e.target.value)}/><SlidersHorizontal size={15}/></div></div>{filtered.length?<div className="history-table-wrap"><table className="history-table"><thead><tr><th>TARGET</th><th>CATEGORY</th><th>STATUS</th><th>ATTEMPTS</th><th>STARTED</th><th>FINDINGS</th></tr></thead><tbody>{filtered.map(s=><tr key={s.scan_id}><td><div className="table-target"><span className="table-icon"><Globe2 size={15}/></span><span><strong>{s.targetName||'Target'}</strong><small title={s.target_id}>{s.scan_id.slice(0,8)}…</small></span></div></td><td><span className="table-category">{s.category}</span></td><td><span className={cx('scan-status',s.status.toLowerCase())}>{s.status}</span></td><td>{s.budget}</td><td>{new Date(s.createdAt).toLocaleString()}</td><td><button className="dashboard-link" onClick={() => onSelectScan?.(s.scan_id)}>Inspect <ArrowUpRight size={13}/></button></td></tr>)}</tbody></table></div>:<div className="history-empty"><div className="empty-icon"><History size={18}/></div><strong>{query?'No matching assessments':'No scans in your history yet'}</strong><p>{query?'Try a different search term.':'Once you start an assessment, its request will be listed here.'}</p></div>}<div className="history-note"><CircleHelp size={14}/>History is stored locally on this device. Engine-backed scan retrieval will be available when lifecycle persistence is connected.</div></section></div>;
}

function Assistant({history}:{history:LocalScan[]}) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      text: 'Hi, I’m Aegis Assistant. I can help you with the OWASP Top 10 for LLM Applications (2026), target configuration, Playwright calibration, and remediation playbooks.',
      source_ids: [],
      citations: [],
    }
  ]);
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const starters = [
    'What is LLM08:2026 Hidden Context Exposure?',
    'What were the 2025 names that changed in 2026?',
    'How do I calibrate a web target?',
    'Can Aegis scan for prompt injection?'
  ];

  async function send(text = draft, mode?: 'ask' | 'simplify') {
    const q = text.trim();
    if (!q || busy) return;
    const userMsg: ChatMessage = { role: 'user', text: q };
    const nextHistory = [...messages, userMsg];
    setMessages(nextHistory);
    setDraft('');
    setBusy(true);

    try {
      const res = await api.chatAssistant({
        message: q,
        history: nextHistory,
        mode: mode ?? null,
      });
      setMessages(m => [
        ...m,
        {
          role: 'assistant',
          text: res.reply,
          source_ids: res.source_ids || [],
          citations: res.citations || [],
        }
      ]);
    } catch {
      const fallback = assist(q, history.length);
      setMessages(m => [
        ...m,
        {
          role: 'assistant',
          text: fallback + '\n\n*(Note: Local engine on port 8765 was unreachable; showing built-in guidance.)*',
          source_ids: [],
          citations: [],
        }
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page-content assistant-page">
      <Heading eyebrow="YOUR SECURITY COPILOT" title="Aegis assistant" sub="Grounded in OWASP Top 10 2026 and Aegis operational playbooks."/>
      <div className="assistant-layout">
        <section className="panel chat-panel">
          <div className="chat-top">
            <div className="assistant-avatar"><Bot size={19}/><i/></div>
            <div>
              <strong>Aegis Assistant</strong>
              <small><span className="status-dot online"/>Local RAG · llama3.2 & nomic-embed</small>
            </div>
            <span className="chat-model">RAG · LLAMA 3.2</span>
          </div>

          <div className="chat-messages">
            {messages.map((m, i) => (
              <div className={cx('message-row', m.role)} key={i}>
                {m.role === 'assistant' && (
                  <div className="message-avatar"><Bot size={14}/></div>
                )}
                <div className="message-bubble">
                  <div style={{ whiteSpace: 'pre-wrap' }}>{m.text}</div>
                  {m.role === 'assistant' && m.citations && m.citations.length > 0 && (
                    <div className="citation-chips" style={{ display: 'flex', flexWrap: 'wrap', gap: '5px', marginTop: '8px', paddingTop: '6px', borderTop: '1px solid rgba(0,0,0,0.06)' }}>
                      {m.citations.slice(0, 4).map((c, idx) => (
                        <span key={idx} style={{ fontSize: '11px', background: 'rgba(59, 130, 246, 0.08)', color: '#1e40af', padding: '2px 6px', borderRadius: '4px', fontWeight: 500 }}>
                          {c.risk_id ? `${c.risk_id}${c.page ? `, p.${c.page}` : ''}` : (c.source_title || c.source)}
                        </span>
                      ))}
                    </div>
                  )}
                  {m.role === 'assistant' && i > 0 && (
                    <div style={{ marginTop: '8px' }}>
                      <button
                        type="button"
                        style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '11px', padding: '3px 8px', background: 'transparent', border: '1px solid #cbd5e1', borderRadius: '4px', cursor: 'pointer', color: '#475569' }}
                        onClick={() => void send('Explain this more simply', 'simplify')}
                        disabled={busy}
                      >
                        <Sparkles size={11}/> Explain simply
                      </button>
                    </div>
                  )}
                </div>
                {m.role === 'user' && (
                  <div className="message-avatar user-message-avatar"><UserRound size={14}/></div>
                )}
              </div>
            ))}
            {busy && (
              <div className="message-row">
                <div className="message-avatar"><Bot size={14}/></div>
                <div className="message-bubble typing"><i/><i/><i/></div>
              </div>
            )}
          </div>

          <div className="suggestion-row">
            {starters.map(s => (
              <button key={s} onClick={() => void send(s)} disabled={busy}>
                {s}<ArrowUpRight size={12}/>
              </button>
            ))}
          </div>

          <form className="chat-compose" onSubmit={e => { e.preventDefault(); void send(); }}>
            <input
              value={draft}
              onChange={e => setDraft(e.target.value)}
              placeholder="Ask about OWASP Top 10 2026, Aegis, scans, or calibration…"
              disabled={busy}
            />
            <button type="submit" disabled={!draft.trim() || busy}>
              <ArrowUpRight size={17}/>
            </button>
          </form>

          <div className="chat-disclaimer">
            <ShieldCheck size={12}/> Assistant guidance is informational and grounded in the local KB. Confirm authorization before every scan.
          </div>
        </section>

        <aside className="assistant-aside">
          <div className="panel assistant-context">
            <div className="panel-head">
              <div><h3>Workspace context</h3><p>What the assistant can see</p></div>
              <Sparkles size={17} className="muted-icon"/>
            </div>
            <div className="context-row"><span>Assessment history</span><strong>{history.length} runs</strong></div>
            <div className="context-row"><span>Knowledge corpus</span><strong>115 indexed chunks</strong></div>
            <div className="context-row"><span>Verified scan module</span><strong>LLM08 active</strong></div>
            <div className="context-row"><span>Target content</span><strong>Not shared</strong></div>
            <div className="privacy-note"><Shield size={14}/>Target page contents and scan evidence are not sent to the assistant.</div>
          </div>

          <div className="panel guide-panel">
            <div className="guide-heading">
              <div className="guide-spark"><Sparkles size={16}/></div>
              <div><strong>Playwright calibration</strong><small>2 target controls to select</small></div>
            </div>
            <div className="guide-step"><span>1</span>Click the chat input area</div>
            <div className="guide-step"><span>2</span>Click the Enter / Send button</div>
            <p>Aegis checks off each selection and detects the response area automatically.</p>
          </div>
        </aside>
      </div>
    </div>
  );
}

function Profile({onSaveName}:{onSaveName:(name:string)=>void}) {
  const [name,setName]=useState(localStorage.getItem(PROFILE_KEY)||'Security analyst');const [saved,setSaved]=useState(false);
  function save(){const savedName=name.trim()||'Security analyst';localStorage.setItem(PROFILE_KEY,savedName);onSaveName(savedName);setSaved(true);window.setTimeout(()=>setSaved(false),2200);}
  return <div className="page-content"><Heading eyebrow="WORKSPACE SETTINGS" title="Profile & preferences" sub="Manage the local desktop profile and workspace preferences."/><div className="profile-layout"><section className="panel profile-panel"><div className="profile-panel-head"><div className="large-profile-avatar">{(name||'S').slice(0,1).toUpperCase()}</div><div><h3>Personal profile</h3><p>Your profile is stored on this device.</p></div></div><div className="field"><label>DISPLAY NAME</label><input value={name} onChange={e=>setName(e.target.value)} placeholder="Security analyst"/></div><div className="profile-detail"><div><UserRound size={16}/><span>Account type</span></div><strong>Local workspace</strong></div><div className="profile-detail"><div><Command size={16}/><span>Workspace</span></div><strong>Personal</strong></div><button className="button primary" onClick={save}>{saved?<Check size={15}/>:<Check size={15}/>} {saved?'Saved':'Save preferences'}</button></section><section className="panel preferences-panel"><div className="panel-head"><div><h3>Runtime preferences</h3><p>Local service connection details</p></div><Settings2 size={17} className="muted-icon"/></div><div className="preference-row"><div className="pref-icon"><Radio size={16}/></div><div><strong>Aegis Engine</strong><small>http://localhost:8765</small></div><span className={cx('scan-status', 'completed')}>LOCAL</span></div><div className="preference-row"><div className="pref-icon"><Bot size={16}/></div><div><strong>Ollama assistant</strong><small>Configured through the local engine</small></div><span className="scan-status">OPTIONAL</span></div><div className="preference-row"><div className="pref-icon"><History size={16}/></div><div><strong>Scan history</strong><small>Saved in this browser profile</small></div><span className="scan-status completed">ON DEVICE</span></div><div className="profile-note"><ShieldCheck size={16}/>Aegis keeps this profile and scan request history on your device.</div></section></div></div>;
}

function connectorFailed(turn: ScanEvent): boolean {
  return turn.status === 'error' || turn.status === 'timeout'
    || /^\[CONNECTOR_(ERROR|TIMEOUT)\]/.test(turn.response || '');
}

function LiveScanPage({scan,targetName,onStatus,onInspectResults}:{scan:ScanRecord;targetName:string;onStatus:(status:string)=>void;onInspectResults?:(scanId:string)=>void}) {
  const events=useScanSocket(scan.scan_id);
  const [savedTurns,setSavedTurns]=useState<ScanTurn[]>([]);
  const [status,setStatus]=useState(scan.status);
  const [attempt,setAttempt]=useState(0);
  const [stopBusy,setStopBusy]=useState(false);
  const [error,setError]=useState('');
  const finished=['COMPLETED','STOPPED','FAILED'].includes(status.toUpperCase());
  useEffect(()=>{
    let alive=true;
    const poll=async()=>{try{
      const next = await api.scanStatus(scan.scan_id);
      if(!alive)return;
      setStatus(next.status);
      setAttempt(next.current_attempt);
      onStatus(next.status);
      try {
        setSavedTurns(await api.scanTurns(scan.scan_id));
      } catch (turnError) {
        // Older engine processes may not have the replay route yet; live telemetry
        // and status polling must continue working while that process is restarted.
        if (alive && !/404|not found/i.test(errorText(turnError))) {
          setError(errorText(turnError));
        }
      }
    }catch(e){if(alive)setError(errorText(e));}};
    void poll();
    const timer=window.setInterval(()=>{if(!finished)void poll();},1000);
    return()=>{alive=false;window.clearInterval(timer);};
  },[scan.scan_id,finished,onStatus]);
  useEffect(()=>{for(const event of events){if(event.event==='turn_started'||event.event==='turn_completed')setAttempt(current=>Math.max(current,event.attempt||0));if(event.event.startsWith('scan_')&&event.status)setStatus(event.status);if(event.event==='scan_failed'&&event.error)setError(event.error);}},[events]);
  async function stop(){setStopBusy(true);setError('');try{await api.stopScan(scan.scan_id);}catch(e){setError(errorText(e));}finally{setStopBusy(false);}}
  const liveTurns=events.filter(event=>event.event==='turn_started'||event.event==='turn_completed').reduce<ScanEvent[]>((acc,event)=>{const index=acc.findIndex(item=>item.attempt===event.attempt);if(index<0)acc.push(event);else if(event.event==='turn_completed')acc[index]=event;return acc;},[]);
  const persistedTurns = savedTurns.map((turn): ScanEvent => ({
    scan_id: scan.scan_id,
    event: 'turn_completed',
    attempt: turn.turn_index,
    prompt: turn.prompt,
    response: turn.response,
    status: turn.status,
    latency_ms: turn.latency_ms,
    strategy: turn.strategy || undefined,
    verdict: turn.verdict || undefined,
  }));
  const savedAttempts = new Set(persistedTurns.map(turn => turn.attempt));
  const turns = [...persistedTurns, ...liveTurns.filter(turn => !savedAttempts.has(turn.attempt))]
    .sort((a,b)=>(b.attempt||0)-(a.attempt||0));
  const progress=Math.min(100,Math.round((attempt/Math.max(scan.budget,1))*100));
  return <div className="page-content live-page"><Heading eyebrow="LIVE ASSESSMENT" title="Scan activity" sub={`${targetName} · ${scan.category} · Playwright browser is open`} action={finished ? <button className="button primary" onClick={()=>onInspectResults?.(scan.scan_id)}><ShieldAlert size={15}/>Inspect findings</button> : <button className="button secondary" onClick={()=>void stop()} disabled={stopBusy}>{stopBusy?<LoaderCircle className="spin" size={15}/>:<Square size={14}/>}Stop scan</button>}/>
    <div className="live-summary panel"><div className="live-state"><span className={cx('status-dot',finished?'':'online')}/><div><strong>{status.replace(/_/g,' ')}</strong><small>{targetName} · scan {scan.scan_id.slice(0,8)}</small></div></div><div className="live-progress"><div><span>Attempts</span><strong>{attempt} / {scan.budget}</strong></div><div className="progress-track"><i style={{width:`${progress}%`}}/></div></div><div className="live-category-badge"><ShieldCheck size={16}/><span>LLM08 active</span></div></div>
    <div className="live-grid"><section className="panel live-feed"><div className="panel-head"><div><h3>Prompt activity</h3><p>Prompts and chatbot replies from this browser session</p></div><span className={cx('live-indicator',!finished&&'live')}>{!finished&&<i/>}{finished?'ENDED':'LIVE'}</span></div>{error&&<div className="error-box"><AlertTriangle size={15}/>{error}</div>}{turns.length?turns.map(event=><article className="turn-card" key={`${event.attempt}-${event.event}`}><div className="turn-heading"><span className="turn-number">Attempt {event.attempt||'—'}</span><span className={cx('scan-status',(connectorFailed(event)?'failed':event.event==='turn_completed'?'completed':'running'))}>{connectorFailed(event)?'Connector failed':event.event==='turn_completed'?'Response received':'Sending prompt'}</span></div><div className="turn-section"><small>PROMPT · {event.strategy||'LLM08'}</small><p>{event.prompt||'Waiting for prompt details…'}</p></div>{event.event==='turn_completed'?<><div className="turn-section response"><small>{connectorFailed(event)?'CONNECTOR ERROR - Not evaluated':'CHATBOT RESPONSE'} {event.latency_ms!=null?`· ${event.latency_ms} ms`:''}</small><p>{event.response||'(No response text returned)'}</p></div>{!connectorFailed(event)&&event.verdict&&<div className="turn-verdict"><ShieldCheck size={14}/>{event.verdict.exploited?'Potential disclosure detected':'No disclosure detected'}{event.verdict.rationale&&<span>{event.verdict.rationale}</span>}</div>}</>:<div className="turn-wait"><LoaderCircle size={14} className="spin"/>Waiting for the chatbot response…</div>}</article>):<div className="live-empty"><LoaderCircle size={18} className="spin"/><strong>Waiting for the first prompt</strong><span>Prompts will appear here as the scan runs.</span></div>}</section>
      <aside className="live-aside"><section className="panel category-panel"><div className="panel-head"><div><h3>OWASP categories</h3><p>Scan module progress</p></div></div>{OWASP.map(([id,title])=><div className={cx('category-row',id==='LLM08'&&'current')} key={id}><span className="category-check">{id==='LLM08'?(status.toUpperCase()==='COMPLETED'?<Check size={13}/>:finished?<X size={13}/>:<LoaderCircle size={13} className="spin"/>):<span/>}</span><div><strong>{id}</strong><small>{title}</small></div><em>{id==='LLM08'?status.toUpperCase()==='COMPLETED'?'Done':status.toUpperCase()==='FAILED'?'Failed':status.toUpperCase()==='STOPPED'?'Stopped':finished?'Ended':'Active':'Not enabled'}</em></div>)}</section><div className="panel browser-note"><div className="browser-note-icon"><Globe2 size={16}/></div><div><strong>Target browser</strong><p>Playwright is interacting with the local site in a separate visible browser window. Keep it open while the scan runs.</p></div></div></aside></div>
  </div>;
}
