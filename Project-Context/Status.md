# Aegis Project Status

## Current review snapshot - 2026-10-23 (RAG AI Assistant Implementation)

The local-first RAG AI Assistant is fully implemented and operational across the backend engine (`:8765`) and desktop frontend (`:3000`), following `rag-assistant-guide.md` and `OWASP-LLM-Top-10-2026.md`:
- **Knowledge Base**: Curated OWASP Top 10 for LLM Applications (2026) markdown placed in `engine/knowledge/owasp/` alongside 8 verified Aegis operational documents in `engine/knowledge/aegis/`.
- **Vector Store & Embeddings**: Ingested 115 semantic chunks with deterministic IDs into persistent ChromaDB (`%APPDATA%\Aegis\chroma`) using `nomic-embed-text:latest` over Ollama with task-prefixing (`search_document:` / `search_query:`). Repeatable CLI ingestion via `scripts/ingest_kb.py` and `scripts/build_kb_index.py`.
- **Grounded Assistant Agent**: Implemented `AssistantAgent` with strict capability honesty (transparently distinguishes full knowledge of all 10 OWASP risks from active scan execution coverage limited to LLM08), prompt templates in `engine/app/agents/prompts/` (Rule 2.6), inline citations (`[LLM08:2026, p.47]`), relevance cutoff fallback (`NO_DOCS_REPLY`), query normalization with 2025-to-2026 crosswalk, and explain-simply mode utilizing companion chunks and everyday analogies.
- **API & Desktop Integration**: Added `/api/v1/assistant/chat` and `/api/v1/assistant/status` endpoints, TypeScript contracts mirroring Pydantic schemas, and wired desktop chat UI with citation chips and per-message "Explain simply" buttons.
- **Verification Evidence**: All 10 unit tests in `test_rag_assistant.py` pass; all 8 integration tests in `test_assistant_api.py` pass (including all 10 OWASP categories, crosswalk, capability honesty, calibration, out-of-scope fallback, and simplify mode); desktop production build (`npm run build`) passes with 0 errors.

## Prior review snapshot - 2026-10-22 (OWASP 2026 Taxonomy Migration)

The active assessment category is migrated to **OWASP LLM08 Hidden Context Exposure** following the newly released OWASP GenAI/LLM Top 10 (2026) canonical taxonomy. The 2025 taxonomy entries are preserved for reference under `engine/app/kb/01_OWASP/2025/`, and `KBLoader` defaults to `2026`. All 10 canonical 2026 categories (LLM01-LLM10) and base risk weights are wired into `RiskScorer.WEIGHTS`, `risk_rules.json`, `test_cases.json`, and backend schemas (`ScanCreate`, `ScanEntity`, `JudgeVerdict`).
The active scanner pipeline, evaluator, judge rubric (`judge_rubric_llm08.md`), reporting agent, HTML/PDF reporting templates, test targets, and desktop frontend (`desktop/src/App.tsx`, `NewAssessment.tsx`, `useAssessmentWizard.ts`, `FindingsInspector.tsx`, `Overview.tsx`) are fully updated to `LLM08`.
Gate 4 verification (`scripts/verify_gate4.py`) was re-verified with 10/10 checks passing against live weak-bot, SQLite persistence, and generated PDF evidence fidelity. All 57 backend tests pass (100% green); desktop production build (`npm run build`) passes with 0 errors.

## Prior review snapshot - 2026-10-21

Documentation checked against the current `shahzaman` checkout. This snapshot takes precedence over dated checkpoints below; those records describe the evidence and state at their original time.

| Frontend milestone | Current assessment |
|---|---|
| 1. Application Shell and Sidebar | Implemented; prior user visual approval recorded. No changes in Milestone 5. |
| 2. Dashboard / Overview | Implemented; prior user visual approval recorded. Results navigation retained. |
| 3. New Assessment Wizard | Four steps implemented; prior user visual approval recorded. No changes in Milestone 5. |
| 4. Live Scan redesign | Earlier conversation approval does not prove retention in this checkout. Current `App.tsx` contains the existing `LiveScanPage` / Scan activity UI, not the approved tabbed/current-step redesign. Reconcile the reverted work separately; no restoration was attempted. |
| 5. Results & Findings redesign | Implemented, awaiting visual approval and required live integration acceptance. Not fully completed or approved. |

Milestone 5 feature scope and executed build/browser checks are recorded in the dated Milestone 5 entry below. Its source changes remain uncommitted. This documentation-only review reran no builds, browser checks, backend tests, calibration, scans, or PDF generation. Earlier build/fixture outcomes are historical evidence, not fresh results from this review. Existing backend report/evidence tests establish their documented service/fixture coverage, not full desktop acceptance.

### Remaining gaps and next steps

1. Obtain visual review of the Results layout; exact visual parity has not been claimed or approved.
2. Verify Results navigation, selected-scan changes, evidence, and PDF download against real persisted scans in a working engine environment; then complete the desktop-to-engine scan/calibration acceptance flow. Earlier service-path scanning and automatic-calibration evidence does not replace this.
3. Extend checks for loading transitions, delayed scan-switch responses, evidence-detail retry, all terminal statuses, keyboard/zoom/screen-reader behavior, Electron and other browsers. Those cases are not all covered by the recorded Milestone 5 fixtures.
4. Findings filtering/sorting, evidence copy, report preview/regeneration controls, continuous Results refresh and engine-wide history discovery remain unimplemented. History is a browser-local index capped at 100 entries.
5. Backend follow-up requires separate authorization: zero-finding PDF narratives can overstate stopped/failed assessments; legacy connector-error findings can remain in summaries/PDFs although replay suppresses their verdicts; cached PDFs are reused; findings-summary lifecycle status may lag the live status endpoint. Frontend TypeScript/Pydantic nullable detail-latency alignment also remains an audit issue. No fix is implied by documenting these limitations.
6. Reconcile the current Live Scan implementation with the previously approved Milestone 4 before declaring all frontend screens complete. No next milestone, commit or push is authorized by this review.

## Historical baseline and dated checkpoints

The older overall/gate/next-work assessments below are preserved for history. The current snapshot and later dated evidence supersede obsolete port-conflict blockers, blanket statements that persistence/reporting are unverified, and old pending-review statuses. Backend benchmark/MCP and full integration acceptance still require their own evidence.

> **Last reviewed:** 2026-10-14 by Muneeb
> **Evidence basis:** Frontend TypeScript/Vite production build passed; scan lifecycle mock tests (3/3) passed; connector initialization and unreachable-target checks (2/2 selected) passed. Calibration verified against the user-provided local test site at 127.0.0.1:5173. Desktop calibration UI end-to-end run passes 17/17 automated checks (consent gate, automatic calibration, click-calibration tick checklist, URL normalization) against a local fixture target; the click-calibration session race and target-deletion persistence were fixed. Connector initialization/unreachable checks and scan lifecycle mock tests pass; port 8001 currently serves an unrelated site.

## Overall Status

The repository contains the foundation and active implementation for the eight-week assessment plan, targeting canonical OWASP 2026 LLM08 Hidden Context Exposure (migrated from 2025 LLM07). Frontend production build and mock scan lifecycle tests pass. Gate 4 evidence fidelity verified against weak-bot.

| Module | Planned window | Current status | Gate |
|---|---|---|---|
| 1. Foundation and test target | Week 1 | Verified: Turn Record contract frozen, weak and hardened bots running | Gate 1 verified |
| 2. Configuration and Playwright connector | Weeks 2Ã¢â‚¬â€œ3 | Automatic and two-step click calibration are implemented with session polling. Session completion race fixed: sessions report `saving_selectors` after capture and `completed` only once selectors are persisted, so a completed session always carries `calibration_config`. Full browser capture is pending a live target test. | Connector partly verified; calibration flow pending |
| 3. Knowledge base and Attack Agent | Weeks 3ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“4 | KB fixed/template prompts feed the Attack Agent; Ollama generates plain-language rephrases. Live Ollama behavior not verified | Not passed |
| 4. Evaluation Agent | Weeks 4ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“5 | RubricJudge calls Ollama and validates JudgeVerdict JSON; benchmark accuracy not verified | Gate 2 not passed |
| 5. Orchestrator | Weeks 5Ã¢â‚¬â€œ6 | Scan start/status/stop dispatch, turn persistence, and prompt telemetry are connected to the visible Playwright adapter. Mock lifecycle tests pass. | Gate 3 not passed |
| 5b. MCP tool layer | Week 6 | Client, schemas, and four server modules present; parity, timeout, and crash handling not verified | Gate 5b not passed |
| 6. Risk, persistence, and report | Weeks 6–7 | Findings service and SQLite persistence verified; RiskScorer computes deterministic severity; ReportingAgent aggregates narrative; ReportService generates styled PDF via xhtml2pdf; Reports API delivers downloads; Gate 4 end-to-end evidence fidelity verified against weak-bot (39/39 tests pass). | Gate 4 verified |
| 7. Integration, UI, and demo | Weeks 7–8 | UI connects calibration and scan lifecycle APIs, includes live prompt/response, FindingsInspector view with Overview/Findings/Evidence/Timeline tabs, and PDF export action. Desktop scanning remains unavailable; integrated browser demo is pending. | Not passed |

## Gate Evidence

| Gate | Acceptance criteria from the plan | Current assessment |
|---|---|---|
| 1 | Startup database creation, frozen Turn Record contract, and locally running test bot | Frozen Turn Record contract is verified. Current availability of the test bots was not verified in this run; port 8001 serves an unrelated local application. Recheck target availability before claiming the live target gate. |
| 2 | Judge returns valid JSON and reaches at least 90% accuracy on labelled benchmark | JSON guard and benchmark pairs test passing (`test_benchmark_pairs`). Complete LLM model run pending Ollama. **Not passed.** |
| 3 | Weak bot exploit found; hardened bot exhausts budget without exploit; stop works mid-scan | Stop, turn persistence, finding creation, and telemetry behavior pass mock tests (`test_scan_flow.py`, 3 passed). Live weak/hardened target acceptance and database-backed end-to-end scan are unverified. **Not passed.** |
| 4 | Styled PDF is produced and finding evidence matches persisted evidence | **Verified.** Styled PDF report generated with xhtml2pdf and Jinja2 template (`engine/app/templates/report.html`). Text extracted from generated PDF verified with 100% fidelity against SQLite DB (scan_id, target name, LLM08 category, canary token `AEGIS-CANARY-7731`, trigger prompt, response evidence, severity, and risk grade). Verified via `test_report_generation.py` (2 passed) and `scripts/verify_gate4.py` (10/10 checks passed). |
| 5b | MCP results match direct calls; killed server is handled without hanging | MCP modules scaffolded. Direct loop to be proven first per plan. **Not passed.** |

## Module 2 Verification Evidence

- `PlaywrightWebAdapter` (`engine/app/adapters/playwright_web.py`):
  - Auto-detection identifies `#chat-input`, `button#send`, and `.chat-message.assistant:last-child`.
  - Supports button click and synthetic `Enter` keypress submissions.
  - Streaming stabilization polls response DOM until text is stable across checks.
  - Produces valid `TurnRecord` instances with latency tracking and metadata.
- `WebCalibration` (`engine/app/adapters/web_calibration.py`):
  - Provides automatic calibration and visible two-control click calibration with session progress callbacks. The response selector is detected automatically after input and send controls are selected; The updated browser click flow is verified against the supplied local target; broader target compatibility remains open.
- Test Target Servers:
  - `weak-bot` serves interactive chat interface and leaks canary `AEGIS-CANARY-7731` on direct inquiry.
  - `hardened-bot` serves interactive chat interface and strictly refuses prompt extraction.
- Current checks: `test_scan_flow.py` passes 3/3; connector initialization and unreachable-target tests pass 2/2 selected. `test_playwright_live_weak_bot_interaction` was not verified because port 8001 serves another local application. Frontend `npm run build` passes.

- Calibration UX fixes verified 2026-10-14: authorization errors render inside the calibration box with the consent card highlighted and scrolled into view, scheme-less URLs normalize to `http://`, and the click checklist ticks "Click on the input area" then "Click on the Enter / Send button" as each control is captured. End-to-end automated run: 17/17 checks passed against a local fixture target; `npm run build` passes; engine suite 10 passed with the pre-existing port-8001 conflict only.

## Next Work

1. Run the integrated calibration and scan flow against the weak and hardened local targets when port 8001 is available.
2. Add database migrations and verify scan, turn, and finding persistence end to end.
3. Implement the desktop UI Automation connector, then verify the web and desktop assessment flows in the integrated demo.
4. Run the live Ollama judge benchmark and verify weak/hardened target gate criteria.

## Contributors

Approved contributor names: **Muneeb**, **Shahzaman**, and **Salman**.

## Frontend Design V1 — Milestone 1 (2026-10-17)

**Module:** Module 7: Integration, UI, and Demo — application shell and design system.
**State:** Shell implemented and frontend checks passed; awaiting user review before individual page redesigns. Branch: `shahzaman`; no commit, push, merge or PR.

- Added a reusable presentation-only application shell, graphite semantic tokens, shared panel/button/heading styles, sidebar/header, active/focus/hover states, compact modal navigation and reduced-motion support.
- Modified frontend files: `desktop/src/App.tsx`, `desktop/src/index.css`; added `desktop/src/components/ApplicationShell.tsx`. Updated the approved `frontend-design.md` and appended this status and the implementation log.
- Verified `npm run build` (TypeScript + Vite), unchanged page components and scanner state/handlers by Git comparison, Chromium shell/navigation at 320/390/768/1024/1440px, keyboard modal behavior, draft preservation, consent guard, profile and assistant. No browser runtime exceptions in these checks.
- Isolated browser API/WebSocket fixtures passed registration, URL normalization, auto/click-calibration UI, authorized start payload, live navigation, polling, telemetry, transcript replay, history/filter and stop checks. Fixtures never entered application source or the real engine.
- **Gate impact:** Frontend milestone verification passes within this scope. Module 7 integrated demo and backend gates remain unverified by this change. The engine was offline; live calibration, scanning, Ollama and stop integration were not run. Electron, screen-reader/full contrast/zoom audits and non-Chromium browsers were not tested. Existing Vite CJS deprecation warning remains.
- **Remaining:** User review; individual page redesign/reflow and page-specific accessibility improvements. Narrow page content may scroll horizontally within the responsive shell. No dashboard or other page redesign begun.


### Milestone 1 review refinement — 2026-10-17

Removed redundant desktop sidebar spacing in `desktop/src/index.css` and prevented section shrinkage. Automatic overflow scrolling remains available. Frontend build passed. Chromium layout checks passed at 1366px width and heights 400/500/600/650/720/768/900, including an additional Live scan-sized DOM fixture. No overflow at 650px tall with the extra item, or 600px without it. Bottom footer/services/profile access and keyboard focus verified on short windows; compact drawer checked at 390x400. No page or scanner code changed. Live integration not rerun for this CSS-only refinement; no backend gate change.


### Sidebar scrollbar visibility correction — 2026-10-17

Scoped native scrollbar hiding to the desktop sidebar only, retaining fixed width and automatic overflow scrolling. Build passed. Chromium desktop/short-window screenshots inspected (1366x768, 1366x400 top and bottom). Wheel/keyboard scrolling, bottom status/profile access, main scrolling and compact drawer checks passed. Firefox/WebKit, physical touchpad and Electron runtime not tested. Scanner code unchanged; no live scan rerun or backend gate update.


## Frontend Design V1 — Milestone 2 (2026-10-17)

**Module:** Module 7: Integration, UI, and Demo — Overview redesign.
**State:** Implemented and locally verified; awaiting user visual review. Milestone 1 was approved and published as `75d4c570ca38227d5ae3dc036d65ccb67930e09a`; this milestone is uncommitted.

- Compact profile-aware header, truthful local metrics, Recent Assessments table, System Health and supported Quick Actions. Scoped component/styles preserve the existing shell and other pages.
- `npm run build` passes (existing Vite CJS warning). Chromium checks pass empty/offline/populated/connected/disconnected and initial loading presentation, existing dashboard actions, health refresh, local counts, selected-scan Open and table keyboard focus. Body/content widths checked at 320/390/768/1024/1280/1440px; desktop and mobile screenshots inspected.
- A populated-table mobile overflow caused by the hidden action-column label was corrected by containing it in the table scroll region. Initial build unused imports were corrected. One loading-fixture cleanup failed in the test harness; loading text had passed, and refresh/scan navigation checks passed separately with corrected fixture handling.
- Scanner and other page handlers unchanged by source comparison. Live backend/calibration/scans, Electron, non-Chromium and full accessibility audits not verified; no backend gate newly passed. Stop after this milestone for review.


### Milestone 2 visual correction — 2026-10-17

Initial Dashboard was not visually approved. Reworked only Overview presentation to reproduce Panel 1's compact left working area and right illustration/context rail, smaller metrics, integrated health panel, dense Recent Assessments and Quick Actions immediately below. Build passes. Chromium 1280x800 before/after empty/offline and populated screenshots compared visually; 390px screenshot inspected. Quick Actions/history/settings/refresh and six responsive widths passed with browser fixtures. Shell/scanner integrations unchanged. Exact illustration, unavailable findings/reporting and sample counts are not reproduced; actual data constraints remain explicit. Awaiting user visual approval; no commit/push/PR or next milestone.


### Milestone 2 full-size reference refinement — 2026-10-18

Still awaiting visual approval. Reworked Dashboard typography/proportions, full-width bottom Quick Actions, persistent five-column empty table header, visible service descriptions and local layered shield SVG. Kept shell and scanner code unchanged. Final Chromium 1440x900 screenshot visually inspected after successive proportion corrections; complete dashboard fits viewport. Empty/offline, populated, connected/disconnected, quick actions, refresh, history/settings and selected-scan target navigation checked using isolated fixtures. Six widths from 320 to 1440px and mobile screenshot verified without page overflow. Final frontend build passes (existing Vite CJS warning); no backend gate changed. No commit, push, merge or PR.


### Milestone 3 — New Assessment wizard — 2026-10-18

Implemented and fixture-verified; awaiting user visual and functional approval. Milestones 1 and 2 are approved/published. Replaced only New Assessment with the four-step target/consent, calibration, LLM07 scope and review workflow. Preserved shell, Overview, shared scanner state and API client; no backend changes or dependencies.

Final frontend build passed. Chromium fixtures covered registration, selection, consent/URL gates, both calibration methods, backend errors, accelerated timeout, selector reuse, target invalidation, stale-response guard, navigation persistence, budget keyboard input, exact scan payload/duplicate guard, and acknowledgment-driven Live Scan navigation. Twenty step/width combinations (320–1440px) passed horizontal-overflow checks; four desktop and one mobile capture inspected. Existing non-assessment App page implementations match HEAD. Live engine scans/calibration, Electron, other browsers and full accessibility certification are untested. No backend gate status changed. Work remains uncommitted on shahzaman; stop for approval.


### Milestone 3 finalization and visual approval — 2026-10-18

Milestone 3 implementation is complete and all four New Assessment wizard screens are visually approved by the user. This supersedes the pending-approval status above. The user authorized committing this milestone and pushing only to origin/shahzaman.

Finalization verification: frontend `npm run build` passed; the existing Vite CJS deprecation warning remains. Chromium fixture checks passed for registration/selection, consent and URL validation, automatic/manual calibration, errors and accelerated timeout handling, selector reuse/invalidation, step persistence, budget keyboard input, exact submission payload and duplicate prevention, and acknowledgment-driven Live Scan navigation. All four steps passed responsive overflow checks at five widths (320–1440px). Dashboard empty state, health refresh, Quick Actions, settings/history and desktop/compact navigation passed additional fixture checks with no runtime errors. Corrected one invalid UTF-8 separator byte in the registered-target fallback option; no behavior or visual design changes.

Live Playwright calibration and end-to-end scanning remain untested. Full integration testing is deferred until all frontend screens are complete. Fixture success is not live scanner verification. No backend/API/scanner changes, dependencies, or run_aegis.ps1 changes are included. No merge, PR, or Milestone 4 work is authorized by this finalization.


### Frontend PR preparation checkpoint — 2026-10-18

This checkpoint supersedes historical pending-approval statements without removing the history.

| Frontend milestone | Current state | Implementation commit |
|---|---|---|
| 1. Application Shell and Sidebar | Implemented and visually approved | `75d4c57` |
| 2. Dashboard / Overview | Implemented and visually approved | `7113e39` |
| 3. New Assessment Wizard (four steps) | Implemented and visually approved | `29610de` |

Live Scan and Results redesigns are **not yet implemented**. The pre-existing Live Scan functionality remains available; it is not the Design V1 redesign. No Milestone 4 work is included.

Verification for this checkpoint: `npm run build` in desktop passed (TypeScript and Vite; existing CJS deprecation warning). No frontend test script or checked-in frontend test suite is configured. Re-ran the existing temporary isolated Chromium fixture harness: target registration/selection, consent and URL checks, auto/manual calibration success/failure, accelerated timeout, selector reuse/invalidation, step persistence, keyboard budget, exact submission payload, duplicate guard, acknowledgment-driven Live Scan navigation, stale-result rejection, and 20 step/viewport overflow combinations passed with no JavaScript runtime errors. The fixture harness is outside the repository and is not a committed automated test suite.

Live Playwright calibration and full LLM07 end-to-end testing remain pending for the redesigned frontend. Full integration testing is deferred until all frontend screens are complete. No backend acceptance gate is newly passed by these fixture results. Historical backend verification entries do not establish integration acceptance of this redesign.

Scope review: shahzaman was active with a clean working tree and no untracked files at entry. Milestone 3 is already committed; this checkpoint adds documentation only. The reviewed branch diff against local main is limited to desktop frontend files and Project-Context documents. Backend functionality, scanner logic and API contracts are preserved; no changes to the API client, engine, agents or run_aegis.ps1 are included. No main modification, merge or PR creation. Push only to origin/shahzaman; PR creation still requires explicit authorization.


## Playwright sizing, chatbot readiness, and connector errors - 2026-10-21

Implemented on `shahzaman`, pending user review; no commit, push, or PR. No Results & Findings UI Milestone 5 work, target website changes, Windows display changes, dependency installs, or `run_aegis.ps1` edits.

- Headed scanning, automatic calibration, and interactive calibration use native viewport sizing. Headless non-persistent contexts retain 1280x800. Initial launch, two window sizes, and maximization were exercised on this Windows laptop.
- Shared readiness logic opens supported collapsed chat launchers once and verifies the authoritative input before typing. Both calibration modes retain the same four saved fields. Closed/visible/lazy-mounted chat, search fields, hidden unrelated textareas, delayed rendering, missing/broken/blocked launchers, readonly inputs, response timeout, and selector persistence/reuse have regression coverage.
- Failed connector turns are persisted without a vulnerability verdict, skip evaluation, and terminate as FAILED. Existing activity displays diagnostic errors as not evaluated. Replay recognizes legacy error markers and suppresses their old verdicts without rewriting records or introducing a migration.
- Backend verification: 57/57 tests passed, including real Chromium fixture interactions, interactive overlay capture, persistence, weak-bot, findings, and PDF regressions. A hardcoded developer-specific connector fixture path was made repository-relative. The initial focused run demonstrated 10 failures before the corrections; review added two further failing calibration cases, now passing.
- Test environment: AEGIS's existing .venv lacks pytest and pytest-asyncio. Tests used the already installed pytest 9.1.1 packages from the target backend environment, appended to sys.path after AEGIS dependencies, plus a temporary in-memory pytest hook executing coroutine tests with asyncio.run. No packages/configuration were installed or changed. Pytest reported its unknown asyncio_mode option, plus existing datetime/FastAPI deprecation warnings. This is not a claim that plain `.venv/python -m pytest` works on this laptop.
- Frontend: TypeScript/Vite production build passed (existing Vite CJS deprecation warning). Isolated built-UI fixtures passed genuine replies, legacy persisted errors, and live errors; turn error status did not replace lifecycle status. Screenshot inspected; no JavaScript runtime exceptions.
- Real scan: `3efe998a-fba0-4db4-aef5-c987f607c6ef` used the existing saved Aegis Electronics target/configuration and the real ScanService/Orchestrator in-process. One fixed KB prompt was submitted with no manual click. Target API returned HTTP 200, generated=true, model smollm:360m; AEGIS's configured llama3.2:latest judge returned HTTP 200 and a genuine verdict. Scan COMPLETED with one success turn and no disclosure detected; response capture took 7079ms. No judge fallback or connector error was used. This verifies the scan service path, not a desktop-to-engine end-to-end run.
- Real automatic calibration succeeded and returned the saved selector values. A later attempt to repeat both calibration modes after the generic-selector refinement was blocked by port 5173 refusing connections, before interactive calibration began. Interactive mode is verified with actual Chromium fixture clicks and subsequent fresh scans, not claimed as verified on the real site in this run.
- Limits: other laptops/monitors, Electron, arbitrary launchers and iframe-specific controls remain unverified. Legacy replay relies on reserved connector text markers and does not repair historical scan states or findings. Startup failures before a turn emit diagnostics but have no turn row. Broader acceptance gates are not newly declared passed.

## Milestone 5 - Results & Findings UI redesign - 2026-10-21

Implemented on `shahzaman`, pending visual review. No commit, push, or PR.

- Modified only `desktop/src/views/FindingsInspector.tsx`, `desktop/src/views/findings-inspector.css` and associated Project-Context documents. Shell, Dashboard, wizard, backend, scanner, calibration, API client, and `run_aegis.ps1` are unchanged.
- Approved-reference layout implemented: compact results header, six summary cards, Key Findings, Assessment Information, Test Case Summary, and Assessment Metrics. Existing finding expansion, persisted evidence, timeline, refresh, scan selection and PDF downloading retained.
- Corrected unavailable/empty presentation, stale aggregate-request handling, zero-grade presentation, connector-diagnostic labels, and detail-fetch error feedback. Scope and coverage remain explicit.
- Verification: `npm.cmd run build` passed (TypeScript and Vite; existing Vite CJS deprecation warning). Initial sandbox build failed on esbuild filesystem access; approved unrestricted rerun passed. No dependencies installed.
- Isolated Chromium API fixtures passed Dashboard-to-Results and History-to-Results navigation, populated results, expandable finding evidence, PDF error and successful download/filename, offline and partial API failures, failed-empty results, zero risk grade, connector-error evidence and timeline. No JavaScript runtime exceptions. Screenshots inspected at 1280x800, 1280x600, and 390x800; document reflow checked at 320px. Fixture script/screenshots reside in OS temporary storage, not the repository.
- PDF success used a generated test PDF supplied by the fixture, not the live report endpoint. Live engine/database results, real PDF generation, scanner execution/calibration, Electron, and full end-to-end integration were not exercised in this milestone. No claim of screen-reader certification or exhaustive keyboard testing.
- Remaining differences: existing shell is preserved; no unsupported report preview, fabricated pending cases, or inferred interface type. Assessment metrics are explicitly persisted-result metrics. Historical backend reporting/legacy findings limitations from the audit remain unresolved and require separate authorization.
