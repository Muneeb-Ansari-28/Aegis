# Aegis — Design Decisions & Rationale

This guide records the reasons behind the current eight-week implementation choices. The broader product architecture includes later tracks; delivery status follows `Aegis_8-Week_Plan_with_MCP.md`.

## Active assessment category: LLM08

The initial delivery assesses OWASP LLM08 Hidden Context Exposure (migrated from OWASP 2025 LLM07 System Prompt Leakage per the canonical OWASP GenAI Top 10 2026 taxonomy) on targets the team owns or has permission to test. The weak and hardened local targets use a planted fake system prompt and canary (`AEGIS-CANARY-7731`). Attack prompts request disclosure directly in plain language; safe wording rephrases are allowed.

Jailbreaks, role impersonation, instruction overrides, encoding/obfuscation, safeguard bypass, and real secret or credential extraction are excluded. This boundary preserves the requested LLM08 coverage without testing jailbreak vulnerabilities.

## Deterministic evaluation

The evaluator checks the planted canary and n-gram overlap against the known test prompt before relying on a rubric judge. A canary match is conclusive test evidence; distinctive prompt overlap is recorded with lower confidence. The test prompt contains fabricated rules only, never real credentials or secrets.

## Architecture decisions

- The orchestrator remains a deterministic Python state machine; models do not select control flow.
- MCP wraps target, knowledge, evaluation, and risk functions while the direct Python implementation remains the underlying logic.
- Pydantic schemas under `engine/app/schemas/` are the API contract and are mirrored by the desktop TypeScript types.
- Agent prompts and versioned knowledge-base records remain separate files for review and tuning.
- Risk scores are computed in deterministic Python code.
- Connector and UI application scanning, packaging, and the website remain later product tracks; the eight-week plan gates take priority.

## Module 2 Design: Playwright Connector & Calibration

1. **Auto-Detection with Fallback:** Chat UIs vary widely across frameworks (React, Vue, custom WebComponents). The connector uses prioritized candidate lists (`CANDIDATE_INPUT_SELECTORS`, `CANDIDATE_SUBMIT_SELECTORS`, `CANDIDATE_RESPONSE_SELECTORS`) to automatically detect standard elements. When detection is ambiguous, explicit `TargetCalibrationConfig` takes precedence.
2. **Dual-Mode Submission (Button vs Enter):** Many chat interfaces omit a dedicated submit button or disable it dynamically. The connector first attempts clicking a visible submit element; if absent, it issues a synthetic `Enter` keypress on the active input element.
3. **Streaming-Aware Polling:** Generative LLM responses stream token-by-token. Reading DOM text once risks capturing partial tokens. The adapter polls the response element at 200ms intervals until the content stabilizes across consecutive checks (default 800ms stability threshold).
4. **Interactive In-Browser Calibration:** For complex or non-standard DOM trees, `WebCalibration` provides a visible headful browser with an injected click-capture overlay (`CALIBRATION_OVERLAY_SCRIPT`). Users open the chat if needed, then select input and Send controls. Response detection is automatic.
5. **Desktop UI Entry Point:** The desktop assessment form calls the target calibration routes, so Playwright owns browser startup, selector capture, and saving calibrated selectors to the registered target. Authorization is confirmed before auto-detection or interactive calibration. The UI only presents LLM08 as runnable; the other OWASP entries remain visible as future scope.

## Browser interaction reliability correction (2026-10-21)

The approved scope is native headed sizing, automatic chat opening, and connector-failure handling; Results & Findings UI Milestone 5 is not part of this work.

- A fixed 1280x800 emulated viewport remained unchanged when Windows maximized the native browser; this laptop's maximized native content height was approximately 730px. Headed scanning and both calibration modes now use native sizing, while headless behavior remains deterministic. Website content-width rules and Windows settings are unchanged.
- Calibration previously opened the chat but scanning started a new context without doing so. A shared helper now checks the configured input, waits for rendering or a supported launcher, clicks a launcher at most once, and verifies visibility, editability, and click actionability before submission. The readiness budget is at most five seconds, capped by the adapter timeout; errors retain diagnostic details. No calibration field or database migration was added.
- Generic search fields must not prevent opening a lazy-mounted chatbot, and hidden unrelated textareas must not override visible specific composers. These cases have regression coverage. Existing main-document launcher heuristics remain finite; iframe/shadow-specific calibration and arbitrary custom launchers are not newly implemented.
- Connector errors/timeouts stop the scan as failed and do not enter the LLM08 evaluator. Failed turn verdicts are null. The existing response column retains reserved `[CONNECTOR_ERROR]` / `[CONNECTOR_TIMEOUT]` diagnostics for status replay. Legacy replay infers status from these markers; historical scan states/verdict rows are not rewritten. A genuine reply beginning with a reserved marker is a limitation of this migration-free compatibility path.
- Scan activity distinguishes connector diagnostics from chatbot replies and suppresses misleading legacy verdicts. Turn status no longer overwrites scan lifecycle status. The layout and vulnerability rules are unchanged.


## Results presentation decisions - Milestone 5

The approved Results reference determines the overview composition; implemented sections and data semantics are maintained in [frontend-design.md, Section 9](frontend-design.md#9-results-findings). Reuse the existing Inspector and PDF client rather than introducing a second Results implementation.

Counts, severity, and risk grade remain backend-derived; the frontend does not assign severity or letter grades. A missing request is not a zero result, and a connector diagnostic is not an evaluated chatbot response. The overview presents only persisted cases, not fabricated pending cases from unused budget. The backend stops on the first positive verdict, so reference-image counts and multiple sample findings are not promised production outcomes. Existing shell/navigation is preserved; screenshot-only report-preview and interface-type controls are not invented. Implementation is awaiting visual approval and live integration acceptance; screenshot comparison is not exact-parity certification.
