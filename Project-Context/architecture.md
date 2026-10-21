# Aegis System Architecture

This guide summarizes the system boundaries and contracts for the current eight-week delivery. The full product architecture remains in `Aegis-Architecture.pdf`; the delivery sequence and active category are defined by `Aegis_8-Week_Plan_with_MCP.md`.

## Active scope

The initial scanner assesses OWASP LLM07 System Prompt Leakage through direct, plain-language disclosure requests against authorized targets. The local weak and hardened chatbots use a fake system prompt with the `AEGIS-CANARY-7731` canary. Deterministic canary and n-gram overlap checks are combined with triage and rubric judging.

Jailbreaks, role impersonation, instruction overrides, encoding or obfuscation, safeguard bypass, and real secret extraction are out of scope. LLM01 and the other OWASP categories remain taxonomy references or future scope, not active scan categories.

## Core components and contracts

- FastAPI engine with deterministic orchestrator and scan state/budget handling.
- Playwright web connector producing the Unified Turn Record.
- Attack Agent uses fixed and templated direct requests with safe wording rephrases.
- Evaluation Agent combines deterministic checks, triage, and structured rubric verdicts.
- Risk scoring stays pure Python; MCP servers expose existing module functions as tools.
- Electron/React desktop client communicates with the engine over localhost REST and WebSocket.

## Website Scanning Module & Playwright Connector (Module 2)

The Playwright web connector (`engine/app/adapters/playwright_web.py`) bridges the deterministic orchestrator to web chatbot targets:
1. **Interface Detection:**
   - Heuristically detects input boxes (`textarea`, `input[type="text"]`, `[contenteditable]`), submit controls (`button#send`, `button[type="submit"]`, or `Enter` key fallback), and assistant response bubbles (`.chat-message.assistant`, `[data-message-author-role="assistant"]`, `#chat-box > *:last-child`).
   - Saved `TargetCalibrationConfig` selectors remain authoritative. Before submission, calibration and scanning share a bounded readiness check that opens a supported launcher only when necessary and verifies a visible, editable, actionable input.
   - Headed Chromium contexts follow the native window (`no_viewport=True`); non-persistent headless contexts retain the deterministic 1280x800 viewport. No machine-specific resolution or display scaling is configured.
2. **Prompt Dispatch & Submission:**
   - Clears, focuses, and fills the prompt into the target input locator.
   - Dispatches submission by clicking the submit button or issuing a synthetic `Enter` keypress on the input.
3. **Streaming-Aware Stabilization:**
   - Snapshots baseline response content before dispatch.
   - Periodically polls the assistant reply container (every 200ms) until text content ceases mutating across a stability threshold (e.g. 800ms), ensuring complete token-stream capture.
4. **Unified Turn Record Normalization:**
   - Formats every interaction into the canonical `TurnRecord` schema, tracking `turn_id`, `scan_id`, `turn_index`, `prompt`, `response`, `latency_ms`, `status` (`success`, `timeout`, `error`), and DOM metadata.
   - Only successful turns enter vulnerability evaluation. A connector error/timeout is persisted with diagnostic text and a null verdict, emitted as a failed turn, and terminates the scan as `FAILED`. No database migration is required. Replay exposes connector status and suppresses old verdicts attached to known connector-error markers without rewriting historical rows.
5. **DOM Calibration Flow (`web_calibration.py`):**
   - **Automated Calibration:** Detects input, Send, and response elements after opening the chatbot as necessary. The API uses a visible browser; headless calibration remains supported.
   - **Interactive Calibration:** Visible browser session injecting `CALIBRATION_OVERLAY_SCRIPT`, enabling user click-to-capture on input and Send. The response selector is detected automatically. The user still controls opening the chatbot during interactive capture. Both modes retain the existing saved selector format.

The complete planned folder layout and module gates are in the eight-week plan. Broader application scanning and packaging tracks are later work.
