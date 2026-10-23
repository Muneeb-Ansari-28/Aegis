import type {
  FindingDetail,
  FindingResponse,
  FindingsSummary,
  ReportMeta,
  AssistantChatRequest,
  AssistantChatResponse,
  AssistantStatusResponse,
} from '../types';

const BASE_URL = 'http://localhost:8765/api/v1';

export interface TargetCalibration {
  input_selector: string;
  submit_selector: string;
  response_selector: string;
  wait_timeout_ms?: number;
}
export interface CalibrationSession {
  session_id: string;
  target_id: string;
  status: string;
  step: number;
  input_selected: boolean;
  enter_selected: boolean;
  calibration_config?: TargetCalibration | null;
  error?: string | null;
}
export interface Target {
  id: string;
  name: string;
  target_type: string;
  url: string;
  calibration_config?: TargetCalibration | null;
}
export interface ScanRecord {
  scan_id: string;
  target_id: string;
  status: string;
  category: string;
  budget: number;
}
export interface ScanTurn {
  turn_index: number;
  prompt: string;
  response: string;
  status?: string;
  latency_ms: number;
  strategy?: string | null;
  verdict?: { exploited?: boolean; rationale?: string; confidence?: number } | null;
  created_at?: string | null;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  });
  if (!response.ok) {
    let message = `Engine request failed (${response.status})`;
    try {
      const body = await response.json() as { detail?: string | Array<{ msg?: string }> };
      if (typeof body.detail === 'string') message = body.detail;
      else if (Array.isArray(body.detail)) message = body.detail.map(x => x.msg).filter(Boolean).join('; ') || message;
    } catch { /* Keep the HTTP status when the response has no JSON body. */ }
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; ollama_connected: boolean }>('/health'),
  targets: () => request<Target[]>('/targets'),
  createTarget: (payload: { name: string; target_type: string; url: string; calibration_config?: TargetCalibration }) =>
    request<Target>('/targets', { method: 'POST', body: JSON.stringify(payload) }),
  autoCalibrate: async (id: string) => request<{ status: string; calibration_config: TargetCalibration }>(`/targets/${id}/calibrate/auto`, { method: 'POST' }),
  beginInteractiveCalibration: (id: string, timeoutSec: number) => request<CalibrationSession>(`/targets/${id}/calibrate/interactive?timeout_sec=${timeoutSec}`, { method: 'POST' }),
  calibrationStatus: (id: string, sessionId: string) => request<CalibrationSession>(`/targets/${id}/calibrate/interactive/${sessionId}`),
  saveCalibration: (id: string, calibration: TargetCalibration) => request<{ status: string; target_id: string }>(`/targets/${id}/calibrate`, { method: 'POST', body: JSON.stringify(calibration) }),
  startScan: (payload: { target_id: string; category: string; budget: number; authorized: boolean }) => request<ScanRecord>('/scans/start', { method: 'POST', body: JSON.stringify(payload) }),
  scanStatus: (id: string) => request<{ scan_id: string; status: string; current_attempt: number; budget: number; exploited: boolean }>(`/scans/${id}`),
  scanTurns: (id: string) => request<ScanTurn[]>(`/scans/${id}/turns`),
  stopScan: (id: string) => request<{ status: string; scan_id: string }>(`/scans/${id}/stop`, { method: 'POST' }),
  findings: (scanId: string) => request<FindingResponse[]>(`/findings/${scanId}`),
  findingsSummary: (scanId: string) => request<FindingsSummary>(`/findings/${scanId}/summary`),
  findingDetail: (findingId: string) => request<FindingDetail>(`/findings/detail/${findingId}`),
  reportMeta: (scanId: string) => request<ReportMeta>(`/reports/${scanId}/meta`),
  generateReport: (scanId: string) => request<ReportMeta>(`/reports/${scanId}/generate`, { method: 'POST' }),
  downloadReport: async (scanId: string): Promise<void> => {
    const response = await fetch(`${BASE_URL}/reports/${scanId}/pdf`);
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Report download failed' }));
      throw new Error(err.detail || 'Report download failed');
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `aegis-report-${scanId.slice(0, 8)}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  },
  chatAssistant: (req: AssistantChatRequest) =>
    request<AssistantChatResponse>('/assistant/chat', {
      method: 'POST',
      body: JSON.stringify(req),
    }),
  getAssistantStatus: () => request<AssistantStatusResponse>('/assistant/status'),
};

// Lightweight local guidance keeps the assistant useful without sending target data to a model.
export function assist(question: string, scans: number): string {
  const q = question.toLowerCase();
  if (q.includes('calibrat') || q.includes('click')) return 'Open New assessment, enter a local target URL, then choose Automatic calibration or Click to calibrate. Click calibration opens a visible Playwright browser. Click the chatbot input, then click its Enter or Send button. Aegis checks off each step and detects the response area automatically.';
  if (q.includes('owasp') || q.includes('categor')) return 'LLM08 Hidden Context Exposure is the active assessment module. The other OWASP LLM Top 10 categories are displayed for planning, but their scan pipelines are not implemented yet. LLM08 uses direct, plain-language disclosure requests against fabricated test content.';
  if (q.includes('scan') || q.includes('history') || q.includes('result')) return `There ${scans === 1 ? 'is' : 'are'} ${scans} scan${scans === 1 ? '' : 's'} in your local history. Open Live scan to follow prompts and responses as the visible Playwright browser submits them. LLM08 Hidden Context Exposure is currently the supported scan category.`;
  if (q.includes('desktop') || q.includes('app')) return 'The desktop UI Automation adapter is scaffolded, but native desktop target scanning is not implemented yet. Web targets use the Playwright connector. Choose Web application to run the currently supported workflow.';
  if (q.includes('consent') || q.includes('authoriz')) return 'Only assess systems you own or have written permission to test. Confirm authorization on the scan setup screen before calibrating or starting a scan. Target interactions and results should be handled as sensitive local data.';
  return 'I can help with Playwright browser calibration, the active LLM08 assessment scope, authorization, and the current scan lifecycle. Try asking “How do I calibrate a web target?” or “Which OWASP categories are available?”';
}
