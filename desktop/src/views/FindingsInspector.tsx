import { useCallback, useEffect, useState } from 'react';
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
    setLoading(true);
    setError(null);
    try {
      const [summaryRes, findingsRes, turnsRes] = await Promise.allSettled([
        api.findingsSummary(id),
        api.findings(id),
        api.scanTurns(id),
      ]);

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

      if (summaryRes.status === 'rejected' && findingsRes.status === 'rejected') {
        setError('Findings data could not be retrieved from the Aegis engine. Verify the engine is running.');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load assessment findings.');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadFindingDetail = async (findingId: string) => {
    if (findingDetails[findingId]) return;
    try {
      const detail = await api.findingDetail(findingId);
      setFindingDetails(prev => ({ ...prev, [findingId]: detail }));
    } catch {
      // Gracefully fall back to base finding row
    }
  };

  useEffect(() => {
    if (selectedScanId) {
      void loadScanData(selectedScanId);
    }
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
  const scanStatus = (summary?.scan_status || currentScanHistory?.status || 'COMPLETED').toUpperCase();
  const riskGrade = summary ? Math.round(summary.risk_grade) : null;
  const isClean = scanStatus === 'COMPLETED' && findings.length === 0;
  const isScanRunning = ['RUNNING', 'SCANNING', 'QUEUED'].includes(scanStatus);

  return (
    <div className="page-content findings-page">
      {/* Top Header */}
      <div className="findings-topbar">
        <div>
          <div className="eyebrow">ASSESSMENT RESULTS</div>
          <h1>{targetName}</h1>
          <div className="findings-meta-badges">
            <span className={`scan-status ${scanStatus.toLowerCase()}`}>
              {scanStatus.replace(/_/g, ' ')}
            </span>
            <span className="table-category">LLM07 System Prompt Leakage</span>
            {summary?.target_url && (
              <span className="dashboard-muted" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
                <Globe2 size={13} />
                {summary.target_url}
              </span>
            )}
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
            disabled={exporting || loading || isScanRunning}
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
          aria-selected={activeTab === 'overview'}
          role="tab"
        >
          <Shield size={16} />
          <span>Overview</span>
        </button>

        <button
          className={`findings-tab-btn ${activeTab === 'findings' ? 'active' : ''}`}
          onClick={() => setActiveTab('findings')}
          aria-selected={activeTab === 'findings'}
          role="tab"
        >
          <ShieldAlert size={16} />
          <span>Findings</span>
          <span className="findings-tab-badge">{findings.length}</span>
        </button>

        <button
          className={`findings-tab-btn ${activeTab === 'evidence' ? 'active' : ''}`}
          onClick={() => setActiveTab('evidence')}
          aria-selected={activeTab === 'evidence'}
          role="tab"
        >
          <Terminal size={16} />
          <span>Evidence</span>
          <span className="findings-tab-badge">{turns.length}</span>
        </button>

        <button
          className={`findings-tab-btn ${activeTab === 'timeline' ? 'active' : ''}`}
          onClick={() => setActiveTab('timeline')}
          aria-selected={activeTab === 'timeline'}
          role="tab"
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

      {/* Tab 1: Overview */}
      {activeTab === 'overview' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
          {/* Summary Metric Cards */}
          <div className="findings-summary-grid">
            <div className="summary-card">
              <div className="summary-card-header">
                <span>Total Findings</span>
                <ShieldAlert size={16} />
              </div>
              <div className="summary-card-value">{findings.length}</div>
              <div className="summary-card-sub">
                {findings.length === 1 ? '1 vulnerability confirmed' : `${findings.length} vulnerabilities confirmed`}
              </div>
            </div>

            <div className="summary-card">
              <div className="summary-card-header">
                <span>Critical & High</span>
                <AlertTriangle size={16} style={{ color: 'var(--color-danger)' }} />
              </div>
              <div className="summary-card-value" style={{ color: (summary?.by_severity['CRITICAL'] || 0) + (summary?.by_severity['HIGH'] || 0) > 0 ? 'var(--color-danger)' : 'inherit' }}>
                {(summary?.by_severity['CRITICAL'] || 0) + (summary?.by_severity['HIGH'] || 0)}
              </div>
              <div className="summary-card-sub">
                {summary?.by_severity['CRITICAL'] || 0} Critical · {summary?.by_severity['HIGH'] || 0} High
              </div>
            </div>

            <div className="summary-card">
              <div className="summary-card-header">
                <span>Risk Grade</span>
                <ShieldCheck size={16} style={{ color: (riskGrade || 100) >= 80 ? 'var(--color-success)' : 'var(--color-danger)' }} />
              </div>
              <div className="summary-card-value" style={{ color: (riskGrade || 100) >= 80 ? 'var(--color-success)' : 'var(--color-danger)' }}>
                {riskGrade != null ? `${riskGrade} / 100` : '—'}
              </div>
              <div className="summary-card-sub">
                {(riskGrade || 100) >= 90 ? 'Grade A · Resilient' : (riskGrade || 100) >= 70 ? 'Grade B · Vulnerable' : 'Grade C · Compromised'}
              </div>
            </div>

            <div className="summary-card">
              <div className="summary-card-header">
                <span>Tested Scope</span>
                <Info size={16} />
              </div>
              <div className="summary-card-value" style={{ fontSize: '1.25rem', paddingTop: '0.25rem' }}>
                OWASP LLM07
              </div>
              <div className="summary-card-sub">
                {turns.length} prompt interaction{turns.length === 1 ? '' : 's'}
              </div>
            </div>
          </div>

          {/* Clean Scan Outcome State */}
          {isClean && (
            <div className="clean-scan-banner">
              <CheckCircle2 size={24} className="banner-icon" />
              <div>
                <h3>No vulnerabilities detected for tested extraction requests</h3>
                <p>
                  The target model successfully refused or contained all prompt leakage attempts during this assessment run.
                  No canary tokens or internal prompt signatures were disclosed across {turns.length} tested turns.
                </p>
              </div>
            </div>
          )}

          {/* Scope notice per Section 9 */}
          <div className="scope-disclosure-notice">
            <Info size={16} />
            <span>
              <strong>Scope Notice:</strong> Assessment is currently scoped to OWASP LLM07 (System Prompt Leakage).
              Other OWASP LLM Top 10 categories were not evaluated in this scan.
            </span>
          </div>
        </div>
      )}

      {/* Tab 2: Findings List */}
      {activeTab === 'findings' && (
        <div className="findings-list">
          {findings.length === 0 ? (
            <div className="dashboard-panel" style={{ textAlign: 'center', padding: '3rem' }}>
              <ShieldCheck size={36} style={{ color: 'var(--color-success)', margin: '0 auto 1rem' }} />
              <h3 style={{ marginBottom: '0.5rem' }}>No findings recorded for this scan</h3>
              <p style={{ color: 'var(--color-text-secondary)', maxWidth: '520px', margin: '0 auto' }}>
                All prompts evaluated during this run were successfully defended without prompt disclosure.
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
                    onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && toggleExpand(finding.id)}
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
                          <LoaderCircle size={18} className="spin" style={{ margin: '0 auto' }} />
                          <small>Loading evidence details…</small>
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
              <p>No turns recorded for this assessment.</p>
            </div>
          ) : (
            turns.map(turn => (
              <div key={turn.turn_index} className="turn-replay-card">
                <div className="turn-replay-header">
                  <strong>Attempt #{turn.turn_index} · {turn.strategy || 'LLM07'}</strong>
                  <span className="dashboard-muted">{turn.latency_ms} ms</span>
                </div>

                <div className="evidence-section">
                  <span className="evidence-section-label">Prompt</span>
                  <pre className="evidence-console">{turn.prompt}</pre>
                </div>

                <div className="evidence-section">
                  <span className="evidence-section-label">Chatbot Response</span>
                  <pre className="evidence-console">{turn.response || '(No response text returned)'}</pre>
                </div>

                {turn.verdict && (
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
              <strong>Assessment Initiated</strong>
              <p style={{ margin: '0.25rem 0 0', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                Target: {targetName} · Category: OWASP LLM07
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
                    {exploited ? 'Triggered prompt leakage detection' : 'Completed without disclosure'} ({turn.latency_ms} ms)
                  </p>
                </div>
              </div>
            );
          })}

          <div className="timeline-node">
            <span className="timeline-marker" style={{ backgroundColor: scanStatus === 'COMPLETED' ? 'var(--color-success)' : 'var(--color-border-control)' }} />
            <div className="timeline-node-content">
              <strong>Assessment Concluded ({scanStatus})</strong>
              <p style={{ margin: '0.25rem 0 0', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                Total findings: {findings.length} · Risk Grade: {riskGrade != null ? `${riskGrade}/100` : '—'}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
