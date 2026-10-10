import { useState, useEffect } from 'react';

export function useScanStatus(scanId: string) {
  const [status, setStatus] = useState<any>(null);

  useEffect(() => {
    if (!scanId) return;
    fetch(`http://localhost:8765/api/v1/scans/${scanId}`)
      .then((res) => res.json())
      .then(setStatus)
      .catch(console.error);
  }, [scanId]);

  return status;
}
