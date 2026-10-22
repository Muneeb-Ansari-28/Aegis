import { useCallback, useEffect, useRef, useState } from 'react';
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Download,
  FileText,
  Globe2,
  Info,
  LoaderCircle,
  RefreshCw,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Terminal,
} from 'lucide-react';
import { api, type ScanTurn } from '../api/client';
import type { FindingDetail, FindingResponse, FindingsSummary } from '../types';
import './findings-inspector.css';

interface FindingsInspectorProps {
  scanId?: string;
  history?: Array<{
    scan_id: string;
    targetName?: string;
    createdAt: string;
    status: string;
    category: string;
  }>;
  onSelectScan?: (scanId: string) => void;
  onNavigate?: (page: any) => void;
  onExportPdf?: (scanId: string) => void;
}

type TabType = 'overview' | 'findings' | 'evidence' | 'timeline';

export default function FindingsInspector({
  scanId: initialScanId,
  history = [],
  onSelectScan,
  onNavigate,
  onExportPdf,
}: FindingsInspectorProps) {
  const [selectedScanId, setSelectedScanId] = useState<string | null>(
    initialScanId || history[0]?.scan_id || null
  );
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const requestVersion = useRef(0);
  const [findingsAvailable, setFindingsAvailable] = useState(false);
  const [turnsAvailable, setTurnsAvailable] = useState(false);
  const [detailErrors, setDetailErrors] = useState<Record<string, string>>({});
  const [summary, setSummary] = useState<FindingsSummary | null>(null);
  const [findings, setFindings] = useState<FindingResponse[]>([]);
  const [turns, setTurns] = useState<ScanTurn[]>([]);
  const [findingDetails, setFindingDetails] = useState<Record<string, FindingDetail>>({});
  const [expandedFindingIds, setExpandedFindingIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState<boolean>(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [exportSuccess, setExportSuccess] = useState<boolean>(false);

  // Sync external scanId changes
  useEffect(() => {
    if (initialScanId && initialScanId !== selectedScanId) {
      setSelectedScanId(initialScanId);
    }
  }, [initialScanId]);

  const loadScanData = useCallback(async (id: string) => {
    const version = ++requestVersion.current;
    setLoading(true);
    setSummary(null); setFindings([]); setTurns([]);
    setFindingsAvailable(false); setTurnsAvailable(false);
    setExpandedFindingIds(new Set()); setExportSuccess(false); setExportError(null);
    setError(null);
    try {
      const [summaryRes, findingsRes, turnsRes] = await Promise.allSettled([
        api.findingsSummary(id),
        api.findings(id),
        api.scanTurns(id),
      ]);

      if (version !== requestVersion.current) return;
      setFindingsAvailable(findingsRes.status === 'fulfilled');
      setTurnsAvailable(turnsRes.status === 'fulfilled');
      if (summaryRes.status === 'fulfilled') {
        setSummary(summaryRes.value);
      } else {
        setSummary(null);
      }

      if (findingsRes.status === 'fulfilled') {
        setFindings(findingsRes.value);
        // Automatically expand the first finding if present
        if (findingsRes.value.length > 0) {
          const firstId = findingsRes.value[0].id;
          setExpandedFindingIds(new Set([firstId]));
          // Preload its detail
          void loadFindingDetail(firstId);
        }
      } else {
        setFindings([]);
      }

      if (turnsRes.status === 'fulfilled') {
        setTurns(turnsRes.value);
      } else {
        setTurns([]);
      }

      const unavailable = [summaryRes.status === 'rejected' && 'assessment metadata', findingsRes.status === 'rejected' && 'findings', turnsRes.status === 'rejected' && 'turn evidence'].filter(Boolean);
      if (unavailable.length) setError(`Unable to load ${unavailable.join(', ')}. Available results are shown; refresh to retry.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load assessment findings.');
    } finally {
      if (version === requestVersion.current) setLoading(false);
    }
  }, []);

  const loadFindingDetail = async (findingId: string) => {
    if (findingDetails[findingId]) return;
    setDetailErrors(prev => ({ ...prev, [findingId]: "" }));
    try {
      const detail = await api.findingDetail(findingId);
      setFindingDetails(prev => ({ ...prev, [findingId]: detail }));
    } catch {
      setDetailErrors(prev => ({ ...prev, [findingId]: "Evidence could not be loaded. Close and reopen this finding to retry." }));
    }
  };

  useEffect(() => {
    if (selectedScanId) {
      void loadScanData(selectedScanId);
    }
    return () => { requestVersion.current += 1; };
  }, [selectedScanId, loadScanData]);

  const toggleExpand = (findingId: string) => {
    setExpandedFindingIds(prev => {
      const next = new Set(prev);
      if (next.has(findingId)) {
        next.delete(findingId);
      } else {
        next.add(findingId);
        void loadFindingDetail(findingId);
      }
      return next;
    });
  };

  const handleScanChange = (id: string) => {
    setSelectedScanId(id);
    onSelectScan?.(id);
  };

  const handleExport = async () => {
    if (!selectedScanId) return;
    setExporting(true);
    setExportError(null);
    setExportSuccess(false);
    try {
      if (onExportPdf) {
        onExportPdf(selectedScanId);
      } else {
        await api.downloadReport(selectedScanId);
      }
      setExportSuccess(true);
      window.setTimeout(() => setExportSuccess(false), 3500);
    } catch (err: unknown) {
      console.error('PDF export failed:', err);
      const msg = err instanceof Error ? err.message : 'Failed to download report PDF';
      setExportError(msg);
    } finally {
      setExporting(false);
    }
  };

  // Helper for severity styling
  const severityClass = (sev: string) => {
    const s = (sev || 'info').toLowerCase();
    return `severity-badge ${s}`;
  };

  if (!selectedScanId && history.length === 0) {
    return (
      <div className="page-content findings-page">
        <div className="page-heading">
          <div>
            <div className="eyebrow">ASSESSMENT FINDINGS</div>
            <h1>Findings & Results</h1>
            <p>Review vulnerabilities, evidence pairs, and remediation guidelines.</p>
          </div>
        </div>
        <div className="dashboard-panel dashboard-empty">
          <span className="dashboard-empty-icon">
            <FileText size={28} aria-hidden="true" />
          </span>
          <h3>No assessments recorded</h3>
          <p>Run a web assessment first to inspect vulnerabilities and export PDF reports.</p>
          {onNavigate && (
            <button className="button primary" onClick={() => onNavigate('scan')}>
              New assessment
            </button>
          )}
        </div>
      </div>
    );
  }

  const currentScanHistory = history.find(h => h.scan_id === selectedScanId);
  const targetName = summary?.target_name || currentScanHistory?.targetName || 'Local target';
  const scanStatus = (summary?.scan_status || currentScanHistory?.status || 'UNKNOWN').toUpperCase();
  const riskGrade = summary ? Math.round(summary.risk_grade) : null;
  const evaluatedTurns = turns.filter(turn => turn.verdict && (!turn.status || turn.status === 'success'));
  const durationMs = summary?.started_at && summary?.completed_at ? Date.parse(summary.completed_at) - Date.parse(summary.started_at) : NaN;
  const duration = Number.isFinite(durationMs) && durationMs >= 0 ? `${Math.floor(durationMs / 60000)} min ${Math.floor(durationMs / 1000) % 60} sec` : 'Unavailable';
  const formatDate = (value?: string | null) => {
    if (!value) return 'Unavailable';
    const date = new Date(/(?:Z|[+-]\d{2}:\d{2})$/.test(value) ? value : `${value}Z`);
    return Number.isNaN(date.getTime()) ? 'Unavailable' : date.toLocaleString();
  };
  const turnOutcome = (turn: ScanTurn) => turn.status === 'error' || turn.status === 'timeout' ? 'Not evaluated' : !turn.verdict ? 'Not evaluated' : turn.verdict.exploited ? 'Disclosure detected' : 'No disclosure detected';
  const successfulTurns = turns.filter(turn => !turn.status || turn.status === 'success');
  const averageLatency = successfulTurns.length ? `${(successfulTurns.reduce((sum, turn) => sum + turn.latency_ms, 0) / successfulTurns.length / 1000).toFixed(1)}s` : 'Unavailable';
  const isScanRunning = ['RUNNING', 'SCANNING', 'QUEUED'].includes(scanStatus);

  return (
    <div className="page-content findings-page">
      {/* Top Header */}
      <div className="findings-topbar">
        <div>
          <div className="results-breadcrumb">Assessment <ChevronRight size={14} /> {targetName} <ChevronRight size={14} /> <strong>Results</strong></div>
          <h1>Assessment Results</h1>
          <div className="findings-meta-badges">
            <span className={`scan-status ${scanStatus.toLowerCase()}`}>
              {scanStatus.replace(/_/g, ' ')}
            </span>
            <span>{targetName} · {summary?.scan_category || currentScanHistory?.category || "Category unavailable"} - System Prompt Leakage</span>
            <span>{turnsAvailable ? `${turns.length} recorded turns` : "Turn count unavailable"} · {duration}</span>

          </div>
        </div>

        <div className="scan-selector-wrapper">
          {history.length > 1 && (
            <select
              className="scan-selector-select"
              value={selectedScanId || ''}
              onChange={e => handleScanChange(e.target.value)}
              aria-label="Select scan to inspect"
            >
              {history.map(item => (
                <option key={item.scan_id} value={item.scan_id}>
                  {item.targetName || 'Target'} ({item.scan_id.slice(0, 8)})
                </option>
              ))}
            </select>
          )}

          <button
            className="button primary"
            onClick={handleExport}
            disabled={exporting || loading || isScanRunning || !summary || !['COMPLETED', 'STOPPED', 'FAILED'].includes(scanStatus)}
            title={isScanRunning ? "Report available after scan completes" : "Export assessment report as PDF"}
            aria-label="Export assessment report as PDF"
          >
            {exporting ? (
              <>
                <LoaderCircle size={15} className="spin" />
                <span>Exporting...</span>
              </>
            ) : exportSuccess ? (
              <>
                <CheckCircle2 size={15} />
                <span>Downloaded</span>
              </>
            ) : (
              <>
                <Download size={15} />
                <span>Export PDF</span>
              </>
            )}
          </button>

          <button
            className="button secondary"
            onClick={() => selectedScanId && void loadScanData(selectedScanId)}
            title="Refresh findings data"
            aria-label="Refresh"
            disabled={loading}
          >
            <RefreshCw size={14} className={loading ? 'spin' : ''} />
          </button>
        </div>
      </div>

      {/* Export Error Notice */}
      {exportError && (
        <div className="error-box" role="alert">
          <AlertTriangle size={15} />
          <span>Export failed: {exportError}</span>
          <button
            className="button secondary"
            style={{ marginLeft: 'auto', padding: '0.2rem 0.6rem', fontSize: '0.8rem' }}
            onClick={() => void handleExport()}
          >
            Retry
          </button>
        </div>
      )}

      {/* Error Notice */}
      {error && (
        <div className="error-box" role="alert">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* Tab Navigation */}
      <nav className="findings-tabs-nav" aria-label="Findings sections">
        <button
          className={`findings-tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
          aria-pressed={activeTab === 'overview'}
        >
          <Shield size={16} />
          <span>Overview</span>
        </button>

        <button
          className={`findings-tab-btn ${activeTab === 'findings' ? 'active' : ''}`}
          onClick={() => setActiveTab('findings')}
          aria-pressed={activeTab === 'findings'}
        >
          <ShieldAlert size={16} />
          <span>Findings</span>
          <span className="findings-tab-badge">{findingsAvailable ? findings.length : "Unavailable"}</span>
        </button>

        <button
          className={`findings-tab-btn ${activeTab === 'evidence' ? 'active' : ''}`}
          onClick={() => setActiveTab('evidence')}
          aria-pressed={activeTab === 'evidence'}
        >
          <Terminal size={16} />
          <span>Evidence</span>
          <span className="findings-tab-badge">{turnsAvailable ? turns.length : "Unavailable"}</span>
        </button>

        <button
          className={`findings-tab-btn ${activeTab === 'timeline' ? 'active' : ''}`}
          onClick={() => setActiveTab('timeline')}
          aria-pressed={activeTab === 'timeline'}
        >
          <Clock size={16} />
          <span>Timeline</span>
        </button>
      </nav>

      {/* Loading Skeleton */}
      {loading && !summary && (
        <div className="dashboard-panel" style={{ textAlign: 'center', padding: '3rem' }}>
          <LoaderCircle size={28} className="spin" style={{ margin: '0 auto 1rem', color: 'var(--color-accent)' }} />
          <p>Loading assessment findings and evidence…</p>
        </div>
      )}

      {/* Overview follows the approved Results composition; all values come from persisted APIs. */}
      {activeTab === 'overview' && (
        <>
          <div className="results-statistics" aria-label="Assessment summary" aria-busy={loading}>
            {[
              ['Prompts Evaluated', turnsAvailable ? evaluatedTurns.length : '—', 'success'],
              ['Vulnerabilities', findingsAvailable ? findings.length : '—', 'danger'],
              ['Critical', summary?.by_severity.CRITICAL ?? '—', 'danger'],
              ['High', summary?.by_severity.HIGH ?? '—', 'danger'],
              ['Medium', summary?.by_severity.MEDIUM ?? '—', 'warning'],
              ['Low', summary?.by_severity.LOW ?? '—', 'muted'],
            ].map(([label, value, tone]) => <div className="results-statistic" key={label}><strong className={`results-${tone}`}>{loading ? '—' : value}</strong><span>{label}</span></div>)}
          </div>
          <div className="results-columns">
            <div className="results-primary">
              <section className="results-panel">
                <div className="results-panel-heading"><h2>Key Findings</h2><button className="dashboard-link" onClick={() => setActiveTab('findings')}>View all <ChevronRight size={14}/></button></div>
                {findingsAvailable && findings.length ? findings.slice(0, 3).map(finding => (
                  <button className="results-finding" key={finding.id} onClick={() => { setActiveTab('findings'); setExpandedFindingIds(new Set([finding.id])); void loadFindingDetail(finding.id); }}>
                    <AlertCircle size={22} className={finding.severity === 'MEDIUM' ? 'results-warning' : 'results-danger'} />
                    <span className="results-finding-text"><strong>{finding.description}</strong><small>Confidence: {Math.round(finding.confidence * 100)}% - Inspect linked evidence</small></span>
                    <span className={severityClass(finding.severity)}>{finding.severity}</span><span className="table-category">{finding.category}</span><ChevronRight size={16}/>
                  </button>
                )) : <div className="results-empty"><ShieldCheck size={24}/><strong>{loading ? 'Loading findings...' : findingsAvailable ? 'No findings recorded' : 'Findings unavailable'}</strong><p>{scanStatus === 'COMPLETED' ? 'Results apply only to evaluated turns within this assessment scope.' : 'This assessment may be incomplete. No findings does not establish that the target is secure.'}</p></div>}
              </section>
              <section className="results-panel">
                <div className="results-panel-heading"><h2>Test Case Summary</h2><button className="dashboard-link" onClick={() => setActiveTab('evidence')}>View all recorded turns</button></div>
                <div className="results-table-scroll" tabIndex={0} aria-label="Recorded test cases">
                  <table className="results-table"><thead><tr><th>#</th><th>Test Case</th><th>Status</th><th>Response Time</th><th>Result</th></tr></thead><tbody>
                    {turns.slice(0, 5).map(turn => <tr key={turn.turn_index}><td>{turn.turn_index}</td><td><span className="results-test-name" title={turn.prompt}>{turn.strategy || `Prompt ${turn.turn_index}`}</span></td><td>{turn.status === 'error' || turn.status === 'timeout' ? turn.status : turn.verdict ? 'Evaluated' : 'Not evaluated'}</td><td>{(turn.latency_ms / 1000).toFixed(1)}s</td><td className={turn.verdict?.exploited ? 'results-danger' : turn.verdict ? 'results-success' : ''}>{turnOutcome(turn)}</td></tr>)}
                  </tbody></table>
                  {!turns.length && <p className="results-empty-line">{loading ? 'Loading recorded turns...' : turnsAvailable ? 'No turns recorded for this assessment.' : 'Turn evidence unavailable.'}</p>}
                </div>
                <button className="results-evidence-link" onClick={() => setActiveTab('evidence')}><FileText size={18}/>View requests & responses<ChevronRight size={16}/></button>
              </section>
            </div>
            <aside className="results-secondary">
              <section className="results-panel"><h2>Assessment Information</h2><dl className="results-details">
                {[[Globe2, 'Target', targetName], [Shield, 'Assessment Type', summary?.scan_category || currentScanHistory?.category || 'Unavailable'], [Clock, 'Started At', formatDate(summary?.started_at)], [Clock, 'Completed At', formatDate(summary?.completed_at)], [Clock, 'Duration', duration], [Globe2, 'Application URL', summary?.target_url || 'Unavailable'], [Info, 'Outcome', scanStatus.replace(/_/g, ' ')]].map(([Icon, label, value]) => {
                  const RowIcon = Icon as typeof Globe2;
                  return <div key={String(label)}><dt><RowIcon size={17}/>{String(label)}</dt><dd>{String(value)}</dd></div>;
                })}
              </dl></section>
              <section className="results-panel"><h2>Assessment Metrics</h2><dl className="results-details">
                <div><dt><Terminal size={17}/>Recorded Turns</dt><dd>{turnsAvailable ? turns.length : 'Unavailable'}</dd></div>
                <div><dt><Clock size={17}/>Average Response Time</dt><dd>{averageLatency}</dd></div>
                <div><dt><ShieldAlert size={17}/>Positive Evaluations</dt><dd>{turnsAvailable ? evaluatedTurns.filter(turn => turn.verdict?.exploited).length : 'Unavailable'}</dd></div>
                <div><dt><FileText size={17}/>Findings Recorded</dt><dd>{findingsAvailable ? findings.length : 'Unavailable'}</dd></div>
                <div><dt><Shield size={17}/>Backend Risk Grade</dt><dd>{riskGrade !== null ? `${riskGrade} / 100` : 'Unavailable'}</dd></div>
              </dl><p className="results-note">Grade reflects recorded findings, not proof of security or complete coverage.</p></section>
            </aside>
          </div>
          <p className="results-note">Scope: OWASP LLM08 - Hidden Context Exposure. Other categories were not tested. Only persisted turns are shown; unused budget is not a pending test case.</p>
        </>
      )}

      {/* Tab 2: Findings List */}
      {activeTab === 'findings' && (
        <div className="findings-list">
          {findings.length === 0 ? (
            <div className="dashboard-panel" style={{ textAlign: 'center', padding: '3rem' }}>
              <ShieldCheck size={36} style={{ color: 'var(--color-text-secondary)', margin: '0 auto 1rem' }} />
              <h3 style={{ marginBottom: '0.5rem' }}>{loading ? "Loading findings..." : findingsAvailable ? "No findings recorded for this scan" : "Findings unavailable"}</h3>
              <p style={{ color: 'var(--color-text-secondary)', maxWidth: '520px', margin: '0 auto' }}>
                No findings are available in this view. Check the assessment outcome and evidence before drawing conclusions.
              </p>
            </div>
          ) : (
            findings.map(finding => {
              const isExpanded = expandedFindingIds.has(finding.id);
              const detail = findingDetails[finding.id];

              return (
                <div key={finding.id} className="finding-card">
                  <div
                    className="finding-card-header"
                    onClick={() => toggleExpand(finding.id)}
                    onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleExpand(finding.id); } }}
                    tabIndex={0}
                    role="button"
                    aria-expanded={isExpanded}
                  >
                    <div className="finding-title-group">
                      <span className="finding-category-tag">OWASP {finding.category}</span>
                      <h3 className="finding-title">{finding.description}</h3>
                      <p className="finding-description">
                        Confidence: {Math.round(finding.confidence * 100)}% · Turn reference: {finding.turn_id.slice(0, 8)}
                      </p>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
                      <span className={severityClass(finding.severity)}>{finding.severity}</span>
                      {isExpanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="finding-card-details">
                      {detail ? (
                        <>
                          <div className="evidence-section">
                            <span className="evidence-section-label">
                              <Terminal size={13} />
                              Trigger Prompt (Turn #{detail.turn_index})
                            </span>
                            <pre className="evidence-console">{detail.prompt}</pre>
                          </div>

                          <div className="evidence-section">
                            <span className="evidence-section-label">
                              <Terminal size={13} />
                              Target Model Response ({detail.latency_ms} ms)
                            </span>
                            <pre className="evidence-console">{detail.response}</pre>
                          </div>

                          {detail.remediation && (
                            <div className="evidence-remediation-box">
                              <strong>Remediation Guidance:</strong> {detail.remediation}
                            </div>
                          )}
                        </>
                      ) : (
                        <div style={{ padding: '1rem', textAlign: 'center' }}>
                          {!detailErrors[finding.id] && <LoaderCircle size={18} className="spin" style={{ margin: '0 auto' }} />}
                          <small>{detailErrors[finding.id] || "Loading evidence details..."}</small>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      )}

      {/* Tab 3: Evidence (Turn-by-turn Replay) */}
      {activeTab === 'evidence' && (
        <div className="transcript-flow">
          {turns.length === 0 ? (
            <div className="dashboard-panel" style={{ textAlign: 'center', padding: '3rem' }}>
              <p>{loading ? "Loading evidence..." : turnsAvailable ? "No turns recorded for this assessment." : "Turn evidence unavailable. Refresh to retry."}</p>
            </div>
          ) : (
            turns.map(turn => (
              <div key={turn.turn_index} className="turn-replay-card">
                <div className="turn-replay-header">
                  <strong>Attempt #{turn.turn_index} · {turn.strategy || 'LLM08'}</strong>
                  <span className="dashboard-muted">{turn.latency_ms} ms</span>
                </div>

                <div className="evidence-section">
                  <span className="evidence-section-label">Prompt</span>
                  <pre className="evidence-console">{turn.prompt}</pre>
                </div>

                <div className="evidence-section">
                  <span className="evidence-section-label">{turn.status === "error" || turn.status === "timeout" ? "Connector diagnostic - not evaluated" : "Chatbot Response"}</span>
                  <pre className="evidence-console">{turn.response || '(No response text returned)'}</pre>
                </div>

                {turn.verdict && (!turn.status || turn.status === "success") && (
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                      padding: '0.5rem 0.75rem',
                      borderRadius: 'var(--radius-control)',
                      fontSize: '0.8125rem',
                      backgroundColor: turn.verdict.exploited ? 'var(--color-danger-bg)' : 'var(--color-success-bg)',
                      color: turn.verdict.exploited ? 'var(--color-danger-text)' : 'var(--color-success-text)',
                    }}
                  >
                    {turn.verdict.exploited ? <AlertTriangle size={15} /> : <CheckCircle2 size={15} />}
                    <strong>
                      {turn.verdict.exploited ? 'Potential prompt disclosure detected' : 'No prompt disclosure detected'}
                    </strong>
                    {turn.verdict.rationale && <span style={{ opacity: 0.9 }}>— {turn.verdict.rationale}</span>}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {/* Tab 4: Timeline */}
      {activeTab === 'timeline' && (
        <div className="timeline-container">
          <div className="timeline-node">
            <span className="timeline-marker" />
            <div className="timeline-node-content">
              <strong>Assessment record</strong>
              <p style={{ margin: '0.25rem 0 0', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                Target: {targetName} · Category: OWASP LLM08
              </p>
            </div>
          </div>

          {turns.map(turn => {
            const exploited = Boolean(turn.verdict?.exploited);
            return (
              <div key={turn.turn_index} className="timeline-node">
                <span className={`timeline-marker ${exploited ? 'exploited' : ''}`} />
                <div className="timeline-node-content">
                  <strong>Turn #{turn.turn_index}: {turn.strategy || 'Extraction attempt'}</strong>
                  <p style={{ margin: '0.25rem 0 0', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                    {turnOutcome(turn)} · {formatDate(turn.created_at)} ({turn.latency_ms} ms)
                  </p>
                </div>
              </div>
            );
          })}

          <div className="timeline-node">
            <span className="timeline-marker" style={{ backgroundColor: scanStatus === 'COMPLETED' ? 'var(--color-success)' : 'var(--color-border-control)' }} />
            <div className="timeline-node-content">
              <strong>Assessment status: {scanStatus}</strong>
              <p style={{ margin: '0.25rem 0 0', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                Total findings: {findingsAvailable ? findings.length : "Unavailable"} · Risk Grade: {riskGrade != null ? `${riskGrade}/100` : '—'}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
