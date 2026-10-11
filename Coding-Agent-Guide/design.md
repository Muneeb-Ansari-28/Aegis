# Aegis — Design Decisions & Rationale

This guide records the reasons behind the current eight-week implementation choices. The broader product architecture includes later tracks; delivery status follows `Aegis_8-Week_Plan_with_MCP.md`.

## Active assessment category: LLM07

The initial delivery assesses OWASP LLM07 System Prompt Leakage on targets the team owns or has permission to test. The weak and hardened local targets use a planted fake system prompt and canary (`AEGIS-CANARY-7731`). Attack prompts request disclosure directly in plain language; safe wording rephrases are allowed.

Jailbreaks, role impersonation, instruction overrides, encoding/obfuscation, safeguard bypass, and real secret or credential extraction are excluded. This boundary preserves the requested LLM07 coverage without testing jailbreak vulnerabilities.

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
4. **Interactive In-Browser Calibration:** For complex or non-standard DOM trees, `WebCalibration` provides a visible headful browser with an injected click-capture overlay (`CALIBRATION_OVERLAY_SCRIPT`). Users simply click the input, submit, and response elements to lock in exact CSS selectors without opening DevTools.
