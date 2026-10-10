# Aegis Engine API Reference

Base URL: `http://localhost:8765/api/v1`

The default scan category is `LLM07` (System Prompt Leakage). Findings are evaluated using the planted canary and known-prompt overlap checks. Only use targets you own or have written permission to assess; jailbreak techniques are outside the active scope.

## Endpoints

- `GET /health` — Readiness and Ollama connection check
- `POST /targets` — Register a target
- `POST /targets/{id}/calibrate` — Calibrate DOM selectors
- `POST /scans/start` — Start an LLM07 scan
- `GET /scans/{id}` — Get scan status
- `POST /scans/{id}/stop` — Abort active scan
- `GET /findings/{scan_id}` — Retrieve confirmed vulnerabilities
- `GET /reports/{scan_id}/pdf` — Generate and download PDF report
- `WS /ws/telemetry/{scan_id}` — Live WebSocket telemetry
