# Project Context

This folder is the single source of truth for AI agents and contributors working on Aegis.
Read all files here before implementing anything.

## References

1. [Rules](rules.md) — implementation, security, testing, logging, and completion reports.
2. [Architecture](architecture.md) — system boundaries and delivery contracts.
3. [Design](design.md) — active scope and implementation rationale.
4. [Folder structure](folder-structure.md) — planned layout and current repository comparison.
5. [Status](Status.md) — implementation and gate state.
6. [Frontend design](frontend-design.md) - approved visual specification and current implementation notes.
7. [Logs](logs.md) — append-only history.

## Key Project Documents

- `Aegis_8-Week_Plan_with_MCP.md` — delivery source for the active LLM08 scope and MCP sequence.
- `Aegis-Architecture.pdf` — broader product architecture.
- `Aegis-Folder-Structure-Guide.pdf` — team-facing annotated directory tree.

The current assessment scope is **OWASP LLM08 Hidden Context Exposure** (migrated from OWASP 2025 LLM07 System Prompt Leakage per the canonical OWASP GenAI/LLM Top 10 2026 taxonomy) using direct, plain-language
disclosure requests against authorized web targets. Jailbreak methods remain excluded.

## Agent Skills & Mandatory Workflow

The `.agents/skills/` folder contains curated skills for AI coding agents working on Aegis.
All agents implementing features or fixes **MUST** adhere to the rated skills below:

### Excellent (Core & Mandatory)

These skills directly govern Aegis's core architecture and must be actively followed:

- **`verification-before-completion`**: **MANDATORY.** Never claim a task, gate, or test passes without running fresh verification commands and checking terminal output.
- **`systematic-debugging`**: Rigorous root-cause analysis for multi-process (Uvicorn/Vite), Playwright browser calibration, and SSE/WebSocket failures.
- **`spec-to-code-compliance`**: Validates that all changes strictly match `Project-Context/` architecture and design contracts.
- **`modern-python`**: Code quality standard for the FastAPI backend (`engine/`) — typing, async conventions, and dependency integrity.
- **`frontend-ui-engineering`**: Enforces responsive, accessible design for the React/Vite client (`desktop/`) per `Project-Context/frontend-design.md`.
- **`test-driven-development`**: Red-green-refactor loop required for pure-logic modules, judge heuristics, and connectors.
- **`security-and-hardening`**: Threat mitigation for LLM prompt injection, subprocess isolation, and target interaction boundaries.
- **`api-and-interface-design`**: Stable, typed REST contracts between engine endpoints (`:8765`) and desktop frontend (`:3000`).
- **`constraint-driven-development`**: Guards against silently weakening project test bars, deleting checks, or bypassing gates.
- **`debugging-and-error-recovery`**: Systematic troubleshooting for external service disconnects (Ollama, Playwright, SQLite).
- **`observability-and-instrumentation`**: Structured JSON logging across attack agents, calibration runs, and evaluation judges.
- **`git-workflow-and-versioning`**: Multi-developer branch discipline (`main`, `muneeb`, `salman`, `shahzaman`) and atomic commits.
- **`differential-review`**: Blast-radius calculation on branch diffs prior to merging.
- **`source-driven-development`**: Grounding all implementation decisions in verified official library documentation.
- **`browser-testing-with-devtools`**: Real-time DOM inspection during web target calibration.
- **`code-review-and-quality`**: 5-axis code quality review prior to PR submission.
- **`playwright-skill`**: Browser automation patterns, robust locators, and wait strategies for web target calibration.
- **`agentic-actions-auditor`**: CI/CD and AI agent integration vulnerability assessments.

### Good (High-Value Workflow & Quality Tools)

- **Planning & Task Breakdown**: `writing-plans`, `planning-and-task-breakdown`, `executing-plans`, `incremental-implementation`, `subagent-driven-development`
- **Quality & Review Loops**: `review-pr`, `code-improver`, `pr-improver`, `code-simplification`, `second-opinion`, `receiving-code-review`, `requesting-code-review`, `panel-review`
- **Architecture & Architecture Decisions**: `spec-driven-development`, `doubt-driven-development`, `documentation-and-adrs`, `sharp-edges`, `deprecation-and-migration`
- **Branch & Performance**: `finishing-a-development-branch`, `using-git-worktrees`, `performance-optimization`, `context-engineering`, `dispatching-parallel-agents`

### Standard Feature Implementation Lifecycle

For any new feature or bugfix, the agent workflow must be:

1. **Plan & Spec Check**: Check `Project-Context/architecture.md` using `spec-to-code-compliance` and `writing-plans`.
2. **Implement**: Apply `modern-python` (backend) or `frontend-ui-engineering` (frontend) with `test-driven-development`.
3. **Verify**: Execute terminal tests using `verification-before-completion`. **Evidence before assertions.**
4. **Report**: File the mandatory post-implementation report in `Project-Context/logs.md` per `rules.md`.

## Startup

Run the full stack (engine + desktop) with a single command from the repo root:

```powershell
.\run_aegis.ps1
```

This script auto-detects `.venv`, installs desktop npm deps on first run, starts both processes,
and opens the browser at `http://127.0.0.1:3000/`. Press `Ctrl+C` to stop everything cleanly.
