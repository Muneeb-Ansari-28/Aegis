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
