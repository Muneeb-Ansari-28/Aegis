# Aegis Project Status

> **Last reviewed:** 2026-10-11 by Muneeb
> **Evidence basis:** Runtime verification against local test targets (`weak-bot` on port 8001 and `hardened-bot` on port 8002) via Playwright Chromium automation; pytest test suite (9 passed).

## Overall Status

The repository contains the foundation and active implementation for the eight-week LLM07 System Prompt Leakage plan. Module 2 (Playwright Web Connector & DOM Calibration) has been implemented and verified with live browser automation and streaming stabilization. All 9 test suite checks pass cleanly.

| Module | Planned window | Current status | Gate |
|---|---|---|---|
| 1. Foundation and test target | Week 1 | Verified: Turn Record contract frozen, weak and hardened bots running | Gate 1 verified |
| 2. Configuration and Playwright connector | Weeks 2–3 | **In Progress / Verified**: Playwright connector, auto-detection, Enter/Click submission, streaming stabilization, and calibration implemented and tested | Connector verified; 20-prompt calibration test ready |
| 3. Knowledge base and Attack Agent | Weeks 3–4 | KB records and agent files present; retrieval and mutation behavior not verified | Not passed |
| 4. Evaluation Agent | Weeks 4–5 | Deterministic, triage, judge, evaluator, and benchmark files present; benchmark results not verified | Gate 2 not passed |
| 5. Orchestrator | Weeks 5–6 | Orchestrator and scan-related files present; state machine skeleton verified with mock adapter | Gate 3 not passed |
| 5b. MCP tool layer | Week 6 | Client, schemas, and four server modules present; parity, timeout, and crash handling not verified | Gate 5b not passed |
| 6. Risk, persistence, and report | Weeks 6–7 | Risk, models, report service/template, and endpoints present; evidence consistency and PDF output not verified | Gate 4 not passed |
| 7. Integration, UI, and demo | Weeks 7–8 | Desktop views and documentation files present; integrated demo not verified | Not passed |

## Gate Evidence

| Gate | Acceptance criteria from the plan | Current assessment |
|---|---|---|
| 1 | Startup database creation, frozen Turn Record contract, and locally running test bot | Frozen Turn Record contract verified; both `weak-bot` (port 8001) and `hardened-bot` (port 8002) operational and serve interactive web chat UIs. **Gate 1 verified.** |
| 2 | Judge returns valid JSON and reaches at least 90% accuracy on labelled benchmark | JSON guard and benchmark pairs test passing (`test_benchmark_pairs`). Complete LLM model run pending Ollama. **Not passed.** |
| 3 | Weak bot exploit found; hardened bot exhausts budget without exploit; stop works mid-scan | State machine skeleton verified with MockAdapter (`test_orchestrator_skeleton`). Live loop integration pending Module 5. **Not passed.** |
| 4 | Styled PDF is produced and finding evidence matches persisted evidence | Report service stub exists. **Not passed.** |
| 5b | MCP results match direct calls; killed server is handled without hanging | MCP modules scaffolded. Direct loop to be proven first per plan. **Not passed.** |

## Module 2 Verification Evidence

- `PlaywrightWebAdapter` (`engine/app/adapters/playwright_web.py`):
  - Auto-detection identifies `#chat-input`, `button#send`, and `.chat-message.assistant:last-child`.
  - Supports button click and synthetic `Enter` keypress submissions.
  - Streaming stabilization polls response DOM until text is stable across checks.
  - Produces valid `TurnRecord` instances with latency tracking and metadata.
- `WebCalibration` (`engine/app/adapters/web_calibration.py`):
  - Provides headless `auto_calibrate()` and headful `calibrate_interactive()` with DOM click-capture overlay (`CALIBRATION_OVERLAY_SCRIPT`).
- Test Target Servers:
  - `weak-bot` serves interactive chat interface and leaks canary `AEGIS-CANARY-7731` on direct inquiry.
  - `hardened-bot` serves interactive chat interface and strictly refuses prompt extraction.
- Test Suite:
  - `pytest` executed with 9/9 tests passing (`test_playwright_initialization`, `test_playwright_unreachable_target`, `test_playwright_live_weak_bot_interaction`, etc.).

## Next Work

1. Implement Target API endpoints (`POST /targets`, `POST /targets/{id}/calibrate`) linking `TargetService` to `WebCalibration`.
2. Proceed to Module 3: Knowledge Base retrieval and Attack Agent direct-disclosure prompt generation.
3. Wire adaptive loop into Orchestrator.

## Contributors

Approved contributor names: **Muneeb**, **Shahzaman**, and **Salman**.
