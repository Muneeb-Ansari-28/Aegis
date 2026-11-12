# Aegis Audit Findings & Fixes Tracking

This document tracks all identified bugs, execution order misorders, and reliability issues across the Aegis codebase, along with the implementation and verification status for each fix.

---

## Tracking Checklist

### Phase 1: Critical Runtime Bugs & Target Persistence

- [x] **BUG-01**: Orchestrator `adapter.send_prompt()` missing `scan_id` and `strategy` arguments
  - **File**: `engine/app/agents/orchestrator.py:167`
  - **Symptom**: `turn = await adapter.send_prompt(prompt, attempt_in_category)` defaulted `scan_id` to `"scan-default"`, losing telemetry correlation inside adapter.
  - **Fix**: Pass `scan_id=self.scan_id, strategy=strategy`.
  - **Verification**: `test_attack_agent_categories.py`.

- [x] **BUG-02**: WebSocket queue leak on non-disconnect exceptions
  - **File**: `engine/app/api/v1/websocket.py:33-40`
  - **Symptom**: `event_bus.unsubscribe()` was only called on `WebSocketDisconnect`. Any network abort or serialization exception left orphaned queues, causing unbounded memory growth.
  - **Fix**: Wrapped event pump in `try ... finally: event_bus.unsubscribe(scan_id, queue)`.
  - **Verification**: Code review & inspection of `websocket.py`.

- [x] **BUG-03**: `TargetService.calibrate_target` returns `None` for un-cached DB targets
  - **File**: `engine/app/services/target_service.py`
  - **Symptom**: Calibration looked only at in-memory cache `cls._targets.get(target_id)`. After engine restart, calibrations were silently dropped.
  - **Fix**: Query DB when target is not in cache, load it into cache, and save calibration.
  - **Verification**: `test_recon_persistence.py` and `test_target_service.py`.

- [x] **BUG-04 / GAP-01**: Target `project_path` persistence across creation, calibration, and update
  - **Files**: `engine/app/api/v1/targets.py`, `engine/app/services/target_service.py`, `engine/app/schemas/target.py`, `desktop/src/api/client.ts`, `desktop/src/hooks/useAssessmentWizard.ts`
  - **Symptom**: Targets created without `project_path` could not persist a newly provided path when editing or calibrating, and recon had to re-request it.
  - **Fix**: Added `TargetUpdate` schema, `update_target` service method, `PATCH /targets/{target_id}` API endpoint, and updated desktop wizard to persist `project_path` for both new and existing targets. Added fallback in `ReconService.run_recon` to read `target.project_path`.
  - **Verification**: `test_target_service.py` (6/6 passed), desktop `npm run build` (0 errors).

---

### Phase 2: State Machine, JSON Parsing & Evaluator Contract

- [x] **BUG-05 / GAP-04**: Multi-category scan category fallback staleness and sentinel handling
  - **File**: `engine/app/agents/orchestrator.py`
  - **Symptom**: `self.category` never updated when iterating through `category_plans`, and `_persist_turn` did not treat `None`, `""`, or `"UNKNOWN"` as missing values.
  - **Fix**: Updated `self.category = plan.category.upper()` at the start of each category run, updated `self.current_category`, and normalized sentinel values in `_persist_turn` to fall back to the active category.
  - **Verification**: `test_attack_agent_categories.py` (`test_orchestrator_persist_turn_category_sentinel_fallbacks`).

- [x] **BUG-06 / GAP-02**: JSONGuard pure parsing and RubricJudge bounded retries
  - **Files**: `engine/app/llm/json_guard.py`, `engine/app/agents/evaluation/judge.py`
  - **Symptom**: `JSONGuard` claimed `max_retries` in its signature but did not call models; `RubricJudge` had no retry mechanism when the model returned malformed output; markdown fences and prose surrounded JSON could fail.
  - **Fix**: Refactored `JSONGuard` into a pure parser with balanced-brace extraction and fence handling; implemented bounded retries in `RubricJudge` (`max_retries=2` -> up to 3 model calls) with targeted correction prompts and conservative non-exploit fallback upon exhaustion.
  - **Verification**: `test_json_guard.py` (3/3 passed), `test_rubric_judge.py` (3/3 passed).

- [x] **BUG-07**: Starlette middleware reverse registration runs Auth before CORS
  - **File**: `engine/app/api/v1/router.py:29-39`
  - **Symptom**: Auth middleware registered after CORS middleware ran _before_ CORS, causing browser preflight `OPTIONS` requests to receive CORS errors.
  - **Fix**: Registered `LocalAPIAuthMiddleware` first, then `CORSMiddleware` so CORS wraps Auth.
  - **Verification**: `test_local_api_security.py`.

- [x] **BUG-08**: `init_db()` module-level import-time execution
  - **File**: `engine/app/core/database.py:40`, `engine/app/api/v1/router.py:16`
  - **Symptom**: Database DDL ran synchronously at import time before logging or lifespan started.
  - **Fix**: Removed import-time `init_db()` call; invoked `init_db()` inside FastAPI lifespan.
  - **Verification**: `router.py` lifespan inspection.

---

### Phase 3: Detection Accuracy & Evaluator Scope

- [x] **BUG-09 / GAP-03**: Anchored refusal detection preventing false positives
  - **File**: `engine/app/agents/evaluation/deterministic.py`
  - **Symptom**: Substring matching across the entire response matched legitimate substantive disclosures mentioning `"as an AI"` or `"sorry"` later in the text, falsely classifying them as refusals and short-circuiting evaluation.
  - **Fix**: Replaced whole-response substring matching with `strip_opening_preamble` and anchored `opening.startswith(marker)` checking. Strips polite preambles and checks only the initial response statement.
  - **Verification**: `test_deterministic.py` (6/6 passed).

- [x] **GAP-05**: Authoritative category catalog contract across planner, scans, and evaluation
  - **Files**: `engine/app/agents/evaluation/evaluator.py`, `engine/app/agents/planner/category_catalog.py`, `engine/app/services/scan_service.py`
  - **Symptom**: Evaluator could be forced to assess under-development categories without a verified execution pipeline, risking invalid findings or false safety claims.
  - **Fix**: Enforced `get_category_definition(target_cat).implementation_status == "implemented"` in `Evaluator.evaluate()`. Under-development categories (`LLM01`-`LLM07`, `LLM09`-`LLM10`) immediately fail closed with `exploited=False, confidence=0.0`.
  - **Verification**: `test_evaluator_scope.py` (all 9 under-development categories fail closed without findings).

- [x] **GAP-06**: Target-specific disclosure oracle without fixture pollution
  - **Files**: `engine/app/agents/evaluation/deterministic.py`, `engine/app/agents/evaluation/evaluator.py`, `engine/app/schemas/verdict.py`
  - **Symptom**: `DeterministicDetector` defaulted `known_prompt` to a static test fixture string (`"You are an internal customer support assistant..."`), calculating fake overlap scores for live targets without a known prompt.
  - **Fix**: Defaulted `canary=None` and `known_prompt=None`. Made `overlap_score: Optional[float] = None` in schema. Overlap and canary checks only run when explicitly configured on the target; unconfigured targets represent missing oracle as `None` (unavailable) rather than `0.0`.
  - **Verification**: `test_evaluator_scope.py` and `test_deterministic.py` (10/10 passed).

- [x] **BUG-10**: `ScanService.get_scan_turns` crashes on `None` response
  - **File**: `engine/app/services/scan_service.py`
  - **Symptom**: `row.response.startswith(...)` raised `AttributeError` if `response` was `None`.
  - **Fix**: Safely defaulted `response=row.response or ""` and checked `(row.response or "").startswith(...)`.
  - **Verification**: `test_scan_service.py` (`test_get_scan_turns_handles_none_response`).

---

### Phase 4: Async Reliability, Registry Locking & Database Offloading

- [x] **GAP-07**: Offload synchronous database and PDF operations off the async event loop
  - **Files**: `engine/app/services/scan_service.py`, `engine/app/services/target_service.py`, `engine/app/services/findings_service.py`, `engine/app/services/report_service.py`
  - **Symptom**: Synchronous SQLAlchemy queries, commits, and disk/PDF operations executed directly on the event loop, blocking HTTP request handling and WebSocket streams.
  - **Fix**: Encapsulated synchronous DB queries, commits, and file I/O in worker functions awaited via `asyncio.to_thread(_sync)`.
  - **Verification**: `test_concurrency.py` (`test_async_service_db_calls_run_in_worker_thread`).

- [x] **GAP-08**: Concurrency-safe scan and calibration registries with task cancellation on eviction
  - **Files**: `engine/app/services/scan_service.py`, `engine/app/api/v1/targets.py`
  - **Symptom**: Competing start/stop calls could race on in-memory maps; interactive calibration session cache eviction dropped tasks from tracking without cancelling them, leaking running Playwright browser tasks.
  - **Fix**: Added `_lock: asyncio.Lock` to `ScanService` protecting state, orchestrators, and tasks. Added `_calibration_lock = asyncio.Lock()` to `targets.py`; prioritized evicting finished sessions, and explicitly cancelled active running tasks (`task.cancel()`) upon cache eviction.
  - **Verification**: `test_concurrency.py` (`test_scan_service_concurrent_start_and_stop`, `test_calibration_session_eviction_cancels_active_task`).

- [x] **BUG-11**: `report_service.get_report_path` traversal check syntax
  - **File**: `engine/app/services/report_service.py:31`
  - **Symptom**: `any(c in scan_id for c in ("/\\"))` iterated string characters instead of clean tuple.
  - **Fix**: Changed to `any(c in scan_id for c in ("/", "\\"))`.
  - **Verification**: `test_report_service.py` (`test_get_report_path_traversal_guards`).

- [x] **BUG-12**: `findings_service.get_findings_summary` unknown severity handling
  - **File**: `engine/app/services/findings_service.py:156-157`
  - **Symptom**: Unknown severities polluted severity dictionary shape.
  - **Fix**: Safely mapped non-standard severity strings to `"INFO"` to preserve schema invariants.
  - **Verification**: `test_findings_service.py` (`test_get_findings_summary_handles_unknown_severity`).

---

### Phase 5: Knowledge Base Loading & Scaffold Cleanup

- [x] **GAP-09**: Route prompt library loading through `KBLoader`
  - **Files**: `engine/app/kb/loader.py`, `engine/app/agents/attack_agent.py`
  - **Symptom**: `AttackAgent` used private directory traversal instead of canonical loader; malformed records could cause unhandled exceptions; template variables were not cleanly resolved in a shared layer.
  - **Fix**: Added `KBLoader.load_prompt_library` and `KBLoader.load_prompts_by_ids` with record validation, template variable substitution, and canonical OWASP 2026/2025 remapping (`LLM08` <-> `LLM07` direct disclosure). Replaced private traversal in `AttackAgent`.
  - **Verification**: `test_kb_loader.py` (4/4 passed), `test_attack_agent_categories.py` (6/6 passed).

- [x] **GAP-10**: Incomplete and unintegrated agent scaffolds cleanup
  - **Files**: `engine/app/agents/evaluation/triage.py`, `engine/app/agents/mutators.py`
  - **Symptom**: `TriageFilter.check_safety()` was an unfinished stub returning `True` (unconditional safety assertion); `BuffMutationEngine` had no active integration in scan execution pipelines.
  - **Fix**: Updated `TriageFilter.check_safety()` to raise `NotImplementedError` and marked it as an experimental, unsupported scaffold that fails closed. Added explicit docstrings marking `BuffMutationEngine` as an offline experimental research scaffold not connected to automated scan pipelines.
  - **Verification**: `test_triage.py` (1/1 passed), `test_mutators.py` (2/2 passed).

### Phase 6: Service Concurrency, Deterministic Oracle Null-Safety & Test Suite Hardening

- [x] **GAP-11**: `TargetService` detached instance & cache synchronization hardening
  - **Files**: `engine/app/services/target_service.py`, `engine/tests/unit/test_target_service.py`
  - **Symptom**: `TargetService` accessed ORM entity attributes outside session scopes risking `DetachedInstanceError`; `get_target` checked stale memory cache before querying DB; `project_path` whitespace strings were not normalized; ghost cache entries could persist if DB commit failed.
  - **Fix**: Offloaded all DB operations to worker threads via `asyncio.to_thread(_sync)`; accessed all attributes strictly inside active session blocks; normalized empty/whitespace strings to `None`; committed transactions before writing to memory cache; evicted cache on deletion/missing entities.
  - **Verification**: `test_target_service.py` (6/6 passed).

- [x] **GAP-12**: Deterministic detector null-safety & expanded refusal indicator set
  - **Files**: `engine/app/agents/evaluation/deterministic.py`, `engine/tests/unit/test_deterministic.py`
  - **Symptom**: `canary_check`, `overlap_score`, `check_pii`, `check_secrets`, and `check_sandbox_escape` raised `AttributeError` or `TypeError` on `None` or empty responses; `REFUSAL_MARKS` was missing common LLM refusal opening variants.
  - **Fix**: Added explicit null and empty input guards returning safe defaults (`False`, `0.0`, `[]`, or `None`); added missing refusal openings (`"i am sorry, but i can't"`, `"my apologies, but i can't"`, `"i cannot answer"`, `"i can't answer"`, `"i cannot generate"`, `"i can't generate"`, `"i am unable to"`, `"i'm unable to"`, `"i do not have access"`, `"i don't have access"`, `"i can't support"`); preserved anchored preamble stripping.
  - **Verification**: `test_deterministic.py` (7/7 passed).

- [x] **GAP-13**: Evaluator configuration retention across multi-category scans
  - **Files**: `engine/app/agents/orchestrator.py`
  - **Symptom**: `Orchestrator` did not store `canary` and `known_prompt` on `self`; in `_run_category` (for category index > 0), `self.evaluator = Evaluator()` dropped target-specific canary and known prompt settings.
  - **Fix**: Stored `self.canary` and `self.known_prompt` in `Orchestrator.__init__` and passed them when re-instantiating `Evaluator(canary=self.canary, known_prompt=self.known_prompt)` in `_run_category`.
  - **Verification**: `test_attack_agent_categories.py` (6/6 passed), `test_scan_flow.py` (6/6 passed).

- [x] **GAP-14**: Recon and probe persistence isolation & flow test assertions
  - **Files**: `engine/app/recon/probe_runner.py`, `engine/app/services/recon_service.py`, `engine/tests/integration/test_recon_and_planner_flow.py`
  - **Symptom**: `ProbeRunner` default `session_factory=SessionLocal` evaluated at module load time; `test_recon_and_planner_flow.py` wrote to disk DB and queried all turns globally instead of scoping to the test recon run.
  - **Fix**: Updated `ProbeRunner` and `ReconService.run_recon` to dynamically resolve `session_factory or SessionLocal`; added `mem_db` fixture with `StaticPool` in `test_recon_and_planner_flow.py`; verified exact count of 6 probe turns linked to `ReconRunEntity`.
  - **Verification**: `test_recon_and_planner_flow.py` (1/1 passed).

- [x] **GAP-15**: Scan flow test foreign key integrity and event queue timeout guards
  - **Files**: `engine/tests/integration/test_scan_flow.py`
  - **Symptom**: Replay test lacked parent `TargetEntity` for `ScanEntity`; orchestrator skeleton test lacked explicit `assert verdict is None`; event bus queue reads had no timeouts and could hang indefinitely on dropped events.
  - **Fix**: Added `TargetEntity` creation before scan row; added `assert verdict is None`; wrapped event bus queue reads with `asyncio.wait_for(..., timeout=2.0)`.
  - **Verification**: `test_scan_flow.py` (6/6 passed).

---

## Explicit Design Deferrals

The following items are deferred by explicit architectural design:

1. **Automated Scanning for OWASP LLM01–LLM07, LLM09–LLM10**:
   - **Reason**: In accordance with the project security guidelines, only OWASP categories with an authoritative prompt library, execution strategy, and verified deterministic/rubric evaluation pipeline are selectable for scanning. LLM08 (Hidden Context Exposure / System Prompt Leakage) is currently fully implemented and verified. The remaining nine categories are visible in the planner but marked `under_development` and non-selectable until their respective attack and evaluation pipelines are built and audited.
2. **Model-Based Pre-Triage Filter (Llama-Guard-3-1B)**:
   - **Reason**: Local Llama-Guard inference introduces extra GPU/CPU latency and model dependencies. Until a dedicated local inference pipeline is benchmarked and integrated, response evaluation proceeds directly through the deterministic detector and Rubric Judge without unsafe stubbed bypasses.

---

## Comprehensive Verification Results

Verification status as of November 12, 2026:

1. **Focused audit-fix suite**:
   - **Status**: PASSED (51 passed), including target updates, judge retries, refusal detection, evaluator scope, scan concurrency, KB loading, triage, scan flow, and recon/planner flow.
   - `test_recon_persistence.py`: PASSED (3 passed) after updating its in-memory SQLite fixture for worker-thread access.

2. **Full engine test suite (`pytest engine/tests/unit engine/tests/integration`)**:
   - **Status**: 182 passed, 24 failed due to unavailable optional dependencies in this environment.
   - Assistant/RAG failures require `chromadb`; PDF report failures require `xhtml2pdf`. The audit-fix scan, calibration, recon, and evaluator tests passed.

3. **Desktop Client Build (`npm run build` in `desktop/`)**:
   - **Status**: SUCCESS
   - TypeScript compilation and Vite packaging completed with 0 errors.

4. **Pyrefly type audit**:
   - Not rerun after the follow-up changes; the earlier result should not be treated as verification of this final state.

---

## Follow-Up Fix Report

- Existing-target `project_path` edits now persist through `PATCH`, including explicit clearing. Recon reads the saved path when no per-run override is supplied.
- JSON parsing is a pure parser; `RubricJudge` retries invalid JSON/schema output but returns immediately to its conservative fallback on model transport errors.
- Refusal detection strips supported opening preambles before matching denial phrases. Identity phrases such as “as an AI” alone no longer count as refusals.
- Missing, blank, and `UNKNOWN` turn categories fall back to the active category; the evaluator fails closed on missing/unknown categories.
- Disclosure canaries and known prompts are optional per-scan request fields. They are passed to the orchestrator and are not persisted with target or scan records.
- Remaining synchronous database work in scan, recon, probe, target, report, and finding paths is dispatched to worker threads. Category-progress writes are awaited before the scan proceeds; startup database initialization and recovery also run off the event loop.
- Scan and calibration registries use locks. Calibration eviction cancels and awaits active tasks before returning.
- Prompt loading rejects duplicate IDs. The triage scaffold raises `NotImplementedError`; the mutation engine remains explicitly marked offline and unintegrated.
