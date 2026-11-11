# Profile-Guided Multi-Category Scan Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** After a user submits an authorized local target, automatically run recon and planning, then let them choose any supported subset of applicable OWASP 2026 categories or run all categories currently ready for testing.

**Architecture:** Treat recon as a staged profile process and planning as a deterministic, evidence-backed decision over all ten canonical categories. The UI defaults to a concise list of categories that are both applicable/testable and implemented, while retaining an expandable view of every category with clear exclusion reasons. Scan creation sends a profile/plan revision and category IDs; the backend revalidates the set and executes each accepted category independently under a shared assessment, reporting per-category outcomes.

**Tech Stack:** Python 3.12, FastAPI, Pydantic 2, SQLAlchemy/SQLite, React, TypeScript, Playwright, pytest, Vite.

**Spec:** Canonical taxonomy: `engine/knowledge/owasp/OWASP-LLM-Top-10-2026.md`. Prerequisite foundation and identified fixes: `docs/superpowers/plans/2026-11-11-recon-planner-and-audit-fixes.md`.

## Global Constraints

- Use the OWASP 2026 IDs and names from `engine/knowledge/owasp/OWASP-LLM-Top-10-2026.md` everywhere new behavior displays, stores, or reports categories.
- All ten categories remain represented in the planner response; the default selector shows only categories eligible to execute and includes an explicit “Show all 10” view.
- Eligibility requires both planner testability (`ready` or an explicitly supported `partial` state) and a complete implemented prompt, execution, and evaluation pipeline.
- Under-development categories remain visible as disabled with a reason, have no executable prompts, are excluded from “Run all,” and cannot be forced through the API.
- “Run all” means every currently eligible category in the latest plan snapshot. Show the exact count and category names before starting; never imply that it means all ten if some are not executable.
- Recon establishes capabilities and testability only. It does not report vulnerabilities or guarantee that an applicable category will find one.
- Unknown, skipped, failed, inaccessible, or permission-limited recon evidence must not be treated as proof a capability is absent.
- Tier 3 project inspection stays optional and requires an explicitly selected project path. Active probes and scans require explicit authorization and remain limited to authorized local/private targets.
- The user must select at least one eligible category to start a manual selection. Each selected category uses its own category-correct prompts, evaluator, budget, and result status.
- Existing audit-plan tasks establish catalog, evidence semantics, recon API, and scan enforcement. This workflow plan supersedes its one-category-per-scan constraint and specifies how those tasks connect to multi-category UI and execution.

## Review Focus

- A browser or passive-recon failure must leave capability-dependent categories unknown, not hide them as inapplicable; test partial recon results.
- A stale profile/plan or a client-tampered category list must be rejected before target interaction; test revision mismatch and unsupported IDs.
- A category that is applicable but still under development must remain unselectable; test both manual selection and “Run all.”
- A failure in one category must preserve other category outcomes and must not make the overall assessment appear fully clean; test mixed success/failure results.
- An empty eligible set, all-under-development plan, or changed plan between selection and start must provide an actionable state and must not enqueue a scan.

---

## File Map

- `engine/app/schemas/test_plan.py`: canonical per-category plan state, reasons, and a plan revision/snapshot reference.
- `engine/app/schemas/scan.py` (or the existing scan request schema): selected category IDs and plan revision on scan creation.
- `engine/app/services/recon_service.py` and `engine/app/api/v1/targets.py`: staged recon launch, authorization options, and progress/result contract.
- `engine/app/services/test_planner.py` and `engine/app/agents/planner/rules.py`: evidence-to-category applicability and executable eligibility.
- `engine/app/services/scan_service.py` and `engine/app/agents/orchestrator.py`: server-side validation and per-category execution under one assessment.
- `engine/app/models/entities.py` and `engine/app/core/database.py` only if a persistent assessment/category-run relation is needed by the current schema; migrations live in `engine/migrations/`.
- `desktop/src/api/client.ts`: typed recon, plan, and multi-category scan calls.
- `desktop/src/hooks/useAssessmentWizard.ts`: workflow state, stale-result handling, and selection validation.
- `desktop/src/components/NewAssessment.tsx` and focused category-picker components: staged progress, category selection, Run all, and rationale disclosure.
- `desktop/src/views/FindingsInspector.tsx` and report templates only where required to display per-category outcomes accurately.
- Focused tests under `engine/tests/unit/`, `engine/tests/integration/`, and the existing desktop test structure.

## Implementation Tasks

### Task 1: Define category readiness and plan snapshot contract

**Files:** Modify `engine/app/schemas/test_plan.py`, `engine/app/agents/planner/category_catalog.py`, and `engine/app/services/test_planner.py`; test `engine/tests/unit/test_test_planner.py` and `engine/tests/unit/test_category_catalog.py`.

**Interfaces:** Produce `CategoryPlan` entries for all ten canonical IDs with `implementation_status`, `testability`, `applicability`, `reason`, `planned_prompt_ids`, and a derived `selectable` boolean. Produce a deterministic plan/profile revision identifier suitable for stale-request detection.

- [x] Add contract tests covering all ten 2026 IDs, readiness derivation, and plan revision stability for identical profile/catalog inputs.
- [x] Define `applicability` as `applicable`, `not_applicable`, or `unknown`; keep it separate from `implementation_status` and `testability`.
- [x] Derive `selectable=true` only when the implementation is complete and testability is `ready` or explicitly supported `partial`; require applicable or policy-approved unknown evidence for that test.
- [x] Ensure `not_applicable` requires affirmative evidence and a category prerequisite rule; failed or omitted recon stages yield `unknown`.
- [x] Ensure under-development categories have no prompt IDs and `selectable=false` even when their capability prerequisite is observed.
- [x] Verify category ID/name ordering against the 2026 Markdown source and run the focused planner/catalog tests.

### Task 2: Make target submission start the staged recon workflow

**Files:** Modify `engine/app/api/v1/targets.py`, `engine/app/services/recon_service.py`, `desktop/src/api/client.ts`, and `desktop/src/hooks/useAssessmentWizard.ts`; test `engine/tests/unit/test_recon_api.py` and add/update `engine/tests/integration/test_recon_and_planner_flow.py`.

**Interfaces:** Target submission returns a target ID and recon-run ID/status. Recon exposes distinct stage states for passive collection, optional local discovery, optional project inspection, calibration, and active benign probes. The desktop polls or subscribes to stage updates through the existing status mechanism.

- [x] After target URL validation and explicit authorization, create the assessment and automatically enqueue passive Tier 1 recon; show its progress in the wizard.
- [x] Present Tier 2 local process discovery with its permission boundary and result separately; a permission denial is `skipped/permission_denied`, not a negative finding.
- [x] Present Tier 3 project inspection as optional, request a project path only if the user opts in, and preserve unknown results when the user skips it.
- [x] Keep chat-based benign probes behind calibration and explicit active-probe authorization; after calibration, run them in a fresh context and attach their evidence to this recon run.
- [x] Have recon produce a profile snapshot and invoke the planner when required stages finish; if a stage fails, still produce a partial plan with unresolved capability states and visible reasons.
- [x] Test URL rejection, passive-stage progress, calibration gating, optional Tier 3 omitted/provided, permission denial, and partial recon completion.

### Task 3: Return an explanatory plan and eligible category list

**Files:** Modify `engine/app/services/test_planner.py`, `engine/app/api/v1/targets.py`, and `desktop/src/api/client.ts`; test `engine/tests/unit/test_test_planner.py` and `engine/tests/unit/test_recon_api.py`.

- [x] Return all ten category entries in canonical 2026 order after recon, including applicable, not-applicable, unknown, under-development, and reason fields.
- [x] Derive a separate `selectable_category_ids` list from the exact entries whose `selectable` field is true; do not let the frontend recreate planner policy.
- [x] Include the profile revision, plan revision, recon completion summary, and whether the plan is complete or partial.
- [x] Test evidence combinations for the profile-linked rules from the prerequisite plan: tool evidence and LLM03, vector/RAG evidence and LLM09, verified rendering and LLM10, and disclosure-related evidence and LLM08, using canonical 2026 names.
- [x] Test that unknown does not collapse into not-applicable, while under-development remains non-selectable regardless of capability profile.

### Task 4: Build the category selection and Run all experience

**Files:** Modify `desktop/src/hooks/useAssessmentWizard.ts`, `desktop/src/components/NewAssessment.tsx`, and `desktop/src/components/new-assessment.css`; add a focused picker component only if it fits the current component structure. This desktop currently has no test runner, so verify with the TypeScript/Vite build and a documented manual wizard walkthrough rather than introducing a test framework solely for this change.

**Interfaces:** Picker receives the backend plan and returns a non-empty subset of `selectable_category_ids`, or all selectable IDs through `Run all`.

- [x] Default to a concise “Ready to scan” list containing only selectable categories; show canonical ID, 2026 name, and a short profile-based rationale.
- [x] Add “Show all 10” to inspect excluded categories. Explain “Not applicable,” “Profile inconclusive,” and “Under development” distinctly; disabled entries cannot be selected.
- [x] Provide multi-select for one or more eligible categories and a “Run all ready categories” action that selects exactly the backend-provided eligible IDs.
- [x] Before run, show the exact category count and names; state that Run all excludes unsupported/under-development categories.
- [x] Disable start for empty selection, recon/plan failure without a documented manual-scope path, or a stale plan; show a retry/recon action and preserve the user's current selections only when IDs still exist in the refreshed eligible set.
- [x] Build the desktop and manually verify one selection, arbitrary subset, Run all, zero eligible categories, mixed applicable/unknown/under-development entries, and preservation/reset of selections after plan refresh.

### Task 5: Accept and revalidate multiple categories at scan start

**Files:** Modify the existing scan request schema, `engine/app/api/v1/router.py`, `engine/app/services/scan_service.py`, and `engine/app/agents/orchestrator.py`; test `engine/tests/unit/test_scan_service.py` and `engine/tests/integration/test_scan_flow.py`.

**Interfaces:** Request accepts `category_ids: list[str]` and `plan_revision: str`; rejects empty/duplicate IDs and mismatched revisions. Server resolves every ID against the current plan before scheduling work.

- [x] Add tests that stale revision, unknown ID, duplicate ID, under-development ID, not-applicable ID, non-selectable ID, and empty selection fail before any target interaction.
- [x] Recompute or retrieve the current profile-backed plan at start and require exact revision match; never trust client-supplied applicability, prompt IDs, or budgets.
- [x] Resolve each accepted category to its own prompt IDs, evaluator, and configured category budget; reject any category lacking a complete execution path.
- [x] Create one parent assessment scan with ordered child category runs, or an equivalent durable structure that preserves independent per-category status and shared target/recon provenance.
- [x] Execute category runs sequentially under the parent assessment initially, with independent progress and failure capture; continue to later selected categories after an isolated category failure unless the parent is explicitly stopped/cancelled.
- [x] Test mixed category outcomes and assert that no prompts/evaluator from one category are routed into another.

### Task 6: Aggregate results without overstating coverage

**Files:** Modify `engine/app/services/report_service.py`, `engine/app/agents/reporting_agent.py`, `engine/app/templates/report.html`, and `desktop/src/views/FindingsInspector.tsx`; test `engine/tests/unit/test_report_service.py` and `engine/tests/integration/test_report_generation.py`.

- [x] Record selected, started, completed, failed, and stopped category IDs plus excluded categories and reasons in assessment metadata.
- [x] Show findings and completion status per category; a successful category must not cause failed, stopped, or unstarted sibling categories to display as passed.
- [x] Define the parent assessment as complete only when every selected category reaches a terminal state; define it as inconclusive/partial when any selected category fails or is stopped.
- [x] Keep “no vulnerability found” scoped to completed category runs with successful evaluated turns; never infer coverage of omitted, not-applicable, unknown, or under-development categories.
- [x] Test all-complete, one-category-failed, stopped-mid-run, zero-successful-turn, and mixed findings/no-findings reports.

### Task 7: End-to-end workflow verification and documentation

**Files:** Update `docs/user-guide.md`, `docs/api.md`, `desktop/src/hooks/useAssessmentWizard.ts`, and `desktop/src/components/NewAssessment.tsx`; update the cross-reference in `docs/superpowers/plans/2026-11-11-recon-planner-and-audit-fixes.md` as part of implementation handoff.

- [x] Document the flow from URL submission to recon, optional tiers, calibration/active probes, plan, category selection, scan, and per-category results.
- [x] Document `Run all` as all categories selectable in the latest plan, not all ten taxonomy entries.
- [x] Verify the normal local-target workflow with one selectable category, a multi-category subset, Run all, a partially failed recon, and no eligible categories.
- [x] Verify optional Tier 3 is never required and incomplete/permission-limited recon never suppresses categories as not-applicable.
- [x] Run focused backend tests and `cd desktop; npm run build`; manually exercise the wizard because the current desktop project has no configured test runner. Confirm all visible taxonomy labels match `OWASP-LLM-Top-10-2026.md`.

## Dependency and Scope Notes

1. Implement the prerequisite plan's category catalog, evidence contracts, recon reliability, security boundaries, and report truthfulness before or alongside Tasks 1–3 and 5–6 here.
2. This plan supersedes the prerequisite plan's constraint “Keep one selected category per scan.” Update that line to reference this plan; Tasks 9–10 of the prerequisite plan should use plural category selection and server-side validation as described here.
3. Do not implement attack libraries for all ten categories as a side effect of this workflow. Categories remain under development until prompts, execution, and evaluation are complete; this workflow automatically includes newly implemented categories only when the backend plan marks them selectable.
4. Keep scan execution sequential for this initial implementation to avoid shared browser/session and per-category evidence races. Parallel execution requires a separate resource-isolation decision.

## Acceptance Criteria

- Submitting an authorized local URL automatically starts passive recon and makes stage progress visible.
- Planner runs from the resulting profile and returns all ten canonical categories with explicit evidence, applicability, testability, and implementation status.
- The default picker contains only backend-approved selectable categories; “Show all 10” explains the remaining categories and does not make them executable.
- The user can start any non-empty subset of eligible categories or Run all of the eligible categories in the current plan.
- Backend revalidation prevents stale or manipulated clients from starting unsupported categories.
- Results and reports distinguish each category’s completed, failed, stopped, excluded, and untested status without claiming broader coverage.
