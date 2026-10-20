// TypeScript contracts mirroring engine/app/schemas/
export interface TurnRecord {
  turn_id: string;
  scan_id: string;
  turn_index: number;
  prompt: string;
  response: string;
  status: string;
  latency_ms: number;
  strategy?: string;
  metadata?: Record<string, any>;
  timestamp?: string;
}

export interface JudgeVerdict {
  exploited: boolean;
  confidence: number;
  rationale: string;
  indicators_found: string[];
  canary_detected: boolean;
  overlap_score: number;
  category: string;
}
export interface FindingResponse {
  id: string;
  scan_id: string;
  turn_id: string;
  category: string;
  severity: string; // CRITICAL, HIGH, MEDIUM, LOW, INFO
  confidence: number;
  description: string;
  remediation?: string | null;
  created_at?: string | null;
}

export interface FindingDetail extends FindingResponse {
  prompt: string;
  response: string;
  turn_index: number;
  latency_ms?: number;
  strategy?: string | null;
}

export interface FindingsSummary {
  scan_id: string;
  total_findings: number;
  by_severity: Record<string, number>;
  risk_grade: number;
  scan_status: string;
  scan_category: string;
  target_name?: string | null;
  target_url?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
}

export interface ReportFinding {
  id: string;
  category: string;
  severity: string;
  confidence: number;
  description: string;
  remediation?: string | null;
  turn_index: number;
  prompt: string;
  response: string;
  latency_ms?: number;
  strategy?: string | null;
}

export interface ReportMeta {
  scan_id: string;
  report_path: string;
  file_size_bytes: number;
  created_at: string;
  sha256?: string | null;
}

export interface ReportData {
  scan_id: string;
  target_name: string;
  target_url: string;
  category: string;
  scan_status: string;
  started_at?: string | null;
  completed_at?: string | null;
  total_turns: number;
  total_findings: number;
  risk_grade: number;
  severity_breakdown: Record<string, number>;
  findings: ReportFinding[];
  executive_summary: string;
  methodology: string;
  generated_at: string;
}
