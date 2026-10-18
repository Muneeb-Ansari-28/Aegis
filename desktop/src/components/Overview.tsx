import { useState } from 'react';
import { ArrowRight, Bot, CheckCircle2, Circle, FileText, Settings2, Cpu, TerminalSquare, History, LoaderCircle, Plus, Radio, ScanLine, Shield } from 'lucide-react';
import type { ScanRecord } from '../api/client';
import type { AppPage } from './ApplicationShell';
import './overview.css';
const securityArtwork = new URL('../assets/security-dashboard.svg', import.meta.url).href;

type HistoryEntry = ScanRecord & { targetName?: string; createdAt: string };
interface OverviewProps {
  history: HistoryEntry[];
  activeScan: ScanRecord | null;
  onNavigate: (page: AppPage) => void;
  engineOnline: boolean | null;
  ollamaOnline: boolean | null;
  profileName: string;
  onRefresh: () => Promise<void>;
}

/** Format recorded request dates without manufacturing missing timestamps. */
function recordedDate(value?: string, compact = false) {
  const date = new Date(value || '');
  return Number.isNaN(date.getTime()) ? 'Unavailable' : compact
    ? date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
    : date.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
}

/** Present existing local history and health signals; never initiate scanner operations. */
export default function Overview({ history, activeScan, onNavigate, engineOnline, ollamaOnline, profileName, onRefresh }: OverviewProps) {
  const [refreshing, setRefreshing] = useState(false);
  const greeting = new Date().getHours() < 12 ? 'Good morning' : new Date().getHours() < 18 ? 'Good afternoon' : 'Good evening';
  const checking = engineOnline === null;
  const metrics = [
    { label: 'Total scans', value: String(history.length), note: 'Local history · up to 100', Icon: ScanLine, tone: 'accent' },
    { label: 'Running', value: String(history.filter(scan => ['RUNNING', 'SCANNING'].includes(scan.status.toUpperCase())).length), note: 'Last known · local history', Icon: Circle, tone: 'warning' },
    { label: 'Completed', value: String(history.filter(scan => scan.status.toUpperCase() === 'COMPLETED').length), note: 'Last known · local history', Icon: CheckCircle2, tone: 'success' },
    { label: 'Vulnerabilities', value: '—', note: 'Not available yet', Icon: Shield, tone: 'danger' },
  ];
  const services = [
    { name: 'Engine', detail: checking ? 'Checking connection…' : engineOnline ? 'Connected' : 'Offline', note: 'Local scanning service', Icon: checking ? LoaderCircle : Settings2, tone: checking ? 'neutral' : engineOnline ? 'success' : 'danger' },
    { name: 'Ollama', detail: checking || ollamaOnline === null ? 'Checking connection…' : !engineOnline ? 'Unavailable' : ollamaOnline ? 'Connected' : 'Disconnected', note: !engineOnline && !checking ? 'Engine connection required' : 'Model readiness is not checked', Icon: Cpu, tone: engineOnline && ollamaOnline ? 'success' : 'neutral' },
    { name: 'Playwright', detail: 'Not checked', note: 'Verified during target calibration', Icon: TerminalSquare, tone: 'neutral' },
  ];

  /** Reuse the existing health refresh, guarding repeat dashboard clicks. */
  async function refreshHealth() {
    if (refreshing) return;
    setRefreshing(true);
    try { await onRefresh(); } finally { setRefreshing(false); }
  }

  return <div className="page-content dashboard"><div className="dashboard-workspace">
    <div className="dashboard-heading">
      <div><h1>{greeting}, {profileName}</h1><p>Let's secure your LLM applications.</p></div>
    </div>

    <div className="dashboard-metrics" aria-label="Assessment summary">
      {metrics.map(({ label, value, note, Icon, tone }) => <section className="dashboard-metric" key={label} aria-label={label}>
        <span className={`dashboard-icon ${tone}`}><Icon size={19} aria-hidden="true" /></span>
        <div><strong className="dashboard-value">{value}</strong><h2>{label}</h2><p title={note}>{note}</p></div>
      </section>)}
    </div>

    <div className="dashboard-columns">
      <section className="dashboard-panel dashboard-recent" aria-labelledby="recent-heading">
        <div className="dashboard-panel-heading"><div><h2 id="recent-heading">Recent Assessments</h2></div><button className="dashboard-link" onClick={() => onNavigate('history')}>View all <ArrowRight size={15} aria-hidden="true" /></button></div>

          <div className="dashboard-table-scroll" tabIndex={0} role="region" aria-label="Recent assessments table">
            <table className="dashboard-table"><thead><tr><th scope="col">Name</th><th scope="col">Category</th><th scope="col">Status</th><th scope="col">Started</th><th scope="col">Findings</th></tr></thead>
              <tbody>{history.slice(0, 4).map(scan => {
                const status = scan.status.toUpperCase();
                const tone = status === 'COMPLETED' ? 'success' : status === 'FAILED' ? 'danger' : ['RUNNING', 'SCANNING', 'QUEUED'].includes(status) ? 'accent' : 'neutral';
                return <tr key={scan.scan_id}><th scope="row">{activeScan?.scan_id === scan.scan_id ? <button className="dashboard-link dashboard-target" aria-label={`Open selected scan for ${scan.targetName || 'unnamed target'}`} onClick={() => onNavigate('live')}>{scan.targetName || 'Unnamed target'}</button> : <span className="dashboard-target" title={scan.targetName || scan.target_id}>{scan.targetName || 'Unnamed target'}</span>}</th><td>{scan.category}</td><td><span className={`dashboard-badge ${tone}`}>{scan.status.replace(/_/g, ' ') || 'Unknown'}</span></td><td>{recordedDate(scan.createdAt)}</td><td><span className="dashboard-muted" title="Aggregate findings unavailable" aria-label="Findings unavailable">—</span></td></tr>;
              })}</tbody>
            </table>
          </div>
        {history.length > 0 ? <p className="dashboard-footnote">Local history · last known statuses. Started shows request time. Completed is not a security verdict.</p> : <div className="dashboard-empty"><span className="dashboard-empty-icon"><FileText size={28} aria-hidden="true" /></span><h3>No assessments yet</h3><p>Start with an authorized web target to see your assessment requests here.</p><button className="button dashboard-outline" onClick={() => onNavigate('scan')}><Plus size={18} aria-hidden="true" />New assessment</button></div>}

      </section>

      <section className="dashboard-panel dashboard-health" aria-labelledby="health-heading">
        <div className="dashboard-panel-heading"><h2 id="health-heading">System Status</h2><button className="icon-button" aria-label="Refresh system health" disabled={refreshing} onClick={() => void refreshHealth()}><Radio size={18} aria-hidden="true" /></button></div>
        <div aria-live="polite" aria-busy={checking || refreshing}>
          {services.map(({ name, detail, note, Icon, tone }) => <div className="dashboard-service" key={name} title={note}><span className={`dashboard-service-icon ${tone}`}><Icon size={18} aria-hidden="true" /></span><div><h3>{name}</h3><p className={`dashboard-service-state ${tone}`}><span aria-hidden="true"/>{detail}</p><small>{note}</small></div></div>)}
          {refreshing && <p className="dashboard-footnote">Refreshing connections…</p>}
        </div>
        <button className="dashboard-link" onClick={() => onNavigate('profile')}>View settings <ArrowRight size={15} aria-hidden="true" /></button>
      </section>
    </div>

    </div>
    <aside className="dashboard-context" aria-label="Assessment scope">
      <img className="dashboard-art" src={securityArtwork} alt="" aria-hidden="true"/>
      <h2>AI Security Testing<br/>for LLM Applications</h2>
      <p>Assess authorized targets for system prompt leakage. Review the evidence behind each response.</p>
      <ul><li><CheckCircle2 size={15}/>Focused OWASP LLM07 testing</li><li><CheckCircle2 size={15}/>Web target calibration</li><li><CheckCircle2 size={15}/>Prompt and response evidence</li><li><CheckCircle2 size={15}/>Browser-local request history</li></ul>
      <p className="dashboard-context-note"><Shield size={15}/>Only test systems you own or have permission to assess.</p>
    </aside>
    <section className="dashboard-panel dashboard-actions" aria-labelledby="actions-heading"><div className="dashboard-panel-heading"><div><h2 id="actions-heading">Quick Actions</h2><p>Common tasks to get started quickly.</p></div></div>
      <div className="dashboard-action-grid">
        {[{ title: 'Start an assessment', text: 'Configure a target and run a scan.', Icon: Plus, page: 'scan' as const }, { title: 'View scan history', text: 'Review past requests and statuses.', Icon: History, page: 'history' as const }, { title: 'Get setup guidance', text: 'Get help with target configuration.', Icon: Bot, page: 'assistant' as const }].map(({ title, text, Icon, page }) => <button className="dashboard-action" key={page} onClick={() => onNavigate(page)}><span className="dashboard-icon accent"><Icon size={19} aria-hidden="true" /></span><span><strong>{title}</strong><small>{text}</small></span><ArrowRight size={16} aria-hidden="true" /></button>)}
      </div>
    </section>
  </div>;
}
