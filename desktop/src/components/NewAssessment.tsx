import { useEffect, useRef } from 'react';
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Cpu,
  Globe2,
  Info,
  Laptop,
  LoaderCircle,
  MousePointer2,
  Play,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  AlertTriangle,
} from 'lucide-react';
import { useAssessmentWizard, type AssessmentProps } from '../hooks/useAssessmentWizard';
import './new-assessment.css';

const steps = [
  ['Target Configuration', 'Application to test'],
  ['Interface Calibration', 'Detect and configure'],
  ['Test Scope', 'Select categories and budget'],
  ['Review & Run', 'Confirm and start'],
];

const CANONICAL_CATEGORIES = [
  {
    id: 'LLM01',
    name: 'Prompt Injection',
    description: 'Tests direct instruction overrides, delimiter hijacking, XML smuggling, translation injection, and PromptInject vectors against prompt adherence safeguards.',
  },
  {
    id: 'LLM02',
    name: 'Sensitive Information Disclosure',
    description: 'Tests inadvertent exposure of PII, credentials, API keys, private training data, or proprietary documents through model output.',
  },
  {
    id: 'LLM03',
    name: 'Excessive Agency',
    description: 'Probes tool capability discovery, arbitrary shell command execution, database query abuse, and unrestricted environment inspection.',
  },
  {
    id: 'LLM04',
    name: 'Supply Chain',
    description: 'Audits vulnerable third-party components, compromised dependencies, and untrusted model/plugin pipelines.',
  },
  {
    id: 'LLM05',
    name: 'Data and Model Poisoning',
    description: 'Detects manipulation of pre-training data, fine-tuning sets, or runtime embeddings to introduce backdoors or biases.',
  },
  {
    id: 'LLM06',
    name: 'Unbounded Consumption',
    description: 'Tests resource exhaustion vectors, unbounded query generation, algorithmic complexity attacks, and denial of wallet.',
  },
  {
    id: 'LLM07',
    name: 'Misinformation',
    description: 'Evaluates confabulation, false claims presented as authoritative fact, hallucinated citations, and deceptive justifications.',
  },
  {
    id: 'LLM08',
    name: 'Hidden Context Exposure',
    description: 'Tests system prompt disclosure, canary extraction, internal instructions, and Many-Shot context saturation (MSJ).',
  },
  {
    id: 'LLM09',
    name: 'Vector and Embedding Weaknesses',
    description: 'Tests vector and RAG context leakage, raw chunk exfiltration, cross-tenant embedding collisions, and retrieval poisoning.',
  },
  {
    id: 'LLM10',
    name: 'Improper Output Handling',
    description: 'Tests client-side Markdown tracking pixels, external hyperlink exfiltration, raw HTML tag rendering, and JavaScript URI schemes.',
  },
];

export default function NewAssessment(props: AssessmentProps) {
  const w = useAssessmentWizard(props);
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => { heading.current?.focus(); }, [w.step]);
  const busy = Boolean(w.operation);
  const targetName = w.target?.name || w.name.trim() || 'Use URL hostname';

  return (
    <div className="assessment-page">
      <header className="assessment-heading">
        <span>ASSESSMENT</span>
        <h1>New Assessment</h1>
        <p>Configure your target, select test scope, and run an AI security scan.</p>
      </header>
      <div className="assessment-layout">
        <nav className="assessment-steps" aria-label="Assessment progress">
          <ol>
            {steps.map(([title, description], index) => (
              <li key={title} className={index === w.step ? 'current' : index < w.step ? 'complete' : ''}>
                <button
                  type="button"
                  aria-current={index === w.step ? 'step' : undefined}
                  disabled={index > w.step || busy}
                  onClick={() => w.navigate(index)}
                >
                  <span className="assessment-step-number">
                    {index < w.step ? <Check size={18} /> : index + 1}
                  </span>
                  <span>
                    <strong>{title}</strong>
                    <small>{description}</small>
                  </span>
                </button>
              </li>
            ))}
          </ol>
        </nav>
        <section className="assessment-panel" aria-labelledby="assessment-step-title" aria-busy={busy}>
          <h2 id="assessment-step-title" tabIndex={-1} ref={heading}>{steps[w.step][0]}</h2>

          {w.step === 0 && (
            <div className="assessment-fields">
              <div className="assessment-types">
                <div className="assessment-web">
                  <Globe2 size={28} />
                  <span>
                    <strong>Web Application</strong>
                    <small>Browser-based interface · Selected</small>
                  </span>
                </div>
                <button type="button" disabled>
                  <Laptop size={28} />
                  <span>
                    <strong>Desktop Application</strong>
                    <small>Native UI automation · Unavailable</small>
                  </span>
                </button>
              </div>

              {props.targets.length > 0 && (
                <label className="assessment-field">
                  Registered target
                  <select value={w.target?.id || ''} onChange={e => w.select(e.target.value)}>
                    <option value="">Create a new target</option>
                    {w.target && !props.targets.some(t => t.id === w.target?.id) && (
                      <option value={w.target.id}>{w.target.name} · {w.target.url}</option>
                    )}
                    {props.targets.map(t => (
                      <option key={t.id} value={t.id} disabled={t.target_type !== 'web'}>
                        {t.name} · {t.url}{t.target_type !== 'web' ? ' (unavailable)' : ''}
                      </option>
                    ))}
                  </select>
                </label>
              )}

              <label className="assessment-field">
                Target Name
                <input
                  value={w.name}
                  onChange={e => w.edit('name', e.target.value)}
                  placeholder="e.g. Internal support assistant"
                  autoComplete="off"
                />
                <small>Optional. Defaults to the URL hostname for a new target.</small>
              </label>

              <label className="assessment-field">
                Application URL
                <input
                  value={w.url}
                  onChange={e => w.edit('url', e.target.value)}
                  placeholder="http://127.0.0.1:5173"
                  autoComplete="off"
                  spellCheck={false}
                  aria-describedby="assessment-url-help"
                />
                <small id="assessment-url-help">
                  Use an authorized local or private-network web target. The engine validates access.
                </small>
              </label>

              <label className="assessment-field">
                Local Project Folder (Optional Tier 3 Inspection)
                <input
                  value={w.projectPath}
                  onChange={e => w.edit('projectPath', e.target.value)}
                  placeholder="e.g. C:\dev\my-rag-chatbot or D:\projects\assistant"
                  autoComplete="off"
                  spellCheck={false}
                />
                <small>
                  Optional local folder. Aegis reads configuration files (package.json, pyproject.toml, .env keys) locally to detect RAG, vector stores, and tools. Never transmits code outside this device.
                </small>
              </label>

              <div className="assessment-inset">
                <h3><ShieldCheck size={20} />Target authorization</h3>
                <label className="assessment-consent">
                  <input
                    type="checkbox"
                    checked={w.consent}
                    onChange={e => w.setConsent(e.target.checked)}
                  />
                  <span>
                    I own this target or have written permission to test it.
                    <small>
                      Applies to <strong>{w.url.trim() || 'the URL entered above'}</strong>. Changing the target requires authorization again.
                    </small>
                  </span>
                </label>
                <p className="assessment-note">
                  <Info size={18} />
                  Playwright will interact with this application during calibration and scanning. Calibration is configured in the next step.
                </p>
              </div>
            </div>
          )}

          {w.step === 1 && (
            <div className="assessment-fields">
              <p className="assessment-intro">
                Detect the chat controls automatically, or select them in the target browser.
              </p>
              <div className="assessment-target">
                <Globe2 size={22} />
                <div>
                  <strong>{targetName}</strong>
                  <span>{w.url}</span>
                </div>
                <span className="assessment-authorized"><ShieldCheck size={16} />Authorized</span>
              </div>

              <div className="assessment-inset">
                <h3>Browser Calibration</h3>
                <p>
                  Automatic detection finds the input, Send control, and response area. Manual calibration asks you to click the input first, then Send / Enter; response detection remains automatic.
                </p>
                <div className="assessment-calibration-actions">
                  <button className="button primary" disabled={busy || w.reconLoading} onClick={() => void w.calibrate(false)}>
                    {w.operation === 'auto' ? <LoaderCircle size={18} className="spin" /> : <Sparkles size={18} />}
                    Automatic calibration
                  </button>
                  <button className="button secondary" disabled={busy || w.reconLoading} onClick={() => void w.calibrate(true)}>
                    {w.operation === 'click' ? <LoaderCircle size={18} className="spin" /> : <MousePointer2 size={18} />}
                    Manual calibration
                  </button>
                </div>
              </div>

              <div role="status" className="assessment-calibration-status">
                {busy ? (
                  <p>
                    <LoaderCircle size={18} className="spin" />
                    {w.operation === 'recon'
                      ? 'Registering target and starting passive reconnaissance…'
                      : w.operation === 'auto'
                        ? 'Opening target and detecting controls…'
                        : 'Follow the selection prompts in the Playwright browser.'}
                  </p>
                ) : w.calibration ? (
                  <p className="assessment-ready"><Check size={18} />Calibration ready · saved selectors</p>
                ) : (
                  <p><Info size={18} />Calibration required before continuing.</p>
                )}
                {w.session && (
                  <>
                    <ol className="assessment-capture">
                      <li>{w.session.input_selected ? <Check size={17} /> : <span>1</span>}Click the input field</li>
                      <li>{w.session.enter_selected ? <Check size={17} /> : <span>2</span>}Click Send / Enter</li>
                    </ol>
                    <p>
                      {w.session.status === 'opening_browser'
                        ? 'Opening the target browser…'
                        : w.session.status === 'saving_selectors'
                        ? 'Saving selectors…'
                        : w.session.status === 'completed'
                        ? w.calibration
                          ? 'Controls captured. Selectors saved to this target.'
                          : 'Controls captured; waiting for saved selectors.'
                        : w.session.status === 'failed'
                        ? 'Calibration failed.'
                        : w.session.input_selected
                        ? 'Input captured. Select Send / Enter next.'
                        : 'Waiting for input selection.'}
                    </p>
                  </>
                )}
              </div>

              {w.calibration && (
                <dl className="assessment-selectors">
                  {[
                    ['Input', w.calibration.input_selector],
                    ['Send', w.calibration.submit_selector],
                    ['Response', w.calibration.response_selector],
                  ].map(([label, value]) => (
                    <div key={label}><dt>{label}</dt><dd><code>{value}</code></dd></div>
                  ))}
                </dl>
              )}

              {/* Reconnaissance & Target Profile Section */}
              <div className="assessment-recon-section">
                <div className="assessment-recon-header">
                  <h3><Cpu size={18} /> Target Reconnaissance & Profiling</h3>
                  {w.target && (
                    <button
                      type="button"
                      className="button secondary small"
                      disabled={busy || w.reconLoading}
                      onClick={() => void w.fetchReconAndPlan()}
                    >
                      {w.reconLoading ? <LoaderCircle size={14} className="spin" /> : <RefreshCw size={14} />}
                      {w.reconLoading ? 'Analyzing…' : 'Refresh profile'}
                    </button>
                  )}
                </div>
                <p className="assessment-intro">
                  Autonomous reconnaissance infers target capabilities (RAG, HTML rendering, local ports, config) to guide the test planner.
                </p>

                {w.reconLoading && (
                  <div style={{ padding: '12px 0', display: 'flex', alignItems: 'center', gap: 8, color: 'var(--color-text-secondary)', fontSize: 13 }}>
                    <LoaderCircle size={16} className="spin" />
                    Fingerprinting target and generating tailored test plan…
                  </div>
                )}

                {w.reconProfile?.stages && (
                  <div className="recon-stage-grid">
                    {Object.entries(w.reconProfile.stages).map(([key, detail]) => {
                      const stageNames: Record<string, string> = {
                        passive_observation: '1. Passive Observation',
                        local_discovery: '2. Loopback Discovery',
                        static_scanner: '3. Static Inspection',
                        probe_runner: '4. Active Probes',
                      };
                      return (
                        <div key={key} className="recon-stage-card">
                          <div className="recon-stage-top">
                            <strong>{stageNames[key] || key}</strong>
                            <span className={`badge-status badge-${detail.status}`}>{detail.status}</span>
                          </div>
                          <small>
                            {detail.duration_ms != null ? `${detail.duration_ms} ms` : ''}
                            {detail.warning ? ` · ${detail.warning}` : ''}
                          </small>
                        </div>
                      );
                    })}
                  </div>
                )}

                {w.reconProfile && (
                  <div className="recon-tag-list">
                    <span className={`recon-tag ${w.reconProfile.has_rag?.detected ? 'ready' : 'neutral'}`}>
                      RAG: {w.reconProfile.has_rag?.detected
                        ? `Detected (${Math.round((w.reconProfile.has_rag.confidence || 0) * 100)}%)`
                        : 'Not detected / unconfirmed'}
                    </span>
                    <span className={`recon-tag ${w.reconProfile.renders_html?.detected ? 'warn' : 'neutral'}`}>
                      HTML: {w.reconProfile.renders_html?.detected
                        ? `DOM Rendered (${Math.round((w.reconProfile.renders_html.confidence || 0) * 100)}%)`
                        : 'Text-only'}
                    </span>
                    {w.reconProfile.has_memory?.detected && (
                      <span className="recon-tag ready">
                        Memory: Detected ({Math.round((w.reconProfile.has_memory.confidence || 0) * 100)}%)
                      </span>
                    )}
                  </div>
                )}

                {w.reconProfile?.warnings && w.reconProfile.warnings.length > 0 && (
                  <div className="recon-warning-box">
                    <AlertTriangle size={15} style={{ flexShrink: 0, marginTop: 2 }} />
                    <div>
                      <strong>Reconnaissance Warnings:</strong>
                      {w.reconProfile.warnings.map((warn, i) => (
                        <div key={i}>{warn}</div>
                      ))}
                    </div>
                  </div>
                )}

                {w.reconError && (
                  <div className="recon-warning-box">
                    <AlertTriangle size={15} style={{ flexShrink: 0, marginTop: 2 }} />
                    <div>{w.reconError}</div>
                  </div>
                )}
              </div>

              <p className="assessment-note">
                <Info size={18} />
                Keep the target browser open during calibration. Navigation is paused while it runs. Leaving this page does not cancel the browser operation.
              </p>
            </div>
          )}

          {w.step === 2 && (
            <div className="assessment-fields">
              <div className="scope-toolbar">
                <div>
                  <p className="assessment-intro" style={{ margin: 0 }}>
                    Choose categories to assess and the attempt budget for each category.
                  </p>
                </div>
                <div className="scope-actions">
                  <button
                    type="button"
                    className="button secondary small"
                    disabled={busy}
                    onClick={w.selectAllReady}
                  >
                    <Sparkles size={14} /> Run all ready categories
                  </button>
                  <label className="scope-toggle">
                    <input
                      type="checkbox"
                      checked={w.showAllCategories}
                      onChange={e => w.setShowAllCategories(e.target.checked)}
                    />
                    Show all 10 categories
                  </label>
                </div>
              </div>

              {!w.showAllCategories && w.testPlan?.selectable_category_ids?.length === 0 && (
                <div className="recon-warning-box">
                  {w.testPlan.is_complete
                    ? 'No categories are currently ready to scan. Review the applicable categories below or show all 10 statuses.'
                    : 'Recon is incomplete. Complete the required recon stages before selecting a category.'}
                </div>
              )}

              <div className="category-card-list">
                {CANONICAL_CATEGORIES
                  .filter(cat => {
                    if (w.showAllCategories) return true;
                    const plan = w.testPlan?.categories.find(c => c.category === cat.id);
                    return plan?.applicability === 'applicable' || Boolean(plan?.selectable);
                  })
                  .map(cat => {
                    const plan = w.testPlan?.categories.find(c => c.category === cat.id);
                    const isSelectable = Boolean(plan?.selectable);
                    const isSelected = w.selectedCategories.includes(cat.id);
                    return (
                      <div
                        key={cat.id}
                        className={`category-card ${isSelected ? 'selected' : ''} ${!isSelectable ? 'disabled' : ''}`}
                      >
                        <label className="category-card-label">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            disabled={!isSelectable || busy}
                            onChange={() => w.toggleCategory(cat.id)}
                          />
                          <div className="category-card-content">
                            <div className="category-card-header">
                              <strong>{cat.id} · {cat.name}</strong>
                              {isSelectable ? (
                                <span className="badge badge-ready"><Check size={12} /> Ready</span>
                              ) : (
                                <span className={`badge ${plan?.implementation_status === 'under_development' ? 'badge-dev' : 'badge-warning'}`}>
                                  {plan?.implementation_status === 'under_development' ? 'Under development' : plan?.applicability === 'not_applicable' ? 'Not applicable' : plan ? 'Recon incomplete' : 'Awaiting profile'}
                                </span>
                              )}
                            </div>
                            <p>{cat.description}</p>
                            {!isSelectable ? (
                              <small className="dev-note">
                                {plan?.reason || 'Run recon and planning before selecting this category.'}
                              </small>
                            ) : (
                              <small className="ready-note">
                                {plan?.planned_prompt_ids ? `${plan.planned_prompt_ids.length} planned prompts · ` : ''}
                                Fully implemented execution and judge pipeline
                              </small>
                            )}
                          </div>
                        </label>
                      </div>
                    );
                  })}
              </div>

              <label className="assessment-field assessment-budget">
                Attempts per category <output>{w.budget} each · {w.budget * w.selectedCategories.length} total maximum</output>
                <input
                  type="range"
                  min="1"
                  max="10"
                  step="1"
                  value={w.budget}
                  onChange={e => w.setBudget(Number(e.target.value))}
                />
                <span className="assessment-range">
                  <span>1 attempt</span>
                  <span>10 attempts</span>
                </span>
                <small>
                  Each selected category receives this budget. The total is a maximum; a category may finish early if a finding is confirmed.
                </small>
              </label>
            </div>
          )}

          {w.step === 3 && (
            <div className="assessment-fields">
              <p className="assessment-intro">
                Review the configuration before submitting your assessment to the engine.
              </p>
              <dl className="assessment-review">
                {[
                  ['Target', targetName],
                  ['Application URL', w.url],
                  ['Project folder', w.projectPath ? w.projectPath : 'None (Tier 3 static scan skipped)'],
                  ['Target type', 'Web Application'],
                  ['Authorization', w.consent ? 'Confirmed for this target' : 'Required'],
                  ['Calibration', w.calibration ? 'Ready · saved selectors' : 'Required'],
                  [
                    'Test categories',
                    `${w.selectedCategories.length} selected (${w.selectedCategories.map(id => {
                      const cat = CANONICAL_CATEGORIES.find(c => c.id === id);
                      return `${id} ${cat?.name || ''}`;
                    }).join(', ')})`,
                  ],
                  ['Attempt budget', `${w.budget} attempts`],
                ].map(([label, value]) => (
                  <div key={label}><dt>{label}</dt><dd>{value}</dd></div>
                ))}
              </dl>
              <p className="assessment-note">
                <Info size={18} />
                Run scan opens the target in Playwright. Keep the browser open. Scan request history is stored locally in this browser profile.
              </p>
            </div>
          )}

          {w.error && (
            <div className="assessment-error" role="alert">
              <Info size={18} />{w.error}
            </div>
          )}

          <footer className="assessment-footer">
            <span>Step {w.step + 1} of 4</span>
            <div>
              {w.step > 0 && (
                <button className="button secondary" disabled={busy} onClick={() => w.navigate(w.step - 1)}>
                  <ArrowLeft size={17} />Back
                </button>
              )}
              {w.step < 3 ? (
                <button className="button primary" disabled={busy} onClick={() => w.navigate(w.step + 1)}>
                  Next<ArrowRight size={18} />
                </button>
              ) : (
                <button
                  className="button primary"
                  disabled={busy || w.selectedCategories.length === 0}
                  onClick={() => void w.start()}
                >
                  {busy ? <LoaderCircle size={18} className="spin" /> : <Play size={17} />}
                  {' '}
                  {busy ? 'Submitting…' : w.selectedCategories.length > 1 ? `Run multi-category scan (${w.selectedCategories.length})` : 'Run scan'}
                </button>
              )}
            </div>
          </footer>
        </section>
      </div>
    </div>
  );
}
