import { useEffect, useRef } from 'react';
import { ArrowLeft, ArrowRight, Check, Globe2, Info, Laptop, LoaderCircle, MousePointer2, Play, ShieldCheck, Sparkles } from 'lucide-react';
import { useAssessmentWizard, type AssessmentProps } from '../hooks/useAssessmentWizard';
import './new-assessment.css';

const steps = [
  ['Target Configuration', 'Application to test'],
  ['Interface Calibration', 'Detect and configure'],
  ['Test Scope', 'Select category and budget'],
  ['Review & Run', 'Confirm and start'],
];

export default function NewAssessment(props: AssessmentProps) {
  const w = useAssessmentWizard(props);
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => { heading.current?.focus(); }, [w.step]);
  const busy = Boolean(w.operation);
  const targetName = w.target?.name || w.name.trim() || 'Use URL hostname';
  return <div className="assessment-page">
    <header className="assessment-heading"><span>ASSESSMENT</span><h1>New Assessment</h1><p>Configure your target, select test scope, and run an AI security scan.</p></header>
    <div className="assessment-layout">
      <nav className="assessment-steps" aria-label="Assessment progress"><ol>{steps.map(([title, description], index) =>
        <li key={title} className={index === w.step ? 'current' : index < w.step ? 'complete' : ''}>
          <button type="button" aria-current={index === w.step ? 'step' : undefined} disabled={index > w.step || busy} onClick={() => w.navigate(index)}>
            <span className="assessment-step-number">{index < w.step ? <Check size={18}/> : index + 1}</span><span><strong>{title}</strong><small>{description}</small></span>
          </button>
        </li>)}</ol></nav>
      <section className="assessment-panel" aria-labelledby="assessment-step-title" aria-busy={busy}>
        <h2 id="assessment-step-title" tabIndex={-1} ref={heading}>{steps[w.step][0]}</h2>
        {w.step === 0 && <div className="assessment-fields">
          <div className="assessment-types"><div className="assessment-web"><Globe2 size={28}/><span><strong>Web Application</strong><small>Browser-based interface · Selected</small></span></div><button type="button" disabled><Laptop size={28}/><span><strong>Desktop Application</strong><small>Native UI automation · Unavailable</small></span></button></div>
          {props.targets.length > 0 && <label className="assessment-field">Registered target<select value={w.target?.id || ''} onChange={e => w.select(e.target.value)}><option value="">Create a new target</option>{w.target && !props.targets.some(t => t.id === w.target?.id) && <option value={w.target.id}>{w.target.name} · {w.target.url}</option>}{props.targets.map(t => <option key={t.id} value={t.id} disabled={t.target_type !== 'web'}>{t.name} · {t.url}{t.target_type !== 'web' ? ' (unavailable)' : ''}</option>)}</select></label>}
          <label className="assessment-field">Target Name<input value={w.name} onChange={e => w.edit('name', e.target.value)} placeholder="e.g. Internal support assistant" autoComplete="off"/><small>Optional. Defaults to the URL hostname for a new target.</small></label>
          <label className="assessment-field">Application URL<input value={w.url} onChange={e => w.edit('url', e.target.value)} placeholder="http://127.0.0.1:5173" autoComplete="off" spellCheck={false} aria-describedby="assessment-url-help"/><small id="assessment-url-help">Use an authorized local or private-network web target. The engine validates access.</small></label>
          <div className="assessment-inset"><h3><ShieldCheck size={20}/>Target authorization</h3><label className="assessment-consent"><input type="checkbox" checked={w.consent} onChange={e => w.setConsent(e.target.checked)}/><span>I own this target or have written permission to test it.<small>Applies to <strong>{w.url.trim() || 'the URL entered above'}</strong>. Changing the target requires authorization again.</small></span></label><p className="assessment-note"><Info size={18}/>Playwright will interact with this application during calibration and scanning. Calibration is configured in the next step.</p></div>
        </div>}
        {w.step === 1 && <div className="assessment-fields">
          <p className="assessment-intro">Detect the chat controls automatically, or select them in the target browser.</p>
          <div className="assessment-target"><Globe2 size={22}/><div><strong>{targetName}</strong><span>{w.url}</span></div><span className="assessment-authorized"><ShieldCheck size={16}/>Authorized</span></div>
          <div className="assessment-inset"><h3>Browser Calibration</h3><p>Automatic detection finds the input, Send control, and response area. Manual calibration asks you to click the input first, then Send / Enter; response detection remains automatic.</p><div className="assessment-calibration-actions"><button className="button primary" disabled={busy} onClick={() => void w.calibrate(false)}>{w.operation === 'auto' ? <LoaderCircle size={18} className="spin"/> : <Sparkles size={18}/>}Automatic calibration</button><button className="button secondary" disabled={busy} onClick={() => void w.calibrate(true)}>{w.operation === 'click' ? <LoaderCircle size={18} className="spin"/> : <MousePointer2 size={18}/>}Manual calibration</button></div></div>
          <div role="status" className="assessment-calibration-status">
            {busy ? <p><LoaderCircle size={18} className="spin"/>{w.operation === 'auto' ? 'Opening target and detecting controls…' : 'Follow the selection prompts in the Playwright browser.'}</p> : w.calibration ? <p className="assessment-ready"><Check size={18}/>Calibration ready · saved selectors</p> : <p><Info size={18}/>Calibration required before continuing.</p>}
            {w.session && <><ol className="assessment-capture"><li>{w.session.input_selected ? <Check size={17}/> : <span>1</span>}Click the input field</li><li>{w.session.enter_selected ? <Check size={17}/> : <span>2</span>}Click Send / Enter</li></ol><p>{w.session.status === 'opening_browser' ? 'Opening the target browser…' : w.session.status === 'saving_selectors' ? 'Saving selectors…' : w.session.status === 'completed' ? w.calibration ? 'Controls captured. Selectors saved to this target.' : 'Controls captured; waiting for saved selectors.' : w.session.status === 'failed' ? 'Calibration failed.' : w.session.input_selected ? 'Input captured. Select Send / Enter next.' : 'Waiting for input selection.'}</p></>}
          </div>
          {w.calibration && <dl className="assessment-selectors">{[['Input', w.calibration.input_selector], ['Send', w.calibration.submit_selector], ['Response', w.calibration.response_selector]].map(([label, value]) => <div key={label}><dt>{label}</dt><dd><code>{value}</code></dd></div>)}</dl>}
          <p className="assessment-note"><Info size={18}/>Keep the target browser open during calibration. Navigation is paused while it runs. Leaving this page does not cancel the browser operation.</p>
        </div>}
        {w.step === 2 && <div className="assessment-fields">
          <p className="assessment-intro">Choose the scope and maximum number of attempts for this assessment.</p>
          <label className="assessment-field">OWASP category<select value="LLM08" onChange={() => undefined}><option value="LLM08">LLM08 · Hidden Context Exposure</option></select></label>
          <div className="assessment-inset"><h3><ShieldCheck size={20}/>Hidden Context Exposure</h3><p>Tests direct, plain-language disclosure requests against your authorized web target. Other OWASP categories are not supported by the current assessment pipeline.</p></div>
          <label className="assessment-field assessment-budget">Attempt budget <output>{w.budget} attempts</output><input type="range" min="1" max="10" step="1" value={w.budget} onChange={e => w.setBudget(Number(e.target.value))}/><span className="assessment-range"><span>1 attempt</span><span>10 attempts</span></span><small>This is the maximum configured budget, not a prediction of completed tests.</small></label>
        </div>}
        {w.step === 3 && <div className="assessment-fields">
          <p className="assessment-intro">Review the configuration before submitting your assessment to the engine.</p>
          <dl className="assessment-review">{[['Target', targetName], ['Application URL', w.url], ['Target type', 'Web Application'], ['Authorization', w.consent ? 'Confirmed for this target' : 'Required'], ['Calibration', w.calibration ? 'Ready · saved selectors' : 'Required'], ['Test category', 'LLM08 · Hidden Context Exposure'], ['Attempt budget', `${w.budget} attempts`]].map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
          <p className="assessment-note"><Info size={18}/>Run scan opens the target in Playwright. Keep the browser open. Scan request history is stored locally in this browser profile.</p>
        </div>}
        {w.error && <div className="assessment-error" role="alert"><Info size={18}/>{w.error}</div>}
        <footer className="assessment-footer"><span>Step {w.step + 1} of 4</span><div>{w.step > 0 && <button className="button secondary" disabled={busy} onClick={() => w.navigate(w.step - 1)}><ArrowLeft size={17}/>Back</button>}{w.step < 3 ? <button className="button primary" disabled={busy} onClick={() => w.navigate(w.step + 1)}>Next<ArrowRight size={18}/></button> : <button className="button primary" disabled={busy} onClick={() => void w.start()}>{busy ? <LoaderCircle size={18} className="spin"/> : <Play size={17}/>} {busy ? 'Submitting…' : 'Run scan'}</button>}</div></footer>
      </section>
    </div>
  </div>;
}
