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

export interface CitationItem {
  source: string;
  source_title?: string;
  risk_id?: string;
  section?: string;
  page?: number | string | null;
  chunk_id?: string | null;
  excerpt?: string | null;
}

export interface ChatMessage {
  role: 'assistant' | 'user';
  text: string;
  source_ids?: string[];
  citations?: CitationItem[];
}

export interface AssistantChatRequest {
  message: string;
  history?: ChatMessage[];
  mode?: 'ask' | 'simplify' | null;
  reply_to_message_id?: string | null;
}

export interface AssistantChatResponse {
  reply: string;
  source_ids: string[];
  citations: CitationItem[];
  mode: 'ask' | 'simplify';
}

export interface ReconStageDetail {
  status: 'completed' | 'partial' | 'skipped' | 'failed' | 'unknown';
  duration_ms?: number;
  warning?: string | null;
  details?: Record<string, any>;
}

export interface TargetProfile {
  target_id: string;
  has_rag?: { detected: boolean; confidence: number; evidence?: string[] };
  has_memory?: { detected: boolean; confidence: number; evidence?: string[] };
  renders_html?: { detected: boolean; confidence: number; evidence?: string[] };
  stages?: Record<string, ReconStageDetail>;
  warnings?: string[];
  inferred_at?: string;
}

export interface CategoryPlan {
  category: string;
  name: string;
  priority: number;
  status: string;
  budget: number;
  implementation_status?: 'implemented' | 'under_development';
  testability?: 'ready' | 'partial' | 'not_testable' | 'not_tested';
  applicability?: 'applicable' | 'not_applicable' | 'unknown';
  selectable?: boolean;
  reason?: string | null;
  applicable_prompt_ids?: string[];
  planned_prompt_ids?: string[];
}

export interface TestPlan {
  target_id: string;
  target_url?: string | null;
  total_budget: number;
  categories: CategoryPlan[];
  selectable_category_ids?: string[];
  plan_revision?: string;
  is_complete?: boolean;
  notes?: string[];
}

export interface AssistantStatusResponse {
  status: string;
  ollama_available: boolean;
  kb_chunks_indexed: number;
  embed_model: string;
  assistant_model: string;
}
