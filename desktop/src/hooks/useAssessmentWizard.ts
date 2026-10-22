import { useEffect, useRef, useState } from 'react';
import { api, type CalibrationSession, type ScanRecord, type Target } from '../api/client';

export type AssessmentProps = {
  targets: Target[];
  refresh: () => Promise<void>;
  onStarted: (scan: ScanRecord, target?: Target) => void;
  notify: (message: string) => void;
};
function normalizeUrl(raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed) throw new Error('Enter the local target URL before continuing.');
  const value = /^[a-z][a-z0-9+.-]*:\/\//i.test(trimmed) ? trimmed : `http://${trimmed}`;
  let parsed: URL;
  try { parsed = new URL(value); } catch { throw new Error('Enter a valid URL such as http://127.0.0.1:5173.'); }
  if (!['http:', 'https:'].includes(parsed.protocol)) throw new Error('Target URL must start with http:// or https://.');
  return value;
}
const message = (error: unknown) => error instanceof Error ? error.message : 'Something went wrong. Check that the Aegis engine is running.';
const wait = (ms: number) => new Promise(resolve => window.setTimeout(resolve, ms));

export function useAssessmentWizard({ targets, refresh, onStarted, notify }: AssessmentProps) {
  const [step, setStep] = useState(0);
  const [target, setTarget] = useState<Target>();
  const [name, setName] = useState('');
  const [url, setUrl] = useState('');
  const [consent, setConsent] = useState(false);
  const [budget, setBudget] = useState(10);
  const [calibration, setCalibration] = useState<Target['calibration_config']>();
  const [session, setSession] = useState<CalibrationSession | null>(null);
  const [operation, setOperation] = useState<'auto' | 'click' | 'scan' | null>(null);
  const [error, setError] = useState('');
  const revision = useRef(0);
  const lock = useRef(false);
  useEffect(() => () => { revision.current++; }, []);

  // A selection is a snapshot, so a background target refresh cannot replace this draft.
  function changeTarget(next?: Target) {
    if (lock.current) return;
    revision.current++;
    setTarget(next); setName(next?.name || ''); setUrl(next?.url || '');
    setConsent(false); setCalibration(next?.calibration_config); setSession(null); setError('');
  }
  function edit(field: 'name' | 'url', value: string) {
    if (lock.current) return;
    revision.current++;
    setTarget(undefined); setConsent(false); setCalibration(undefined); setSession(null); setError('');
    if (field === 'name') setName(value); else setUrl(value);
  }
  function validate() {
    const normalized = normalizeUrl(url);
    if (!consent) throw new Error('Confirm that you own this target or have written permission to test it.');
    return normalized;
  }
  function navigate(next: number) {
    if (lock.current) return;
    setError('');
    try {
      if (next > step) {
        setUrl(validate());
        if (next > 1 && !calibration) throw new Error('Complete automatic or manual calibration before continuing.');
      }
      setStep(next);
    } catch (e) { setError(message(e)); }
  }
  async function calibrate(interactive: boolean) {
    if (lock.current) return;
    let targetUrl: string;
    try { targetUrl = validate(); } catch (e) { setError(message(e)); return; }
    lock.current = true;
    const version = revision.current;
    const current = () => revision.current === version;
    setError(''); setSession(null); setCalibration(undefined); setOperation(interactive ? 'click' : 'auto');
    try {
      const registered = target || await api.createTarget({ name: name.trim() || new URL(targetUrl).hostname, target_type: 'web', url: targetUrl });
      if (!current()) return;
      setTarget(registered); void refresh();
      if (!interactive) {
        const result = await api.autoCalibrate(registered.id);
        if (!current()) return;
        setCalibration(result.calibration_config);
      } else {
        let progress = await api.beginInteractiveCalibration(registered.id, 90);
        if (!current()) return;
        setSession(progress);
        const deadline = Date.now() + 95000;
        while (progress.status !== 'completed' && progress.status !== 'failed' && Date.now() < deadline) {
          await wait(300);
          if (!current()) return;
          progress = await api.calibrationStatus(registered.id, progress.session_id);
          if (!current()) return;
          setSession(progress);
        }
        let configWaits = 0;
        while (progress.status === 'completed' && !progress.calibration_config && configWaits < 20) {
          await wait(250);
          if (!current()) return;
          progress = await api.calibrationStatus(registered.id, progress.session_id);
          if (!current()) return;
          setSession(progress); configWaits++;
        }
        if (progress.status === 'failed') throw new Error(progress.error || 'Click calibration failed.');
        if (progress.status !== 'completed' || !progress.calibration_config) throw new Error('Calibration timed out before both target controls were selected.');
        setCalibration(progress.calibration_config);
      }
      void refresh(); notify('Calibration complete. Selectors saved to this target.');
    } catch (e) { if (current()) setError(message(e)); }
    finally { if (current()) { lock.current = false; setOperation(null); } }
  }
  async function start() {
    if (lock.current) return;
    setError('');
    try {
      validate();
      if (!target || !calibration) throw new Error('Calibrate this target before starting the scan.');
      if (!Number.isInteger(budget) || budget < 1 || budget > 10) throw new Error('Choose an attempt budget from 1 to 10.');
    } catch (e) { setError(message(e)); return; }
    lock.current = true; setOperation('scan');
    const version = revision.current;
    try {
      const scan = await api.startScan({ target_id: target!.id, category: 'LLM08', budget, authorized: consent });
      // Preserve acknowledged scans in App even if the analyst left this view while waiting.
      onStarted(scan, target);
    } catch (e) { if (version === revision.current) setError(message(e)); }
    finally { if (version === revision.current) { lock.current = false; setOperation(null); } }
  }
  return { step, target, name, url, consent, budget, calibration, session, operation, error,
    select: (id: string) => changeTarget(targets.find(item => item.id === id)), edit,
    setConsent, setBudget, navigate, calibrate, start };
}
