# Aegis Project Context & Agent Governance

This directory serves as the authoritative single source of truth for software engineers and AI coding agents working on the **Aegis** codebase.

---

## Table of Contents

- [Core Reference Documents](#core-reference-documents)
- [Active Assessment Scope](#active-assessment-scope)
- [Agent Skills & Mandatory Workflow](#agent-skills--mandatory-workflow)
  - [Mandatory Quality Standards](#mandatory-quality-standards)
  - [Lifecycle: Plan -> Implement -> Verify -> Report](#lifecycle-plan---implement---verify---report)
- [Startup & Execution](#startup--execution)

---

## Core Reference Documents

All contributors and AI agents must review these documents before introducing changes:

1. **[rules.md](rules.md)**: Master engineering rules, security boundaries, testing mandates, logging conventions, and completion report requirements.
2. **[architecture.md](architecture.md)**: Architectural specifications, agent contracts, reconnaissance tiers, test planner algorithms, and evaluation defense pipelines.
3. **[design.md](design.md)**: Active design choices, scope boundaries, and implementation rationale.
4. **[Status.md](Status.md)**: Current milestone implementation states, verification gates, and known limitations.
5. **[frontend-design.md](frontend-design.md)**: Approved visual design specifications, component guidelines, and accessibility standards for the desktop workspace.
6. **[folder-structure.md](folder-structure.md)**: Annotated repository directory structure and module layout.
7. **[audit_findings_and_fixes.md](audit_findings_and_fixes.md)**: Record of security audits, bug remediations, and code hardening passes.
8. **[logs.md](logs.md)**: Append-only chronological history of implementations, verification outputs, and milestone sign-offs.

---

## Active Assessment Scope

Aegis aligns strictly with the canonical **OWASP GenAI/LLM Top 10 (2026)** framework:
- **Active Execution Pipeline**: **OWASP LLM08: Hidden Context Exposure** (migrated from OWASP 2025 LLM07 System Prompt Leakage).
- **Execution Strategy**: Direct, plain-language disclosure requests, planted canary tokens (`AEGIS-CANARY-7731`), prompt-overlap heuristics, refusal pre-filtering, and rubric-based judging against authorized web targets.
- **Boundaries**: Offensive jailbreaks, role impersonation, instruction overrides, character encoding tricks, and real secret extraction are strictly excluded from the active scope. Scans must only run against authorized local or private-network targets with explicit written permission.

---

## Agent Skills & Mandatory Workflow

The `.agents/skills/` directory contains curated agent skills. All AI agents modifying code must adhere to these governing standards:

### Mandatory Quality Standards
- **`verification-before-completion`**: **MANDATORY.** Never claim a task, gate, or test passes without running fresh verification commands and confirming terminal output. **Evidence before assertions always.**
- **`systematic-debugging`**: Rigorous root-cause analysis for multi-process (Uvicorn/Vite), Playwright browser calibration, and WebSocket telemetry issues.
- **`spec-to-code-compliance`**: Validates that all changes strictly match `Project-Context/` architecture and design contracts.
- **`modern-python`**: Code quality standard for the FastAPI backend (`engine/`) — type annotations, async conventions, and dependency integrity.
- **`frontend-ui-engineering`**: Enforces responsive, accessible design for the React/Vite client (`desktop/`) per `frontend-design.md`.
- **`test-driven-development`**: Red-green-refactor loop required for pure-logic modules, judge heuristics, and connectors.
- **`security-and-hardening`**: Threat mitigation for LLM prompt injection, subprocess isolation, and target interaction boundaries.

### Lifecycle: Plan -> Implement -> Verify -> Report
For every new feature or bugfix, agents must follow this sequential lifecycle:
1. **Plan & Spec Check**: Review `architecture.md` and formulate an explicit implementation plan.
2. **Implement**: Code changes incrementally with strict typing and unit test coverage.
3. **Verify**: Execute verification commands in the terminal. Confirm exit code 0 and inspect outputs.
4. **Report**: File the mandatory post-implementation report in `Project-Context/logs.md` per `rules.md`.

---

## Startup & Execution

Run the complete stack (FastAPI engine + React desktop) with a single command from the repository root:
```powershell
.\run_aegis.ps1
```

This script auto-detects `.venv`, validates Node.js dependencies, starts both services, and launches the browser at `http://127.0.0.1:3000/`. Press `Ctrl+C` for clean process termination.
