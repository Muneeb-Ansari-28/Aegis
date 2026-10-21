# Aegis Engine API Reference

Base URL: `http://localhost:8765/api/v1`

The default scan category is `LLM07` (System Prompt Leakage). Findings are evaluated using the planted canary and known-prompt overlap checks. Only use targets you own or have written permission to assess; jailbreak techniques are outside the active scope.

## Endpoints

- `GET /health` — Readiness and Ollama connection check
- `POST /targets` — Register a target
- `POST /targets/{id}/calibrate` — Calibrate DOM selectors
- `POST /scans/start` — Start an LLM07 scan
- `GET /scans/{id}` — Get scan status
- `GET /scans/{id}/turns` — Replay turns, including `status` (`success`, `error`, or `timeout`) and nullable `verdict`. Connector failures are not vulnerability verdicts. Older persisted connector-error markers are recognized without changing the database schema.
- `POST /scans/{id}/stop` — Abort active scan
- `GET /findings/{scan_id}` — Retrieve confirmed vulnerabilities
- `GET /reports/{scan_id}/pdf` — Generate and download PDF report
- `WS /ws/telemetry/{scan_id}` — Live WebSocket telemetry

Connector errors/timeouts terminate new scans as `FAILED`. A `turn_completed` event
can carry turn `status: "error"` or `"timeout"` and `verdict: null`; only successful
turns carry evaluated chatbot evidence. `scan_failed` includes diagnostic `error`
text. Consumers must distinguish turn status from scan lifecycle status. Failures
before the first turn (for example navigation failure) emit `scan_failed` without
creating a synthetic chatbot response.
