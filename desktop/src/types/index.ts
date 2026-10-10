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


