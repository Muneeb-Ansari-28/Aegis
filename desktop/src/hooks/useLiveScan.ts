import { useEffect, useMemo, useRef, useState } from 'react';
import { api, type ScanRecord, type ScanTurn } from '../api/client';
import { useScanSocket, type ScanEvent } from './useScanSocket';

export const isTerminal = (status: string) => ['COMPLETED', 'FAILED', 'STOPPED'].includes(status.toUpperCase());
const errorMessage = (error: unknown) => error instanceof Error ? error.message : 'Unable to reach the scan engine.';
const lifecycle: Record<string, string> = { scan_queued: 'QUEUED', scan_started: 'RUNNING', scan_completed: 'COMPLETED', scan_failed: 'FAILED', scan_stopped: 'STOPPED' };
export type LiveTurn = ScanEvent & { persisted?: boolean };

/** Monitor the selected scan independently of the visible page. Poll serially, never concurrently. */
export function useLiveScan(scan: ScanRecord | null, onStatus: (status: string) => void) {
  const id = scan?.scan_id || '';
  const [status, setStatus] = useState(scan?.status || 'UNKNOWN');
  const [confirmed, setConfirmed] = useState(false);
  const [attempt, setAttempt] = useState<number | null>(null);
  const [budget, setBudget] = useState(scan?.budget || 0);
  const [saved, setSaved] = useState<ScanTurn[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusError, setStatusError] = useState('');
  const [turnError, setTurnError] = useState('');
  const [stopError, setStopError] = useState('');
  const [stopState, setStopState] = useState<'idle' | 'sending' | 'requested'>('idle');
  const refreshPoll = useRef<() => void>(() => {});
  const terminal = useRef(false);
  const stopLock = useRef(false);
  const generation = useRef(0);
  const callback = useRef(onStatus);
  callback.current = onStatus;
  const { events, connection } = useScanSocket(id, !(confirmed && isTerminal(status)));

  useEffect(() => {
    generation.current++;
    terminal.current = false; stopLock.current = false;
    setStatus(scan?.status || 'UNKNOWN'); setConfirmed(false); setAttempt(null);
    setBudget(scan?.budget || 0); setSaved([]); setLoading(true);
    setStatusError(''); setTurnError(''); setStopError(''); setStopState('idle');
    // Scan identity, not App's status updates, resets this monitoring session.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    if (!id) { setLoading(false); return; }
    let alive = true;
    let timer: number | undefined;
    let inFlight = false;
    const poll = async () => {
      if (inFlight || !alive) return;
      inFlight = true;
      try {
        const next = await api.scanStatus(id);
        if (!alive) return;
        if (next.scan_id !== id) throw new Error('The engine returned a different scan identifier.');
        if (!terminal.current || isTerminal(next.status)) {
          terminal.current = isTerminal(next.status);
          setStatus(next.status.toUpperCase()); setConfirmed(true); callback.current(next.status);
        }
        if (Number.isFinite(next.current_attempt)) setAttempt(value => Math.max(value ?? 0, next.current_attempt));
        if (Number.isFinite(next.budget)) setBudget(next.budget);
        setStatusError('');
      } catch (error) { if (alive) setStatusError(errorMessage(error)); }
      if (!alive) return;
      try {
        const turns = await api.scanTurns(id);
        if (!alive) return;
        setSaved(previous => JSON.stringify(previous) === JSON.stringify(turns) ? previous : turns);
        setTurnError('');
      } catch (error) {
        if (alive) setTurnError(/404|not found/i.test(errorMessage(error)) ? 'Saved transcript is unavailable from this engine. Live telemetry remains visible.' : errorMessage(error));
      }
      if (!alive) return;
      setLoading(false);
      inFlight = false;
      // One final replay after terminal telemetry; no background polling after termination.
      if (!terminal.current) timer = window.setTimeout(() => void poll(), 1000);
    };
    refreshPoll.current = () => { window.clearTimeout(timer); void poll(); };
    void poll();
    return () => { alive = false; window.clearTimeout(timer); refreshPoll.current = () => {}; };
  }, [id]);

  useEffect(() => {
    const relevant = events.filter(event => event.scan_id === id);
    const lastLifecycle = [...relevant].reverse().find(event => lifecycle[event.event]);
    if (lastLifecycle && (!terminal.current || isTerminal(lifecycle[lastLifecycle.event]))) {
      const next = lifecycle[lastLifecycle.event];
      terminal.current = isTerminal(next); setStatus(next); setConfirmed(true); callback.current(next);
    }
    const attempts = relevant.map(event => event.attempt).filter((value): value is number => typeof value === 'number' && Number.isFinite(value));
    if (attempts.length) setAttempt(value => Math.max(value ?? 0, ...attempts));
    // turn_completed.status describes a turn, never the scan lifecycle.
  }, [events, id]);

  const turns = useMemo(() => {
    const map = new Map<number, LiveTurn>();
    for (const event of events) {
      if (event.scan_id !== id || !event.attempt || !['turn_started', 'turn_completed'].includes(event.event)) continue;
      const existing = map.get(event.attempt);
      if (existing?.event === 'turn_completed' && event.event === 'turn_started') continue;
      map.set(event.attempt, { ...existing, ...event });
    }
    for (const turn of saved) {
      const existing = map.get(turn.turn_index);
      map.set(turn.turn_index, { ...existing, scan_id: id, event: 'turn_completed', attempt: turn.turn_index,
        prompt: turn.prompt, response: turn.response, latency_ms: turn.latency_ms,
        strategy: turn.strategy || existing?.strategy, verdict: turn.verdict || existing?.verdict,
        timestamp: existing?.timestamp || turn.created_at || undefined, persisted: true });
    }
    return [...map.values()].sort((a, b) => (a.attempt || 0) - (b.attempt || 0));
  }, [events, saved, id]);

  async function stop() {
    if (!id || stopLock.current || terminal.current) return;
    const version = generation.current;
    stopLock.current = true; setStopState('sending'); setStopError('');
    try {
      const result = await api.stopScan(id);
      if (version !== generation.current) return;
      if (result.scan_id !== id) throw new Error('The stop response did not match this scan.');
      if (result.status === 'stop_requested') setStopState('requested');
      else if (isTerminal(result.status)) {
        terminal.current = true; setStatus(result.status.toUpperCase()); setConfirmed(true); callback.current(result.status.toUpperCase());
      } else throw new Error('The engine did not acknowledge the stop request.');
    } catch (error) {
      if (version === generation.current) { setStopError(errorMessage(error)); setStopState('idle'); stopLock.current = false; }
    }
  }
  const selectedEvents = useMemo(() => events.filter(event => event.scan_id === id), [events, id]);
  return { status, confirmed, attempt, budget, events: selectedEvents, turns, connection,
    loading, statusError, turnError, stopError, stopState, stop, refresh: () => refreshPoll.current() };
}
export type LiveScanState = ReturnType<typeof useLiveScan>;
