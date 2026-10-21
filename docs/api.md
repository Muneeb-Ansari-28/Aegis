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
- `POST /scans/{id}/stop` — Request graceful stop at the next turn boundary
- `GET /findings/{scan_id}` — Retrieve confirmed vulnerabilities
- `GET /findings/{scan_id}/summary` - Severity counts, backend risk grade, persisted status and target/timestamp metadata
- `GET /findings/detail/{finding_id}` - Finding plus linked prompt/response, strategy and latency
- `GET /reports/{scan_id}/pdf` - Download cached PDF, or generate it when absent
- `GET /reports/{scan_id}/meta` - Generated PDF path, byte size, timestamp and SHA-256
- `POST /reports/{scan_id}/generate` - Explicitly generate/regenerate a PDF and return metadata
- `WS /ws/telemetry/{scan_id}` — Live WebSocket telemetry

Connector errors/timeouts terminate new scans as `FAILED`. A `turn_completed` event
can carry turn `status: "error"` or `"timeout"` and `verdict: null`; only successful
turns carry evaluated chatbot evidence. `scan_failed` includes diagnostic `error`
text. Consumers must distinguish turn status from scan lifecycle status. Failures
before the first turn (for example navigation failure) emit `scan_failed` without
creating a synthetic chatbot response.


## Results consumer and reporting limits

The active consumer is `desktop/src/views/FindingsInspector.tsx`, using `desktop/src/api/client.ts`. `FindingResponse`, `FindingDetail`, and `FindingsSummary` are defined in `engine/app/schemas/finding.py`; PDF schemas are in `schemas/report.py`. Detail latency is nullable in the backend schema. Missing findings/scan/detail resources return 404. Report generation rejects persisted QUEUED/RUNNING states with 409; unexpected generation failures return 500. Cached PDF download does not rerun generation validation. Metadata requires an existing report file.

List results are ordered by creation time; these endpoints do not offer severity/search sorting controls. An empty findings list does not prove a secure or fully evaluated target. Summary lifecycle status comes from the persisted scan row and may lag live in-memory status. Legacy error-marker verdict suppression applies to turn replay; it does not repair historical findings or cached reports. The reporting narrative's treatment of zero findings on failed/stopped scans remains a known limitation. No API change was made for the Milestone 5 UI; live acceptance is tracked in [project status](../Project-Context/Status.md).
