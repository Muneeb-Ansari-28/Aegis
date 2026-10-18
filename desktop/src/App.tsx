import { useCallback, useEffect, useState, type ReactNode } from 'react';
import { ArrowUpRight, Bot, Check, CircleHelp, Command, Globe2, History, Radio, Search, Settings2, Shield, ShieldCheck, SlidersHorizontal, Sparkles, UserRound, X } from 'lucide-react';
import { api, assist, type ScanRecord, type Target } from './api/client';
import { useLiveScan } from './hooks/useLiveScan';
import LiveScan from './components/LiveScan';
import Overview from './components/Overview';
import NewAssessment from './components/NewAssessment';
import ApplicationShell, { type AppPage as Page } from './components/ApplicationShell';

type ChatMessage = { role: 'assistant' | 'user'; text: string };
type LocalScan = ScanRecord & { targetName?: string; createdAt: string };
const HISTORY_KEY = 'aegis.scan-history';
const PROFILE_KEY = 'aegis.profile';
type SelectedScan = ScanRecord & { targetName?: string; targetUrl?: string };
const SELECTED_SCAN_KEY = 'aegis.selected-scan';
function readSelectedScan(): SelectedScan | null {
  try {
    const value = JSON.parse(sessionStorage.getItem(SELECTED_SCAN_KEY) || 'null') as SelectedScan | null;
    return value && typeof value.scan_id === 'string' && typeof value.target_id === 'string' && typeof value.status === 'string' && typeof value.category === 'string' && Number.isFinite(value.budget) ? value : null;
  } catch { return null; }
}

function readHistory(): LocalScan[] { try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]') as LocalScan[]; } catch { return []; } }
function cx(...v: Array<string | false | null | undefined>): string { return v.filter(Boolean).join(' '); }
export default function App() {
  const [page, setPage] = useState<Page>(() => readSelectedScan() ? 'live' : 'overview');
  const [engineOnline, setEngineOnline] = useState<boolean | null>(null);
  const [ollamaOnline, setOllamaOnline] = useState<boolean | null>(null);
  const [targets, setTargets] = useState<Target[]>([]);
  const [history, setHistory] = useState<LocalScan[]>(readHistory);
  const [activeScan, setActiveScan] = useState<SelectedScan | null>(readSelectedScan);
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
    setActiveScan({ ...scan, targetName: target?.name, targetUrl: target?.url });
    const next = [{ ...scan, targetName: target?.name, createdAt: new Date().toISOString() }, ...readHistory()].slice(0, 100);
    setHistory(next); localStorage.setItem(HISTORY_KEY, JSON.stringify(next));
    setPage('live'); setToast('Scan request acknowledged. Monitoring the selected assessment.');
  };
  const onScanStatus = useCallback((status: string) => {
    setActiveScan(current => current && current.status !== status ? { ...current, status } : current);
    setHistory(current => {
      if (!current.some(item => item.scan_id === activeScan?.scan_id && item.status !== status)) return current;
      const updated = current.map(item => item.scan_id === activeScan?.scan_id ? { ...item, status } : item);
      localStorage.setItem(HISTORY_KEY, JSON.stringify(updated));
      return updated;
    });
  }, [activeScan?.scan_id]);

  const live = useLiveScan(activeScan, onScanStatus);
  useEffect(() => {
    try { if (activeScan) sessionStorage.setItem(SELECTED_SCAN_KEY, JSON.stringify(activeScan)); } catch { /* Monitoring still works if browser storage is unavailable. */ }
  }, [activeScan]);

  return <><ApplicationShell page={page} onNavigate={setPage} hasActiveScan={Boolean(activeScan)}
    profileName={profileName} engineOnline={engineOnline} ollamaOnline={ollamaOnline} onRefresh={refresh}>
      {page === 'overview' && <Overview history={history} activeScan={activeScan} onNavigate={setPage} engineOnline={engineOnline} ollamaOnline={ollamaOnline} profileName={profileName} onRefresh={refresh}/>}
      {page === 'scan' && <NewAssessment targets={targets} refresh={refresh} onStarted={onScanStarted} notify={setToast}/>}
      {page === 'live' && activeScan && <LiveScan key={activeScan.scan_id} scan={activeScan} targetName={activeScan.targetName || history.find(item => item.scan_id === activeScan.scan_id)?.targetName || 'Local target'} targetUrl={activeScan.targetUrl || targets.find(target => target.id === activeScan.target_id)?.url} state={live}/>}
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
