import { useEffect, useRef, useState } from 'react';

export interface ScanEvent {
  scan_id: string;
  event: string;
  status?: string;
  timestamp?: string;
  category?: string;
  attempt?: number;
  budget?: number;
  prompt?: string;
  response?: string;
  latency_ms?: number;
  strategy?: string;
  verdict?: { exploited?: boolean; rationale?: string; confidence?: number };
}

export function useScanSocket(scanId: string, enabled = true) {
  const [events, setEvents] = useState<ScanEvent[]>([]);
  const [connection, setConnection] = useState<'connecting' | 'connected' | 'disconnected' | 'closed'>('connecting');
  const seen = useRef(new Set<string>());

  useEffect(() => { setEvents([]); seen.current.clear(); }, [scanId]);

  useEffect(() => {
    if (!scanId || !enabled) { setConnection('closed'); return; }
    let alive = true;
    let socket: WebSocket;
    let retry: number | undefined;
    const connect = () => {
      setConnection('connecting');
      socket = new WebSocket(`ws://127.0.0.1:8765/api/v1/ws/telemetry/${encodeURIComponent(scanId)}`);
      socket.onopen = () => { if (alive) setConnection('connected'); };
      socket.onmessage = (event: MessageEvent<string>) => {
        if (!alive) return;
        try {
          const item = JSON.parse(event.data) as ScanEvent;
          if (!item || item.scan_id !== scanId || typeof item.event !== 'string') return;
          const key = JSON.stringify(item);
          if (seen.current.has(key)) return;
          seen.current.add(key);
          if (seen.current.size > 1000) seen.current.delete(seen.current.values().next().value!);
          setEvents(previous => [...previous, item].slice(-250));
        } catch { /* Malformed frames do not replace lifecycle polling. */ }
      };
      socket.onerror = () => { if (alive) setConnection('disconnected'); };
      socket.onclose = () => {
        if (!alive) return;
        setConnection('disconnected');
        retry = window.setTimeout(connect, 3000);
      };
    };
    connect();
    return () => { alive = false; window.clearTimeout(retry); socket.close(); };
  }, [scanId, enabled]);

  return { events, connection };
}
