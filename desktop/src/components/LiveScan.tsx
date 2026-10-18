import { useEffect, useRef, useState, type KeyboardEvent } from 'react';
import { Activity, ArrowDown, Check, ChevronRight, Clock3, FileText, Globe2, Info, LoaderCircle, Radio, Shield, Square, Zap } from 'lucide-react';
import type { ScanRecord } from '../api/client';
import type { ScanEvent } from '../hooks/useScanSocket';
import { isTerminal, type LiveScanState, type LiveTurn } from '../hooks/useLiveScan';
import './live-scan.css';

const tabs = ['Live Activity', 'Agent Reasoning', 'Requests & Responses', 'Evidence'];
const labels: Record<string, string> = { scan_queued: 'Assessment queued', scan_started: 'Assessment started', scan_completed: 'Assessment completed', scan_failed: 'Assessment failed', scan_stopped: 'Assessment stopped' };
const time = (value?: string) => value && !Number.isNaN(Date.parse(value)) ? new Date(value).toLocaleTimeString() : '—';
const latency = (value?: number) => typeof value === 'number' && Number.isFinite(value) && value > 0 ? `${(value / 1000).toFixed(2)}s` : 'Unavailable';
const verdictLabel = (turn: LiveTurn) => turn.verdict?.exploited === true ? 'Potential disclosure detected' : turn.verdict?.exploited === false ? 'No disclosure detected in this response' : 'Evaluation unavailable';
function eventLabel(event: ScanEvent) {
  if (event.event === 'turn_started') return `Prompt ${event.attempt ?? '—'} dispatched · awaiting response or evaluation`;
  if (event.event === 'turn_completed') return `Turn ${event.attempt ?? '—'} recorded${event.status ? ` · ${event.status}` : ''} · ${verdictLabel(event)}`;
  return labels[event.event] || event.event.replace(/_/g, ' ');
}

/** Display only backend events; following the log is opt-in again after scrolling away. */
function ActivityConsole({ state }: { state: LiveScanState }) {
  const viewport = useRef<HTMLDivElement>(null);
  const [follow, setFollow] = useState(true);
  useEffect(() => { if (follow && viewport.current) viewport.current.scrollTop = viewport.current.scrollHeight; }, [state.events, follow]);
  return <div className="execution-console-wrap"><div className="execution-console" ref={viewport} tabIndex={0} role="region" aria-label="Live activity history"
    onScroll={event => { const node = event.currentTarget; setFollow(node.scrollHeight - node.scrollTop - node.clientHeight < 32); }}>
    {state.events.length ? state.events.map((event, index) => <div className="execution-log-line" key={`${event.event}-${event.attempt}-${event.timestamp}-${index}`}><time title={event.timestamp || 'Timestamp not supplied'}>{time(event.timestamp)}</time><span aria-hidden="true" className={`execution-dot ${event.event === 'scan_failed' ? 'danger' : event.event.endsWith('completed') ? 'success' : 'accent'}`}/><span>{eventLabel(event)}</span></div>) : <div className="execution-console-empty"><Activity size={24}/><strong>{state.loading ? 'Connecting to this assessment…' : isTerminal(state.status) ? 'No activity events available' : state.statusError ? 'Activity connection unavailable' : 'Waiting for scan activity'}</strong><p>{isTerminal(state.status) ? 'The assessment has ended. Saved turns may still be available in Requests & Responses.' : 'Events will appear when supplied by the engine. Saved turns are available separately.'}</p></div>}
  </div><div className="execution-console-footer"><span>Live events · latest 250 · timestamps when supplied</span>{!follow && <button onClick={() => setFollow(true)}>Jump to latest <ArrowDown size={14}/></button>}</div></div>;
}

function Transcript({ turns, evidence, finished }: { turns: LiveTurn[]; evidence: boolean; finished: boolean }) {
  const shown = evidence ? turns.filter(turn => turn.verdict) : turns;
  return <div className="execution-transcript" tabIndex={0} role="region" aria-label={evidence ? 'Turn evidence' : 'Prompt and response transcript'}>
    {!shown.length && <div className="execution-empty"><FileText size={26}/><strong>{evidence ? 'No turn evidence available' : 'No recorded prompts yet'}</strong><p>{finished ? 'The assessment has ended. Missing data does not mean the target is secure.' : 'This panel updates when the engine supplies recorded turns.'}</p></div>}
    {shown.map(turn => <article className="execution-turn" key={turn.attempt}><header><strong>Prompt {turn.attempt}</strong><span>{turn.event === 'turn_completed' ? 'Recorded' : finished ? 'Incomplete' : 'Awaiting response'}</span></header>
      {turn.strategy && <small>Strategy: {turn.strategy}</small>}
      <h3>Request</h3><pre>{turn.prompt ?? 'Request text unavailable'}</pre>
      <h3>Response</h3><pre>{turn.response === '' ? '(Empty response returned)' : turn.response ?? 'Response not available'}</pre>
      <footer><span>Response time: {latency(turn.latency_ms)}</span><span>{turn.persisted ? 'Saved transcript' : 'Live telemetry'}</span></footer>
      {turn.verdict && <div className="execution-verdict"><strong>{verdictLabel(turn)}</strong><p>{turn.verdict.rationale || 'No evaluation rationale supplied.'}</p></div>}
    </article>)}
  </div>;
}

export default function LiveScan({ scan, targetName, targetUrl, state }: { scan: ScanRecord; targetName: string; targetUrl?: string; state: LiveScanState }) {
  const [tab, setTab] = useState(0);
  const finished = isTerminal(state.status);
  const completed = state.turns.filter(turn => turn.event === 'turn_completed');
  const latest = state.turns[state.turns.length - 1];
  const percent = state.attempt !== null && state.budget > 0 ? Math.min(100, Math.round(state.attempt / state.budget * 100)) : null;
  const statusText = state.stopState === 'requested' && !finished ? 'Stopping…' : state.status.replace(/_/g, ' ').toLowerCase().replace(/^./, value => value.toUpperCase());
  const current = finished ? `Assessment ${state.status.toLowerCase()}` : state.stopState === 'requested' ? 'Waiting for a safe stop boundary' : state.status === 'QUEUED' ? 'Waiting for execution' : state.statusError ? 'Awaiting engine connection' : latest?.event === 'turn_started' ? `Prompt ${latest.attempt} · awaiting response or evaluation` : state.attempt ? `Attempt ${state.attempt} reported by engine` : 'Waiting for execution details';
  const latencies = completed.map(turn => turn.latency_ms).filter((value): value is number => typeof value === 'number' && Number.isFinite(value) && value > 0);
  const average = latencies.length ? latency(latencies.reduce((sum, value) => sum + value, 0) / latencies.length) : 'Unavailable';
  const evaluated = completed.filter(turn => typeof turn.verdict?.exploited === 'boolean');
  const leaks = evaluated.length ? `${evaluated.filter(turn => turn.verdict?.exploited).length} / ${evaluated.length} evaluated` : 'Unavailable';
  function tabKey(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    const next = event.key === 'ArrowRight' ? (index + 1) % tabs.length : event.key === 'ArrowLeft' ? (index + tabs.length - 1) % tabs.length : event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : null;
    if (next === null) return;
    event.preventDefault(); setTab(next); document.getElementById(`execution-tab-${next}`)?.focus();
  }
  return <div className="execution-page">
    <section className="execution-primary" aria-label="Live scan execution">
      <header className="execution-heading"><div><div className="execution-breadcrumb">Assessment <ChevronRight size={14}/><span>{targetName}</span><ChevronRight size={14}/><strong>Live Scan</strong></div><div className="execution-title"><h1>Scanning: {targetName}</h1><span className={`execution-badge ${state.status === 'FAILED' ? 'danger' : finished ? 'neutral' : 'accent'}`} role="status">{statusText}{!state.confirmed && ' · last known'}</span></div></div><div className="execution-controls"><button className="button secondary" onClick={state.refresh} disabled={state.loading} aria-label="Refresh scan status"><Radio size={16} aria-hidden="true"/> Refresh status</button><button className="button secondary" onClick={() => void state.stop()} disabled={finished || !state.confirmed || state.stopState !== 'idle'}>{state.stopState === 'sending' ? <LoaderCircle size={16} className="spin"/> : <Square size={15}/>} {state.stopState === 'sending' ? 'Requesting…' : state.stopState === 'requested' && !finished ? 'Stopping…' : 'Stop'}</button></div></header>
      <div className="execution-progress-label"><p>Testing for {scan.category} — System Prompt Leakage</p><span>{state.attempt ?? '—'} / {state.budget || '—'} attempts</span></div>
      <progress className="execution-progress" aria-label="Attempt budget progress" max={100} value={percent ?? undefined}/><div className="execution-progress-foot"><span>{state.attempt === null ? 'Waiting for progress data' : 'Attempt progress · not a security verdict'}</span><strong>{percent === null ? '—' : `${percent}%`}</strong></div>
      {(state.statusError || state.turnError || state.stopError) && <div className="execution-errors" role="alert">{state.statusError && <p>Status unavailable: {state.statusError} Last known state is retained.</p>}{state.turnError && <p>{state.turnError}</p>}{state.stopError && <p>Stop failed: {state.stopError}</p>}</div>}
      <div className="execution-tabs" role="tablist" aria-label="Scan information">{tabs.map((label, index) => <button key={label} id={`execution-tab-${index}`} role="tab" aria-selected={tab === index} aria-controls="execution-tab-panel" tabIndex={tab === index ? 0 : -1} onClick={() => setTab(index)} onKeyDown={event => tabKey(event, index)}>{label}</button>)}</div>
      <div className="execution-main-grid"><div id="execution-tab-panel" role="tabpanel" aria-labelledby={`execution-tab-${tab}`}>
        {tab === 0 && <ActivityConsole state={state}/>}
        {tab === 1 && <div className="execution-unavailable"><Info size={28}/><h2>Agent reasoning is unavailable</h2><p>The engine does not expose an agent reasoning stream. Supplied evaluation rationale appears with the recorded turns in Evidence.</p><button className="button secondary" onClick={() => setTab(3)}>View available evidence</button></div>}
        {tab === 2 && <Transcript turns={state.turns} evidence={false} finished={finished}/>}
        {tab === 3 && <Transcript turns={state.turns} evidence finished={finished}/>}
      </div><aside className="execution-step-card"><h2>Current Step</h2><div className="execution-current"><Activity size={22}/><div><strong>{current}</strong><p>{finished ? 'Review the available transcript and turn evidence.' : 'Only reported activity is shown; detailed phase timing is unavailable.'}</p></div></div>
        {[['Attack Generation', latest?.prompt ? 'Prompt available for latest recorded attempt' : 'No generation phase reported'], ['Execution', latest?.event === 'turn_started' && !finished ? 'Awaiting response or evaluation' : completed.length ? `${completed.length} recorded turn${completed.length === 1 ? '' : 's'}` : 'No execution detail reported'], ['Analysis', latest?.verdict ? 'Evaluation supplied for latest recorded turn' : 'No evaluation phase reported']].map(([title, detail], index) => <div className="execution-phase" key={title}><span>{index + 1}</span><div><strong>{title}</strong><p>{detail}</p></div></div>)}
        <p className="execution-connection" role="status">Telemetry: {state.connection === 'closed' ? 'ended' : state.connection}{state.connection === 'disconnected' ? ' · reconnecting; status polling continues' : ''}</p>
      </aside></div>
    </section>
    <div className="execution-lower-grid"><section className="execution-card execution-tests"><header><h2>Test Case Progress</h2><span>{completed.length} recorded / {state.budget || '—'} budget</span></header>
      <div className="execution-test-list" tabIndex={0} role="region" aria-label="Recorded test attempts">{state.turns.length ? state.turns.map(turn => <div className="execution-test-row" key={turn.attempt}><span className="execution-attempt">{turn.attempt}</span><div><strong>Prompt {turn.attempt}</strong><small>{turn.strategy || 'Strategy not supplied'}</small></div><span>{turn.event === 'turn_completed' ? <Check size={14}/> : <Clock3 size={14}/>} {turn.event === 'turn_completed' ? 'Recorded' : finished ? 'Incomplete' : 'In progress'}</span><small>{latency(turn.latency_ms)}</small></div>) : <p className="execution-muted">{finished ? 'No recorded turns returned for this assessment.' : 'No test attempts reported yet.'} Test names and future cases are not supplied by the engine.</p>}</div>
      <button className="execution-text-button" onClick={() => { setTab(2); document.getElementById('execution-tab-2')?.focus(); }}>View requests & responses <ChevronRight size={16}/></button>
    </section><section className="execution-card"><h2>Target Information</h2><dl className="execution-facts"><div><Globe2 size={20}/><dt>Target</dt><dd>{targetName}</dd></div><div><Shield size={20}/><dt>Assessment Type</dt><dd>{scan.category} — System Prompt Leakage</dd></div><div><Globe2 size={20}/><dt>Application URL</dt><dd>{targetUrl || 'Unavailable'}</dd></div><div><Info size={20}/><dt>Interface</dt><dd>Browser-based (Playwright)</dd></div></dl><small className="execution-id">Scan ID: {scan.scan_id}</small></section>
      <section className="execution-card"><h2>Live Metrics</h2><dl className="execution-metrics">{[[Zap, 'Attempt progress', `${state.attempt ?? '—'} / ${state.budget || '—'}`], [Clock3, 'Average response time', average], [Shield, 'Potential leaks', leaks], [FileText, 'Findings generated', 'Unavailable'], [Activity, 'Scan duration', 'Unavailable']].map(([Icon, label, value]) => { const MetricIcon = Icon as typeof Activity; return <div key={String(label)}><MetricIcon size={18}/><dt>{String(label)}</dt><dd>{String(value)}</dd></div>; })}</dl><p className="execution-metric-note">Metrics use available turns only. Missing or zero latency is excluded. Findings totals and scan duration are not supplied.</p></section>
    </div>
  </div>;
}
