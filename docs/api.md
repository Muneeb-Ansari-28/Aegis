# Aegis Engine API Reference

Base URL: `http://127.0.0.1:8765/api/v1`

Aegis provides REST and WebSocket APIs for target management, multi-tier reconnaissance, deterministic test planning, scan execution, and audit report generation.

Private APIs accept loopback Host headers only and require the Aegis UI session cookie (bootstrapped from an exact trusted local UI origin) or the process token. Untrusted browser origins are rejected. `GET /health` is public and returns readiness only.

## Endpoints

### System & Health
- `GET /health` — Readiness check and Ollama daemon connectivity.
- `GET /assistant/status` — Operational status of RAG assistant, model availability, and indexed chunk count.
- `POST /assistant/chat` — Conversational assistant queries grounded in OWASP Top 10 2026.

### Targets & Calibration
- `POST /targets` — Register a new scan target (URL and name).
- `GET /targets` — List all registered targets.
- `GET /targets/{id}` — Retrieve target details and calibration configuration.
- `POST /targets/{id}/calibrate/auto` — Automatic DOM selector detection via Playwright.
- `POST /targets/{id}/calibrate/interactive` — Start interactive two-click calibration.
- `GET /targets/{id}/calibrate/interactive/{session_id}` — Poll interactive calibration progress.
- `POST /targets/{id}/calibrate` — Save custom CSS selectors.

### Reconnaissance & Planning
- `POST /targets/{id}/recon` — Generate a `TargetProfile`. The JSON body supports `project_path` (explicit opt-in Tier 3 local inspection), `run_probes` (defaults to `false`), and `authorized` (must be `true` before active probes can run). Passive profiling and loopback inspection do not submit chat prompts.
- `GET /targets/{id}/profile` — Fetch saved target capability profile.
- `GET /targets/local/discover` — Scan active listening loopback dev ports.
- `POST /targets/{id}/plan` — Generate deterministic `TestPlan` across all 10 OWASP 2026 categories with plan revision hash and selectable category IDs.

### Scans & Execution
- `POST /scans/start` — Start a scan with:
  ```json
  {
    "target_id": "uuid",
    "category": "LLM08",
    "category_ids": ["LLM08"],
    "plan_revision": "sha256-hash",
    "budget": 10,
    "authorized": true
  }
  ```
  Validates authorization, saved complete recon profile, current plan revision, and that every requested canonical category ID is selectable. Budgets are per category; the total budget is multiplied by the number of selected categories.
- `GET /scans/{id}` — Poll current scan status and attempt progress.
- `GET /scans/{id}/turns` — Replay recorded turns with latency and evaluation verdicts.
- `POST /scans/{id}/stop` — Graceful scan termination at the next turn boundary.
- `WS /ws/telemetry/{scan_id}` — Real-time telemetry events (`turn_started`, `turn_completed`, `scan_completed`, `scan_failed`).

### Findings & Reporting
- `GET /findings/{scan_id}` — Retrieve confirmed vulnerability findings.
- `GET /findings/{scan_id}/summary` — Severity breakdown and risk grade.
- `GET /findings/detail/{finding_id}` — Detailed finding with linked prompt and response.
- `POST /reports/{scan_id}/generate` — Generate styled PDF executive report. FAILED, PARTIAL, STOPPED, INTERRUPTED, or zero-turn scans are truthfully marked as **INCONCLUSIVE**.
- `GET /reports/{scan_id}/pdf` — Download cached PDF report. Strict path validation prevents path traversal outside the user AppData directory.
- `GET /reports/{scan_id}/meta` — Report file metadata and SHA-256 digest.
