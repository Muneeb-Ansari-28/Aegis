import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import { AlertTriangle, ArrowUpRight, Bot, Check, CircleHelp, Command, Globe2, History, Laptop, LoaderCircle, MousePointer2, Play, Radio, Search, Settings2, Shield, ShieldCheck, SlidersHorizontal, Sparkles, Square, UserRound, X } from 'lucide-react';
import { api, assist, type CalibrationSession, type ScanRecord, type ScanTurn, type Target } from './api/client';
import { useScanSocket, type ScanEvent } from './hooks/useScanSocket';
import Overview from './components/Overview';
import ApplicationShell, { type AppPage as Page } from './components/ApplicationShell';

type ScanMode = 'web' | 'desktop';
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
function normalizeTargetUrl(raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed) throw new Error('Enter the local target URL before continuing.');
  const withScheme = /^[a-z][a-z0-9+.-]*:\/\//i.test(trimmed) ? trimmed : `http://${trimmed}`;
  let parsed: URL;
  try { parsed = new URL(withScheme); } catch { throw new Error('Enter a valid URL such as http://127.0.0.1:5173.'); }
  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') throw new Error('Target URL must start with http:// or https://.');
  return withScheme;
}
function normalizeTargetUrlSafe(raw: string): string {
  try { return normalizeTargetUrl(raw); } catch { return raw.trim() || 'the target URL'; }
}

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
      {page === 'scan' && <NewScan targets={targets} refresh={refresh} onStarted={onScanStarted} notify={setToast}/>}
      {page === 'live' && activeScan && <LiveScanPage scan={activeScan} targetName={history.find(item => item.scan_id === activeScan.scan_id)?.targetName || 'Local target'} onStatus={onScanStatus}/>}
      {page === 'history' && <HistoryPage history={history} onRefresh={() => { const h = readHistory(); setHistory(h); }} />}
      {page === 'assistant' && <Assistant history={history}/>}
      {page === 'profile' && <Profile onSaveName={setProfileName}/>}
    </ApplicationShell>{toast && <div className="toast"><Check size={17}/>{toast}<button onClick={() => setToast('')}><X size={15}/></button></div>}
  </>;
}

function Heading({ eyebrow, title, sub, action }: { eyebrow: string; title: string; sub: string; action?: ReactNode }) { return <div className="page-heading"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{sub}</p></div>{action}</div>; }

function NewScan({ targets, refresh, onStarted, notify }: { targets: Target[]; refresh: () => Promise<void>; onStarted: (s: ScanRecord,t?: Target)=>void; notify: (s:string)=>void }) {
  const [mode, setMode] = useState<ScanMode>('web'); const [targetId, setTargetId] = useState(''); const [name,setName]=useState(''); const [url,setUrl]=useState(''); const [category,setCategory]=useState('LLM07'); const [budget,setBudget]=useState(10); const [consent,setConsent]=useState(false); const [busy,setBusy]=useState(false); const [calibrating,setCalibrating]=useState(false); const [calibration,setCalibration]=useState<Target['calibration_config']>(); const [calibrationSession,setCalibrationSession]=useState<CalibrationSession|null>(null); const [calibrationMethod,setCalibrationMethod]=useState<'auto'|'click'|null>(null); const [error,setError]=useState(''); const [calibError,setCalibError]=useState(''); const consentRef=useRef<HTMLDivElement>(null);
  const selected = targets.find(t=>t.id===targetId); const supported=category==='LLM07';
  async function calibrate(interactive:boolean) {
    setError(''); setCalibError(''); setCalibrationSession(null); setCalibrationMethod(interactive?'click':'auto');
    if(!consent){const msg='Confirm authorization below before Aegis opens this local target.';setError(msg);setCalibError(msg);consentRef.current?.scrollIntoView({behavior:'smooth',block:'center'});return;}
    let targetUrl='';try{targetUrl=normalizeTargetUrl(url);}catch(e){const msg=errorText(e);setError(msg);setCalibError(msg);return;}
    setCalibrating(true);
    try {
      const target=selected||await api.createTarget({name:name.trim()||new URL(targetUrl).hostname,target_type:'web',url:targetUrl});
      setTargetId(target.id); void refresh();
      if(!interactive){
        const result=await api.autoCalibrate(target.id);
        setCalibration(result.calibration_config); setCalibrationSession(null); void refresh();
        notify('Automatic calibration complete. Selectors saved to this target.');
        return;
      }
      let progress=await api.beginInteractiveCalibration(target.id,90);
      setCalibrationSession(progress);
      const deadline=Date.now()+95000;
      while(progress.status!=='completed'&&progress.status!=='failed'&&Date.now()<deadline){
        await new Promise(resolve=>window.setTimeout(resolve,300));
        progress=await api.calibrationStatus(target.id,progress.session_id);
        setCalibrationSession(progress);
      }
      if(progress.status==='failed') throw new Error(progress.error||'Click calibration failed.');
      let configWaits=0;
      while(progress.status==='completed'&&!progress.calibration_config&&configWaits<20){await new Promise(resolve=>window.setTimeout(resolve,250));progress=await api.calibrationStatus(target.id,progress.session_id);setCalibrationSession(progress);configWaits++;}
      if(progress.status==='failed') throw new Error(progress.error||'Click calibration failed.');
      if(progress.status!=='completed'||!progress.calibration_config) throw new Error('Calibration timed out before both target controls were selected.');
      setCalibration(progress.calibration_config); void refresh();
      notify('Click calibration complete. Selectors saved to this target.');
    }catch(e){const msg=errorText(e);setError(msg);setCalibError(msg);}finally{setCalibrating(false);}
  }
  async function start() { setError(''); setCalibError(''); if(!consent){setError('Confirm that you are authorized to assess this target.');return;} if(mode==='desktop'){setError('Desktop UI Automation is scaffolded but the engine adapter is not implemented yet.');return;} if(!supported){setError('The active assessment pipeline currently supports OWASP LLM07 only.');return;} if(!calibration){setError('Choose automatic or click calibration before starting the scan.');return;} let targetUrl='';try{targetUrl=normalizeTargetUrl(url);}catch(e){setError(errorText(e));return;} setBusy(true); try { let target=selected; if(!target) target=await api.createTarget({name:name.trim()||new URL(targetUrl).hostname,target_type:'web',url:targetUrl,calibration_config:calibration}); const scan=await api.startScan({target_id:target.id,category,budget,authorized:consent}); onStarted(scan,target); }catch(e){setError(errorText(e));}finally{setBusy(false);} }
  return <div className="page-content"><Heading eyebrow="NEW ASSESSMENT" title="Configure a scan" sub="Set up an authorized target, calibrate its interface, and choose an OWASP category."/><div className="scan-layout"><div className="scan-form-column"><section className="panel form-panel"><div className="section-title"><span className="step-number">01</span><div><h3>Choose target type</h3><p>Select the application surface you want to assess.</p></div></div><div className="mode-switch"><button onClick={()=>setMode('web')} className={cx(mode==='web'&&'selected')}><Globe2 size={18}/><span><strong>Web application</strong><small>Browser-based chat interface</small></span><span className="radio-dot"/></button><button onClick={()=>setMode('desktop')} className={cx(mode==='desktop'&&'selected')}><Laptop size={18}/><span><strong>Desktop application</strong><small>Native UI automation</small></span><span className="radio-dot"/></button></div></section>
  <section className="panel form-panel"><div className="section-title"><span className="step-number">02</span><div><h3>Configure target</h3><p>Register a target or pick one you have already added.</p></div></div>{targets.length>0&&<div className="field"><label>REGISTERED TARGETS</label><select value={targetId} onChange={e=>{setTargetId(e.target.value);const t=targets.find(x=>x.id===e.target.value);if(t){setUrl(t.url);setName(t.name);setCalibration(t.calibration_config);}}}><option value="">Add a new target…</option>{targets.map(t=><option key={t.id} value={t.id}>{t.name} · {t.url}</option>)}</select></div>}<div className="field-row"><div className="field"><label>TARGET NAME</label><input value={name} onChange={e=>setName(e.target.value)} placeholder="e.g. Internal support assistant"/></div><div className="field"><label>APPLICATION URL</label><input value={url} onChange={e=>{setUrl(e.target.value);setTargetId('');setCalibration(undefined);setCalibError('');}} placeholder="http://127.0.0.1:5173" disabled={mode==='desktop'}/></div></div>{mode==='web'&&<div className="calibration-box"><div className="calibration-info"><div className="calibration-icon"><MousePointer2 size={17}/></div><div><strong>Browser calibration</strong><p>{calibration?'Selectors are configured. You can recalibrate any time.':calibrating?calibrationMethod==='auto'?`Opening ${normalizeTargetUrlSafe(url)} in the Playwright browser — detecting the chat input, send button, and response area on its own.`:`Opening ${normalizeTargetUrlSafe(url)} in a visible browser. Open the chat if needed, then click its input area and its Enter / Send button.`:'Choose automatic calibration to detect the controls on its own, or click to calibrate and select the chatbot controls yourself.'}</p></div></div><div className="calibration-buttons"><button className="button secondary small" onClick={()=>void calibrate(false)} disabled={calibrating}>{calibrating?<LoaderCircle className="spin" size={15}/>:<Sparkles size={15}/>}Automatic calibration</button><button className="button secondary small" onClick={()=>void calibrate(true)} disabled={calibrating}>{calibrating?<LoaderCircle className="spin" size={15}/>:<MousePointer2 size={15}/>}Click to calibrate</button></div>{calibError&&<div className="calibration-error"><CircleHelp size={13}/>{calibError}</div>}{calibrationSession&&<div className="calibration-checklist"><div className={cx('checklist-item',calibrationSession.input_selected&&'done')}><span className="checklist-box">{calibrationSession.input_selected&&<Check size={11}/>}</span><span>Click on the input area</span></div><div className={cx('checklist-item',calibrationSession.enter_selected&&'done')}><span className="checklist-box">{calibrationSession.enter_selected&&<Check size={11}/>}</span><span>Click on the Enter / Send button</span></div><small className="checklist-status">{calibrationSession.status==='opening_browser'?'Opening the target in the Playwright browser…':calibrationSession.status==='saving_selectors'?'Both controls captured. Saving selectors…':calibrationSession.status==='capturing_controls'?calibrationSession.step===1?'Input captured. Now click the Enter / Send button in the browser.':'Waiting for you to click the input area in the browser…':calibrationSession.status==='completed'?'Both controls captured. Selectors saved to this target.':calibrationSession.status==='failed'?(calibrationSession.error||'Calibration failed. Try again.'):''}</small></div>}{calibration&&<div className="selector-list"><span><Check size={13}/>Input <code>{calibration.input_selector}</code></span><span><Check size={13}/>Send <code>{calibration.submit_selector}</code></span><span><Check size={13}/>Response <code>{calibration.response_selector}</code></span></div>}</div>}</section>
  <section className="panel form-panel"><div className="section-title"><span className="step-number">03</span><div><h3>Assessment scope</h3><p>Choose the OWASP LLM Top 10 category and test budget.</p></div></div><div className="field-row"><div className="field"><label>OWASP CATEGORY</label><select value={category} onChange={e=>setCategory(e.target.value)}>{OWASP.map(([id,title])=><option key={id} value={id}>{id} · {title}{id!=='LLM07'?' (coming soon)':''}</option>)}</select></div><div className="field budget-field"><label>ATTEMPT BUDGET <span>{budget} prompts</span></label><input type="range" min="1" max="10" value={budget} onChange={e=>setBudget(Number(e.target.value))}/><div className="range-hints"><span>1</span><span>10</span></div></div></div><div className="scope-note"><Shield size={15}/><span><strong>LLM07 · System Prompt Leakage</strong> is the active scan module. Other categories are shown for planning and are not yet supported by the assessment pipeline.</span></div></section>
  <div className={cx('consent-card',!consent&&Boolean(calibError)&&'attention')} ref={consentRef}><label className="consent-check"><input type="checkbox" checked={consent} onChange={e=>{setConsent(e.target.checked);if(e.target.checked&&calibError)setCalibError('');}}/><span className="custom-check"><Check size={13}/></span><span><strong>I confirm I own this target or have written permission to test it.</strong><small>Target interactions require your authorization. Scan request history is stored locally; orchestration is still in progress.</small></span></label></div>{error&&<div className="error-box"><CircleHelp size={16}/>{error}</div>}<div className="form-footer"><span><ShieldCheck size={14}/> Assessment requires explicit authorization</span><button className="button primary" onClick={()=>void start()} disabled={busy||calibrating||!consent}>{busy?<LoaderCircle className="spin" size={16}/>:<Play size={15} fill="currentColor"/>}Submit scan request <ArrowUpRight size={15}/></button></div></div><aside className="scan-side"><div className="panel side-summary"><div className="side-summary-head"><div className="summary-shield"><ShieldCheck size={18}/></div><div><strong>Assessment summary</strong><small>Review before you start</small></div></div><div className="summary-line"><span>Target type</span><strong>{mode==='web'?'Web application':'Desktop application'}</strong></div><div className="summary-line"><span>Target</span><strong className="truncate">{name||'Not configured'}</strong></div><div className="summary-line"><span>OWASP category</span><strong className="category-value">{category}</strong></div><div className="summary-line"><span>Prompt budget</span><strong>{budget} attempts</strong></div><div className="summary-line"><span>Browser connector</span><strong className="green-text"><span className="status-dot online"/>Playwright</strong></div><div className="summary-foot"><ShieldCheck size={15}/><span>Uses fabricated test content. No real secrets or jailbreak techniques.</span></div></div><div className="help-card"><div className="help-icon"><CircleHelp size={16}/></div><div><strong>Need a hand?</strong><p>The assistant can guide you through target setup and calibration.</p><button onClick={()=>notify('Open Aegis assistant from the left navigation.')}>View setup guide <ArrowUpRight size={13}/></button></div></div></aside></div></div>;
}

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
