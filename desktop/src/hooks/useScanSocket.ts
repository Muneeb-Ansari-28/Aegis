import { useEffect, useState } from 'react';

export function useScanSocket(scanId: string) {
  const [events, setEvents] = useState<any[]>([]);

  useEffect(() => {
    if (!scanId) return;
    const ws = new WebSocket(`ws://localhost:8765/api/v1/ws/telemetry/${scanId}`);
    ws.onmessage = (event) => {
      setEvents((prev) => [...prev, JSON.parse(event.data)]);
    };
    return () => ws.close();
  }, [scanId]);

  return events;
}
