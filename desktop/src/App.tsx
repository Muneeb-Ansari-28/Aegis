import { useCallback, useEffect, useState, type ReactNode } from 'react';
import { AlertTriangle, ArrowUpRight, Bot, Check, CircleHelp, Command, Globe2, History, LoaderCircle, Radio, Search, Settings2, Shield, ShieldCheck, SlidersHorizontal, Sparkles, Square, UserRound, X } from 'lucide-react';
import { api, assist, type ScanRecord, type ScanTurn, type Target } from './api/client';
import { useScanSocket, type ScanEvent } from './hooks/useScanSocket';
import Overview from './components/Overview';
import NewAssessment from './components/NewAssessment';
import ApplicationShell, { type AppPage as Page } from './components/ApplicationShell';

type ChatMessage = { role: 'assistant' | 'user'; text: string };
type LocalScan = ScanRecord & { targetName?: string; createdAt: string };
const HISTORY_KEY = 'aegis.scan-history';
const PROFILE_KEY = 'aegis.profile';
const OWASP = [
  ['LLM01', 'Prompt Injection'], ['LLM02', 'Sensitive Information Disclosure'], ['LLM03', 'Supply Chain'], ['LLM04', 'Data and Model Poisoning'], ['LLM05', 'Improper Output Handling'], ['LLM06', 'Excessive Agency'], ['LLM07', 'System Prompt Leakage'], ['LLM08', 'Vector and Embedding Weaknesses'], ['LLM09', 'Misinformation'], ['LLM10', 'Unbounded Consumption'],
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

  return <><ApplicationShell page={page} onNavigate={setPage} hasActiveScan={Boolean(activeScan)}
    profileName={profileName} engineOnline={engineOnline} ollamaOnline={ollamaOnline} onRefresh={refresh}>
      {page === 'overview' && <Overview history={history} activeScan={activeScan} onNavigate={setPage} engineOnline={engineOnline} ollamaOnline={ollamaOnline} profileName={profileName} onRefresh={refresh}/>}
      {page === 'scan' && <NewAssessment targets={targets} refresh={refresh} onStarted={onScanStarted} notify={setToast}/>}
      {page === 'live' && activeScan && <LiveScanPage scan={activeScan} targetName={history.find(item => item.scan_id === activeScan.scan_id)?.targetName || 'Local target'} onStatus={onScanStatus}/>}
      {page === 'history' && <HistoryPage history={history} onRefresh={() => { const h = readHistory(); setHistory(h); }} />}
      {page === 'assistant' && <Assistant history={history}/>}
      {page === 'profile' && <Profile onSaveName={setProfileName}/>}
    </ApplicationShell>{toast && <div className="toast"><Check size={17}/>{toast}<button onClick={() => setToast('')}><X size={15}/></button></div>}
  </>;
}

function Heading({ eyebrow, title, sub, action }: { eyebrow: string; title: string; sub: string; action?: ReactNode }) { return <div className="page-heading"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{sub}</p></div>{action}</div>; }

function HistoryPage({history,onRefresh}:{history:LocalScan[];onRefresh:()=>void}) {
  const [query,setQuery]=useState(''); const filtered=history.filter(x=>(x.targetName||'').toLowerCase().includes(query.toLowerCase())||x.category.toLowerCase().includes(query.toLowerCase()));
  return <div className="page-content"><Heading eyebrow="ASSESSMENT RECORDS" title="Scan history" sub="Review scan requests started from this desktop workspace." action={<button className="button secondary" onClick={onRefresh}><Radio size={15}/>Refresh</button>}/><section className="panel history-panel"><div className="history-toolbar"><div className="history-count"><strong>{history.length}</strong> assessment{history.length===1?'':'s'}</div><div className="search-box"><Search size={15}/><input placeholder="Search target or category" value={query} onChange={e=>setQuery(e.target.value)}/><SlidersHorizontal size={15}/></div></div>{filtered.length?<div className="history-table-wrap"><table className="history-table"><thead><tr><th>TARGET</th><th>CATEGORY</th><th>STATUS</th><th>ATTEMPTS</th><th>STARTED</th></tr></thead><tbody>{filtered.map(s=><tr key={s.scan_id}><td><div className="table-target"><span className="table-icon"><Globe2 size={15}/></span><span><strong>{s.targetName||'Target'}</strong><small title={s.target_id}>{s.scan_id.slice(0,8)}…</small></span></div></td><td><span className="table-category">{s.category}</span></td><td><span className={cx('scan-status',s.status.toLowerCase())}>{s.status}</span></td><td>{s.budget}</td><td>{new Date(s.createdAt).toLocaleString()}</td></tr>)}</tbody></table></div>:<div className="history-empty"><div className="empty-icon"><History size={18}/></div><strong>{query?'No matching assessments':'No scans in your history yet'}</strong><p>{query?'Try a different search term.':'Once you start an assessment, its request will be listed here.'}</p></div>}<div className="history-note"><CircleHelp size={14}/>History is stored locally on this device. Engine-backed scan retrieval will be available when lifecycle persistence is connected.</div></section></div>;
}

function Assistant({history}:{history:LocalScan[]}) {
  const [messages,setMessages]=useState<ChatMessage[]>([{role:'assistant',text:'Hi, I’m Aegis Assistant. I can help you set up an authorized assessment, understand Playwright calibration, or explain what the current scan modules support.'}]); const [draft,setDraft]=useState(''); const [busy,setBusy]=useState(false);
  const starters=['How do I calibrate a web target?','Which OWASP categories are available?','What does the current scan module check?'];
  async function send(text=draft){const q=text.trim();if(!q||busy)return;setMessages(m=>[...m,{role:'user',text:q}]);setDraft('');setBusy(true);await new Promise(resolve=>window.setTimeout(resolve,240));setMessages(m=>[...m,{role:'assistant',text:assist(q,history.length)}]);setBusy(false);}
  return <div className="page-content assistant-page"><Heading eyebrow="YOUR SECURITY COPILOT" title="Aegis assistant" sub="Get help with target configuration, calibration, and assessment results."/><div className="assistant-layout"><section className="panel chat-panel"><div className="chat-top"><div className="assistant-avatar"><Bot size={19}/><i/></div><div><strong>Aegis Assistant</strong><small><span className="status-dot online"/>Built-in setup guidance · no model calls</small></div><span className="chat-model">GUIDE</span></div><div className="chat-messages">{messages.map((m,i)=><div className={cx('message-row',m.role)} key={i}>{m.role==='assistant'&&<div className="message-avatar"><Bot size={14}/></div>}<div className="message-bubble">{m.text}</div>{m.role==='user'&&<div className="message-avatar user-message-avatar"><UserRound size={14}/></div>}</div>)}{busy&&<div className="message-row"><div className="message-avatar"><Bot size={14}/></div><div className="message-bubble typing"><i/><i/><i/></div></div>}</div><div className="suggestion-row">{starters.map(s=><button key={s} onClick={()=>void send(s)}>{s}<ArrowUpRight size={12}/></button>)}</div><form className="chat-compose" onSubmit={e=>{e.preventDefault();void send();}}><input value={draft} onChange={e=>setDraft(e.target.value)} placeholder="Ask about Aegis, your scans, or calibration…"/><button type="submit" disabled={!draft.trim()||busy}><ArrowUpRight size={17}/></button></form><div className="chat-disclaimer"><ShieldCheck size={12}/> Assistant guidance is informational. Confirm authorization before every scan.</div></section><aside className="assistant-aside"><div className="panel assistant-context"><div className="panel-head"><div><h3>Workspace context</h3><p>What the assistant can see</p></div><Sparkles size={17} className="muted-icon"/></div><div className="context-row"><span>Assessment history</span><strong>{history.length} runs</strong></div><div className="context-row"><span>Assessment module</span><strong>LLM07 active</strong></div><div className="context-row"><span>Target content</span><strong>Not shared</strong></div><div className="privacy-note"><Shield size={14}/>Target page contents and scan evidence are not sent to the assistant.</div></div><div className="panel guide-panel"><div className="guide-heading"><div className="guide-spark"><Sparkles size={16}/></div><div><strong>Playwright calibration</strong><small>2 target controls to select</small></div></div><div className="guide-step"><span>1</span>Click the chat input area</div><div className="guide-step"><span>2</span>Click the Enter / Send button</div><p>Aegis checks off each selection and detects the response area automatically.</p></div></aside></div></div>;
}

function Profile({onSaveName}:{onSaveName:(name:string)=>void}) {
  const [name,setName]=useState(localStorage.getItem(PROFILE_KEY)||'Security analyst');const [saved,setSaved]=useState(false);
  function save(){const savedName=name.trim()||'Security analyst';localStorage.setItem(PROFILE_KEY,savedName);onSaveName(savedName);setSaved(true);window.setTimeout(()=>setSaved(false),2200);}
  return <div className="page-content"><Heading eyebrow="WORKSPACE SETTINGS" title="Profile & preferences" sub="Manage the local desktop profile and workspace preferences."/><div className="profile-layout"><section className="panel profile-panel"><div className="profile-panel-head"><div className="large-profile-avatar">{(name||'S').slice(0,1).toUpperCase()}</div><div><h3>Personal profile</h3><p>Your profile is stored on this device.</p></div></div><div className="field"><label>DISPLAY NAME</label><input value={name} onChange={e=>setName(e.target.value)} placeholder="Security analyst"/></div><div className="profile-detail"><div><UserRound size={16}/><span>Account type</span></div><strong>Local workspace</strong></div><div className="profile-detail"><div><Command size={16}/><span>Workspace</span></div><strong>Personal</strong></div><button className="button primary" onClick={save}>{saved?<Check size={15}/>:<Check size={15}/>} {saved?'Saved':'Save preferences'}</button></section><section className="panel preferences-panel"><div className="panel-head"><div><h3>Runtime preferences</h3><p>Local service connection details</p></div><Settings2 size={17} className="muted-icon"/></div><div className="preference-row"><div className="pref-icon"><Radio size={16}/></div><div><strong>Aegis Engine</strong><small>http://localhost:8765</small></div><span className={cx('scan-status', 'completed')}>LOCAL</span></div><div className="preference-row"><div className="pref-icon"><Bot size={16}/></div><div><strong>Ollama assistant</strong><small>Configured through the local engine</small></div><span className="scan-status">OPTIONAL</span></div><div className="preference-row"><div className="pref-icon"><History size={16}/></div><div><strong>Scan history</strong><small>Saved in this browser profile</small></div><span className="scan-status completed">ON DEVICE</span></div><div className="profile-note"><ShieldCheck size={16}/>Aegis keeps this profile and scan request history on your device.</div></section></div></div>;
}

function LiveScanPage({scan,targetName,onStatus}:{scan:ScanRecord;targetName:string;onStatus:(status:string)=>void}) {
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
  useEffect(()=>{for(const event of events){if(event.event==='turn_started'||event.event==='turn_completed')setAttempt(current=>Math.max(current,event.attempt||0));if(event.status)setStatus(event.status);}},[events]);
  async function stop(){setStopBusy(true);setError('');try{await api.stopScan(scan.scan_id);}catch(e){setError(errorText(e));}finally{setStopBusy(false);}}
  const liveTurns=events.filter(event=>event.event==='turn_started'||event.event==='turn_completed').reduce<ScanEvent[]>((acc,event)=>{const index=acc.findIndex(item=>item.attempt===event.attempt);if(index<0)acc.push(event);else if(event.event==='turn_completed')acc[index]=event;return acc;},[]);
  const persistedTurns = savedTurns.map((turn): ScanEvent => ({
    scan_id: scan.scan_id,
    event: 'turn_completed',
    attempt: turn.turn_index,
    prompt: turn.prompt,
    response: turn.response,
    latency_ms: turn.latency_ms,
    strategy: turn.strategy || undefined,
    verdict: turn.verdict || undefined,
  }));
  const savedAttempts = new Set(persistedTurns.map(turn => turn.attempt));
  const turns = [...persistedTurns, ...liveTurns.filter(turn => !savedAttempts.has(turn.attempt))]
    .sort((a,b)=>(b.attempt||0)-(a.attempt||0));
  const progress=Math.min(100,Math.round((attempt/Math.max(scan.budget,1))*100));
  return <div className="page-content live-page"><Heading eyebrow="LIVE ASSESSMENT" title="Scan activity" sub={`${targetName} · ${scan.category} · Playwright browser is open`} action={!finished&&<button className="button secondary" onClick={()=>void stop()} disabled={stopBusy}>{stopBusy?<LoaderCircle className="spin" size={15}/>:<Square size={14}/>}Stop scan</button>}/>
    <div className="live-summary panel"><div className="live-state"><span className={cx('status-dot',finished?'':'online')}/><div><strong>{status.replace(/_/g,' ')}</strong><small>{targetName} · scan {scan.scan_id.slice(0,8)}</small></div></div><div className="live-progress"><div><span>Prompts sent</span><strong>{attempt} / {scan.budget}</strong></div><div className="progress-track"><i style={{width:`${progress}%`}}/></div></div><div className="live-category-badge"><ShieldCheck size={16}/><span>LLM07 active</span></div></div>
    <div className="live-grid"><section className="panel live-feed"><div className="panel-head"><div><h3>Prompt activity</h3><p>Prompts and chatbot replies from this browser session</p></div><span className={cx('live-indicator',!finished&&'live')}>{!finished&&<i/>}{finished?'ENDED':'LIVE'}</span></div>{error&&<div className="error-box"><AlertTriangle size={15}/>{error}</div>}{turns.length?turns.map(event=><article className="turn-card" key={`${event.attempt}-${event.event}`}><div className="turn-heading"><span className="turn-number">Attempt {event.attempt||'—'}</span><span className={cx('scan-status',(event.event==='turn_completed'?'completed':'running'))}>{event.event==='turn_completed'?'Response received':'Sending prompt'}</span></div><div className="turn-section"><small>PROMPT · {event.strategy||'LLM07'}</small><p>{event.prompt||'Waiting for prompt details…'}</p></div>{event.event==='turn_completed'?<><div className="turn-section response"><small>CHATBOT RESPONSE {event.latency_ms!=null?`· ${event.latency_ms} ms`:''}</small><p>{event.response||'(No response text returned)'}</p></div>{event.verdict&&<div className="turn-verdict"><ShieldCheck size={14}/>{event.verdict.exploited?'Potential disclosure detected':'No disclosure detected'}{event.verdict.rationale&&<span>{event.verdict.rationale}</span>}</div>}</>:<div className="turn-wait"><LoaderCircle size={14} className="spin"/>Waiting for the chatbot response…</div>}</article>):<div className="live-empty"><LoaderCircle size={18} className="spin"/><strong>Waiting for the first prompt</strong><span>Prompts will appear here as the scan runs.</span></div>}</section>
      <aside className="live-aside"><section className="panel category-panel"><div className="panel-head"><div><h3>OWASP categories</h3><p>Scan module progress</p></div></div>{OWASP.map(([id,title])=><div className={cx('category-row',id==='LLM07'&&'current')} key={id}><span className="category-check">{id==='LLM07'?(status.toUpperCase()==='COMPLETED'?<Check size={13}/>:finished?<X size={13}/>:<LoaderCircle size={13} className="spin"/>):<span/>}</span><div><strong>{id}</strong><small>{title}</small></div><em>{id==='LLM07'?status.toUpperCase()==='COMPLETED'?'Done':status.toUpperCase()==='FAILED'?'Failed':status.toUpperCase()==='STOPPED'?'Stopped':finished?'Ended':'Active':'Not enabled'}</em></div>)}</section><div className="panel browser-note"><div className="browser-note-icon"><Globe2 size={16}/></div><div><strong>Target browser</strong><p>Playwright is interacting with the local site in a separate visible browser window. Keep it open while the scan runs.</p></div></div></aside></div>
  </div>;
}
