import { useEffect, useState } from 'react';

export interface ScanEvent {
  scan_id: string;
  event: string;
  status?: string;
  error?: string;
  timestamp?: string;
  category?: string;
  category_ids?: string[];
  category_results?: import('../api/client').CategoryRunStatus[];
  attempt?: number;
  budget?: number;
  prompt?: string;
  response?: string;
  latency_ms?: number;
  strategy?: string;
  verdict?: { exploited?: boolean; rationale?: string; confidence?: number };
}

export function useScanSocket(scanId: string): ScanEvent[] {
  const [events, setEvents] = useState<ScanEvent[]>([]);

  useEffect(() => {
    setEvents([]);
    if (!scanId) return;
    const wsHost = window.location.hostname === '127.0.0.1' ? '127.0.0.1' : 'localhost';
    const ws = new WebSocket(`ws://${wsHost}:8765/api/v1/ws/telemetry/${scanId}`);
    ws.onmessage = (event: MessageEvent<string>) => {
      try {
        const item = JSON.parse(event.data) as ScanEvent;
        setEvents(previous => [...previous, item].slice(-250));
      } catch {
        // Ignore malformed telemetry frames; the scan lifecycle API remains available.
      }
    };
    return () => ws.close();
  }, [scanId]);

  return events;
}
