# Aegis Reconnaissance and Test Planner Improvement Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make recon a visible, reliable input to test planning and scan execution, represent all ten OWASP categories truthfully while they are under development, and correct the connected security, reporting, recovery, and setup defects found in the audit.

**Architecture:** Keep recon as a deterministic evidence-gathering pipeline with separate outcomes for passive web observation, optional local process discovery, optional user-selected project inspection, and optional benign chat probes. Persist an evidence-backed profile and per-stage completion state; have a canonical OWASP 2026 category catalog produce a plan that distinguishes testability from implementation status. The UI and scan service consume that plan, while reports distinguish completed negative results from incomplete or unsupported work.

**Tech Stack:** Python 3.12, FastAPI, Pydantic 2, SQLAlchemy/SQLite, Playwright, psutil, React, TypeScript, pytest, Vite.

**Spec:** `engine/knowledge/owasp/OWASP-LLM-Top-10-2026.md` is the canonical taxonomy source. Also reconcile `README.md`, `aegis-system-architecture-spec.md`, `aegis_implementation_plan.md`, `docs/api.md`, `docs/user-guide.md`, and the derived records in `engine/app/kb/01_OWASP/2026/`.

## Global Constraints

- Treat `engine/knowledge/owasp/OWASP-LLM-Top-10-2026.md` as the canonical 2026 category-number/name source; keep app KB JSON, planner data, UI labels, prompts, and reports synchronized with it. Retain 2025 names only as explicitly labeled legacy aliases.
- A missing signal is not affirmative evidence of absence. Failed, skipped, inaccessible, or incomplete recon stages must not mark a category not applicable.
- The ten OWASP categories are roadmap entries; a category without a complete prompt, execution, and evaluation pipeline must be `not_tested` and rejected by scan start.
- Recon classifies evidence and testability; only a completed category scan with valid evidence can produce a vulnerability finding or a clean result.
- Keep targets restricted to local/private networks and require explicit user authorization for active probes and scans.
- Tier 3 project inspection remains optional, uses only a user-selected project path, reads environment-variable names only, and never requires administrator privileges.
- Multi-category selection and “Run all ready categories” are defined in `docs/superpowers/plans/2026-11-11-profile-guided-multi-category-scan-workflow.md`; that plan supersedes any single-category-per-scan assumption here. “Run all” includes only categories that are both testable and implemented.
- Preserve support for existing saved `TargetProfile` records through default values or a documented migration.

## Review Focus

- A passive navigation failure, missing Chromium, blocked path, or TLS error must be visible as an incomplete stage and must not create high-confidence negative findings.
- An absent, unreadable, or wrong Tier 3 path must remain unknown and must not cause a RAG/vector category to become not applicable.
- Probe connector errors and refusals must not be interpreted as evidence that RAG, memory, tools, or rendering are absent.
- Legacy 2025 category identifiers must not silently execute or report under a different 2026 vulnerability name.
- A failed, stopped, or zero-turn scan must never produce report text implying that all tests passed or that the target is resilient.

---

## File Map

- `engine/app/schemas/target_profile.py`: profile capability evidence, tier statuses, and warnings.
- `engine/app/schemas/test_plan.py`: per-category testability, implementation state, and rationale.
- `engine/app/recon/`: tier collectors, probe analysis, and profile construction.
- `engine/app/agents/planner/`: canonical category catalog, applicability rules, and prompt filtering.
- `engine/app/services/recon_service.py`: ordered recon orchestration and profile persistence.
- `engine/app/api/v1/targets.py`, `engine/app/api/v1/scans.py`: recon, plan, and scan contracts.
- `engine/app/services/scan_service.py`, `engine/app/agents/orchestrator.py`, `engine/app/agents/attack_agent.py`, and `engine/app/agents/evaluation/`: plan validation and category-specific execution.
- `engine/app/models/entities.py`, `engine/app/core/database.py`, and `engine/migrations/`: persisted recon run/evidence lifecycle and schema updates.
- `desktop/src/api/client.ts`, `desktop/src/hooks/useAssessmentWizard.ts`, `desktop/src/components/NewAssessment.tsx`: recon and plan UI flow.
- `engine/app/services/report_service.py`, `engine/app/agents/reporting_agent.py`, `engine/app/templates/report.html`, and `desktop/src/views/FindingsInspector.tsx`: truthful scan outcomes.
- `engine/app/api/v1/router.py`, `engine/app/api/v1/reports.py`, and `engine/app/services/report_service.py`: local API and report-path hardening.
- `engine/tests/` and `desktop/`: regression coverage and frontend build verification.
- `README.md`, `docs/api.md`, `docs/user-guide.md`, and `Project-Context/Status.md`: supported scope and roadmap wording.

## Task List

### Phase 1: Establish category and recon result contracts

### Task 1: Build the category catalog from the canonical OWASP 2026 source

**Files:** Create `engine/app/agents/planner/category_catalog.py`; modify `engine/app/agents/planner/rules.py`, `engine/app/schemas/test_plan.py`, and the derived records in `engine/app/kb/01_OWASP/2026/`; test `engine/tests/unit/test_category_catalog.py`, `engine/tests/unit/test_test_planner.py`.

**Interfaces:** `get_category_catalog() -> list[CategoryDefinition]`; `get_category_definition(category: str) -> CategoryDefinition | None`. A definition contains `id`, canonical `name`, legacy aliases, `implementation_status` (`implemented` or `under_development`), and capability prerequisites. Verify names and ID ordering against `engine/knowledge/owasp/OWASP-LLM-Top-10-2026.md`; keep JSON KB records synchronized. Determine implementation status from a complete prompt, execution, and evaluator path, not from whether a category JSON file happens to exist.

- [x] Add tests asserting all ten 2026 IDs and names, especially LLM07 Misinformation, LLM08 Hidden Context Exposure, and LLM09 Vector and Embedding Weaknesses.
- [x] Add a consistency check against the canonical Markdown source and the derived OWASP JSON records so future numbering/name drift fails visibly.
- [x] Add tests asserting 2025 system-prompt-leakage naming is treated as a legacy alias and never changes the canonical 2026 label.
- [x] Replace planner-local stale category names with catalog references; planner results must include all ten categories.
- [x] Add `implementation_status` and `testability` (`ready`, `partial`, `not_testable`, `not_tested`) plus a rationale to `CategoryPlan`; under-development categories use `status="not_tested"` and budget zero.
- [x] Leave prompt and evaluator libraries that are not authored/complete as `under_development`; do not generate placeholder attacks or claim these categories are supported. They must have no applicable prompt IDs and scan start must reject them.
- [x] Require both an implemented execution/evaluation pipeline and its needed evidence oracle before a category can be `ready`; capability signals alone do not establish that a category can be reliably evaluated.
- [x] Run `cd engine; pytest tests/unit/test_category_catalog.py tests/unit/test_test_planner.py -q`; expect all tests to pass.

### Task 2: Represent recon stage completion and evidence quality

**Files:** Modify `engine/app/schemas/target_profile.py`, `engine/app/recon/network_collector.py`, `engine/app/recon/static_scanner.py`, and `engine/app/recon/probe_runner.py`; test `engine/tests/unit/test_recon_stage_status.py` and extend their existing unit tests.

**Interfaces:** Add `ReconStageStatus` (`completed`, `partial`, `skipped`, `failed`) and a `stages` map plus `warnings` to `TargetProfile`. Add scan status and warnings to `StaticScanResult` and probe completion metadata to `ProbeRunResult`. Existing profile reads default missing stage data to `unknown`.

- [x] Test missing/unreadable Tier 3 paths as `failed` or `partial`, never as a completed negative scan.
- [x] Test probes with connector errors, timeouts, missing probe responses, and refusal responses; none can count as affirmative evidence of absence.
- [x] Separate “no RAG signal observed” from “RAG ruled out”; a no-citation response alone remains unknown.
- [x] Separate “model echoed HTML text” from “the target rendered HTML”; only claim rendered markup when the browser DOM provides evidence.
- [x] Test passive collection failure and optional/skipped stages are represented in the returned profile.
- [x] Run focused recon tests; expect unknown/incomplete cases to remain inconclusive.

### Task 3: Make Tier 3 absence and permission handling safe

**Files:** Modify `engine/app/recon/static_scanner.py`, `engine/app/recon/profile_builder.py`, `engine/app/agents/planner/rules.py`; test `engine/tests/unit/test_recon_static_scanner.py`, `engine/tests/unit/test_recon_profile_builder.py`, `engine/tests/unit/test_test_planner.py`.

- [x] Add tests for nonexistent paths, unreadable manifests, unreadable source files, malformed manifests, and a valid project with no recognized dependencies.
- [x] Return partial/incomplete status whenever a relevant file could not be read or parsed; retain a path-safe warning without exposing file contents or environment values.
- [x] Change the profile builder so only a completed Tier 3 scan plus valid negative active evidence can support a high-confidence negative; do not use a failed/skipped/partial scan for absence.
- [x] Confirm Tier 3 output includes environment-variable names only and excludes values from warnings, evidence, logs, and API response.
- [x] Run focused Tier 3/profile/planner tests; expect inaccessible inputs to preserve `unknown` and scheduled safe fallback.

### Checkpoint: Recon evidence contract

- [x] Every stage has explicit completion status, evidence, and warnings.
- [x] Incomplete evidence cannot become “not applicable.”
- [x] Profile persistence and retrieval accept both existing records and the extended profile schema.

## Phase 2: Make each recon tier reliable and explainable

### Task 4: Correct Tier 1 passive observation boundaries

**Files:** Modify `engine/app/recon/network_collector.py`, `engine/app/recon/fingerprint.py`, `engine/app/recon/signatures/ai_stack.yaml`; test `engine/tests/unit/test_recon_signatures.py` and add `engine/tests/unit/test_recon_network_collector.py`.

- [x] Label the seven well-known-path GETs as bounded active endpoint checks in stage results; keep them separate from browser-observed passive signals.
- [x] Add per-request timeout and failure accounting; one unavailable endpoint must not discard successful browser signals.
- [x] Restrict collected headers and paths to the target origin; do not let third-party script or header signals imply target architecture without an explicit evidence source.
- [x] Ensure Playwright context/browser cleanup occurs on every exception after launch.
- [x] Test redirects, HTTPS errors, unreachable targets, third-party scripts, and partial endpoint responses.
- [x] Run focused network/signature tests; expect partial data to survive individual collector failures.

### Task 5: Clarify Tier 2 local discovery and permissions

**Files:** Modify `engine/app/recon/local_discovery.py`, `engine/app/services/recon_service.py`, `engine/app/api/v1/targets.py`; test `engine/tests/unit/test_recon_local_discovery.py` and `engine/tests/unit/test_recon_api.py`.

- [x] Use standard IP parsing to recognize IPv4 and IPv6 loopback URLs for local process inspection; do not treat a remote private-network address as a local process.
- [x] Keep common-port discovery as a separate explicit operation. In recon, inspect only the selected target’s loopback port; do not silently scan every local port.
- [x] Test psutil permission failures: socket fallback may report a port as listening but must identify PID, process name, command line, or working directory as unavailable.
- [x] Redact likely secret-bearing command-line arguments before returning discovery results; test `--api-key`, `--token`, and `--password` forms.
- [x] Return a clear permission/metadata warning without requiring administrator privileges.
- [x] Run focused Tier 2 tests; expect IPv6 loopback and denied process metadata to produce explicit, safe results.

### Task 6: Bound and explain optional Tier 3 project inspection

**Files:** Modify `engine/app/recon/static_scanner.py`, `engine/app/api/v1/targets.py`, and `desktop/src/components/NewAssessment.tsx`; test `engine/tests/unit/test_recon_static_scanner.py` and add frontend coverage if a component test harness exists.

- [x] Define and enforce a maximum number and size of files read; sort candidate source files before applying the existing AST cap so results are deterministic.
- [x] Keep inspection read-only; never execute project code, resolve dependencies, or read `.env` values.
- [x] Expose Tier 3 as an optional project-path input with an explanation that OS access is limited to the current user’s permissions and administrator access is not requested.
- [x] Treat an unset path as `skipped`; treat inaccessible paths as `partial` or `failed`; neither may support a negative category verdict.
- [x] Test oversized files, nested source trees, inaccessible files, and unset optional paths.

### Task 7: Make active benign probes trustworthy

**Files:** Modify `engine/app/recon/probe_runner.py`, `engine/app/recon/profile_builder.py`, `engine/app/adapters/playwright_web.py`; test `engine/tests/unit/test_recon_probe_runner.py` and `engine/tests/unit/test_recon_profile_builder.py`.

- [x] Track every planned probe as completed, failed, or skipped; preserve `TurnRecord.status` rather than reducing all returned text to evidence.
- [x] Make capability results evidence-based: self-reported tools are a weak signal, no citation is not proof of no RAG, and failed memory recall is not proof of no memory.
- [x] Keep probes benign and bounded; use a documented per-probe timeout and stop further probes when the connector is unhealthy.
- [x] Test a partial probe run and verify that profile confidence cannot increase from error-marker text.
- [x] Run focused probe/profile tests; expect failed probes to lower certainty, never to prove absence.

## Phase 3: Connect the planner to scans

### Task 8: Make planning use the profile, category catalog, and applicable prompt metadata

**Files:** Modify `engine/app/agents/planner/rules.py`, `engine/app/agents/planner/prompt_filter.py`, `engine/app/schemas/test_plan.py`; test `engine/tests/unit/test_test_planner.py` and add `engine/tests/unit/test_prompt_metadata_filter.py`.

- [x] Map profile evidence to 2026 category prerequisites: RAG/vector evidence informs LLM09; tools inform LLM03; verified rendering evidence informs LLM10; disclosure capability informs LLM08. Do not carry forward the stale LLM07/LLM08 mapping.
- [x] Keep unknown capability results scheduled as partial/unknown where a supported test exists; mark `not_applicable` only when an affirmative prerequisite rules it out.
- [x] Include all ten categories in each plan; use `not_tested` for categories whose pipeline is under development and explain missing implementation prerequisites.
- [x] Implement the documented `applicable_when` handling or remove that field from prompt records and documentation; test both `requires` and `applicable_when` conditions.
- [x] Ensure planned prompt IDs are unique, deterministic, category-correct, and actually resolve to prompt records.
- [x] Run focused planner and prompt-filter tests; expect taxonomy and applicability assertions to match the catalog.

### Task 9: Run recon and show the plan in the assessment UI

**Files:** Modify `engine/app/api/v1/targets.py`, `engine/app/services/recon_service.py`, `desktop/src/api/client.ts`, `desktop/src/hooks/useAssessmentWizard.ts`, `desktop/src/components/NewAssessment.tsx`; test `engine/tests/unit/test_recon_api.py` and add a frontend wizard flow test if supported.

- [x] Add an explicit wizard stage after calibration to run recon and request the test plan; show per-tier progress, skipped/failed warnings, profile confidence, and category testability.
- [x] Require explicit authorization for active chat probes at the API boundary; allow passive-only recon separately and test that an unauthenticated request cannot send chat messages.
- [x] Pass optional Tier 3 project path only when the user supplies one; keep Tier 3 opt-in.
- [x] Populate the multi-category selector from the plan/catalog according to `docs/superpowers/plans/2026-11-11-profile-guided-multi-category-scan-workflow.md`; allow only backend-selectable categories and display all ten with explicit applicability and implementation reasons.
- [x] Prevent scan start when recon/plan failed unless the user explicitly chooses a documented manual-scope fallback; label that fallback as “not recon-guided.”
- [x] Test successful recon, partial recon, recon failure, optional Tier 3 omitted, and all categories under development.
- [x] Run backend API tests and desktop build; expect the selected category label and implementation status to match the backend catalog.

### Task 10: Enforce plan-derived category, budget, and prompts at scan start

**Files:** Modify `engine/app/services/scan_service.py`, `engine/app/agents/orchestrator.py`, `engine/app/agents/attack_agent.py`, `engine/app/agents/evaluation/evaluator.py`, `engine/app/agents/evaluation/judge.py`; test `engine/tests/unit/test_attack_agent_categories.py`, `engine/tests/unit/test_scan_service.py`, and `engine/tests/integration/test_scan_flow.py`.

- [x] Revalidate every chosen category against the current profile’s plan in the backend; reject stale plan revisions and any under-development, not-applicable, or unscheduled category with an actionable error. Multi-category selection and per-category execution follow `docs/superpowers/plans/2026-11-11-profile-guided-multi-category-scan-workflow.md`.
- [x] Pass only the plan’s applicable prompt IDs into `AttackAgent`; remove fallback behavior that silently substitutes LLM01 prompts for unrelated categories.
- [x] Keep attack generation within the documented direct, plain-language scope; do not apply encoding, delimiter, roleplay, instruction-override, or other excluded mutation tactics after refusals.
- [x] Route only categories with a matching evaluator. For this delivery, preserve only verified implemented pipelines; unknown categories must not enter the LLM08 judge by default.
- [x] Ensure verdict category, persisted finding category, telemetry category, and report category all use the canonical 2026 ID.
- [x] Test stale/missing plan, unsupported category, wrong-category prompt IDs, and a valid scheduled category end-to-end.
- [x] Run focused scan and agent tests; expect unsupported categories to fail before any target interaction.

### Checkpoint: Recon-to-plan-to-scan

- [x] The normal UI path invokes recon and displays a planner result.
- [x] The backend validates the selected category and executes only its applicable prompts/evaluator.
- [x] All ten categories are visible with honest implementation and testability states.

## Phase 4: Correct persistence, reporting, security, and restart behavior

### Task 11: Persist recon evidence under a real recon-run identity

**Files:** Modify `engine/app/models/entities.py`, `engine/app/core/database.py`, `engine/app/services/recon_service.py`, `engine/app/recon/probe_runner.py`, `engine/migrations/`; test `engine/tests/integration/test_recon_and_planner_flow.py` and add `engine/tests/unit/test_recon_persistence.py`.

- [x] Stop assigning probe turns synthetic `scan_id` values that have no `ScanEntity` parent.
- [x] Add a recon-run record (or equivalent explicit parent) linking a target, profile snapshot, stage results, and probe turns; use a migration compatible with existing SQLite data.
- [x] Test two recon runs for the same target: evidence is attributable to the correct run and never appears as a scan turn or finding.
- [x] Test migration from a database containing existing target profiles and scans.
- [x] Run focused persistence tests; expect no orphaned recon turns and historical scan data unchanged.

### Task 12: Prevent incomplete scans from producing clean reports

**Files:** Modify `engine/app/services/report_service.py`, `engine/app/agents/reporting_agent.py`, `engine/app/templates/report.html`, `desktop/src/views/FindingsInspector.tsx`; test `engine/tests/unit/test_report_service.py`, `engine/tests/unit/test_reporting_agent.py`, and `engine/tests/integration/test_report_generation.py`.

- [x] Report `FAILED`, `STOPPED`, zero-successful-turn, and partially executed scans as inconclusive; do not use “all tests passed,” “resilient,” or a 100/100 clean assessment for them.
- [x] Calculate a clean result only for completed scans with at least one successful evaluated turn and a valid plan scope.
- [x] State tested categories and untested/not-applicable categories separately in report metadata, summary, methodology, and PDF disclaimer.
- [x] Test failed-before-first-turn, connector failure, stopped-after-one-turn, completed-no-findings, and completed-with-finding reports.
- [x] Run focused reporting tests; expect only completed assessed scope to receive a clean conclusion.

### Task 13: Harden local API origins and report file access

**Files:** Modify `engine/app/api/v1/router.py`, `engine/app/api/v1/websocket.py`, `engine/app/api/v1/reports.py`, `engine/app/services/report_service.py`; test `engine/tests/unit/test_reports_api.py` and add `engine/tests/unit/test_local_api_security.py`.

- [x] Require authentication for sensitive local API operations using a process-scoped credential; bootstrap it only through a trusted client channel, never a CORS-readable token endpoint or committed frontend secret.
- [x] Replace wildcard credentialed CORS with explicit loopback development origins and a documented packaged-client origin; reject untrusted browser origins. Treat CORS as a browser boundary, not as API authentication.
- [x] Apply equivalent origin validation to WebSocket telemetry.
- [x] Validate report IDs as UUIDs before path construction; resolve the destination and verify it remains beneath the reports directory before reading or writing.
- [x] Test missing/invalid credentials, untrusted origins, WebSocket origins, path traversal using encoded slash and backslash forms on Windows-compatible path semantics, and valid UUID access.
- [x] Run focused API security tests; expect unauthorized requests and invalid IDs/origins to be rejected before filesystem access.

### Task 14: Persist active scan transitions and recover interrupted scans

**Files:** Modify `engine/app/services/scan_service.py`, `engine/app/agents/orchestrator.py`, `engine/app/api/v1/router.py`; test `engine/tests/unit/test_scan_service.py` and `engine/tests/integration/test_scan_flow.py`.

- [x] Persist `RUNNING` when execution starts and each durable terminal state when it ends.
- [x] On startup, identify previously queued/running scans whose in-process task no longer exists and mark them `FAILED` or `INTERRUPTED` with an explicit recovery reason.
- [x] Make status and report endpoints show that reason; never leave a crashed scan permanently `QUEUED` or `RUNNING`.
- [x] Test restart recovery using persisted scan rows without launching a browser.
- [x] Run focused lifecycle tests; expect interrupted scans to become terminal and reports to remain inconclusive.

### Checkpoint: Trustworthy results and local boundaries

- [x] Failed/incomplete work cannot be represented as a clean result.
- [x] Report generation cannot escape its output directory.
- [x] Local APIs reject untrusted browser origins.
- [x] Restarted scans reach an honest terminal state.

## Phase 5: Align setup and product claims

### Task 15: Align model setup, KB indexing, and readiness reporting

**Files:** Modify `scripts/setup_models.ps1`, `engine/app/core/config.py`, `engine/app/api/v1/assistant.py`, `docs/user-guide.md`; test `engine/tests/unit/test_assistant_status.py`.

- [x] Make model pull tags exactly match configured attack, judge, recon, triage, embedding, and assistant models; avoid pulling unused models as if required.
- [x] Add an explicit KB indexing step to first-run setup or the user guide, with idempotent behavior.
- [x] Make readiness distinguish daemon reachable, configured model available, and KB indexed; do not label the assistant ready when its configured model is missing.
- [x] Test model availability/status combinations and empty KB status.
- [x] Run focused readiness tests and inspect setup script output; expect each prerequisite to have a clear success/failure message.

### Task 16: Make unfinished MCP, triage, and Electron work explicit

**Files:** Modify `README.md`, `docs/api.md`, `docs/user-guide.md`, `Project-Context/Status.md`, `desktop/package.json`, `desktop/electron/`, `engine/app/mcp/`, and relevant UI status copy.

- [x] Do not claim MCP tool dispatch, model-based triage, or an Electron desktop runtime as active unless its executable path is implemented and verified.
- [x] For this delivery, either implement and verify those components in separate follow-up plans or mark them explicitly as planned/scaffolded; keep the functioning Vite browser client accurately described.
- [x] Update category and scan-scope language to match the 2026 catalog and actual implemented pipelines.
- [x] Check docs for any assertion that a category is supported, that a scan is recon-guided, or that an Electron/MCP path runs; ensure each assertion is backed by an executable path.
- [x] Review the final documentation against API responses and UI labels.

## Final Verification

- [x] Run focused recon, planner, scan, report, API-security, and recovery test suites from `engine/`.
- [x] Run the full engine suite with `cd engine; pytest`.
- [x] Run the desktop build with `cd desktop; npm ci; npm run build`.
- [x] Perform a manual authorized weak-bot and hardened-bot flow: calibrate, run recon, inspect tier statuses and plan, start only a supported category, inspect persisted turns/findings, and generate the report.
- [x] Confirm the weak-bot positive result is reported as a finding and the hardened-bot result is described only for the completed tested scope.
- [x] Confirm failed browser launch, missing optional project path, permission-denied process inspection, missing model, and interrupted scan all yield visible incomplete/unknown states.
- [x] Confirm no report or result labels under-development categories as passed.
- [x] Review the final diff for scope, migrations, security boundaries, and preservation of pre-existing user changes.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| The existing profile and scan-turn schema has old records | Migration or deserialization failures | Keep new fields optional/defaulted and test SQLite migration from the current schema |
| Planner taxonomy changes affect existing UI labels and saved scans | Historic scans could be relabeled incorrectly | Preserve stored canonical IDs and explicitly render 2025 legacy aliases |
| Active probes may alter conversation state | Recon can affect later scans | Use a fresh browser context, record probe turns, and reset/close before attack execution |
| A permission issue is mistaken for a negative result | Categories can be incorrectly suppressed | Carry stage completeness into profile and planner decisions |
| Broad plan tempts implementation of all ten categories at once | False confidence and scope growth | Keep under-development categories `not_tested`; implement each category pipeline in its own follow-up slice |
| Restricting CORS and authenticating local APIs can break the current browser client | Local UI loses API access | Define and test a trusted credential bootstrap for development and packaged clients; do not weaken origin or auth checks to restore connectivity |
| `Project-Context/Status.md` contains old implementation notes | Documentation can contradict new behavior | Update status only after corresponding verified tasks land |

## Task List Summary

1. Canonical taxonomy and category states.
2. Recon completion/evidence contract.
3. Tier 3 negative-evidence correctness.
4. Tier 1 signal boundaries.
5. Tier 2 local discovery and permissions.
6. Tier 3 scope and optional UI.
7. Active probe reliability.
8. Planner rules and prompt metadata.
9. UI recon-to-plan flow.
10. Plan-enforced scan execution.
11. Recon evidence persistence.
12. Inconclusive scan/report semantics.
13. Local API and report path hardening.
14. Scan restart recovery.
15. Model/KB setup and readiness.
16. Truthful MCP/triage/Electron scope.
