# Project Context

This folder is the single source of truth for AI agents and contributors working on Aegis.
Read all files here before implementing anything.

## References

1. [Rules](rules.md) — implementation, security, testing, logging, and completion reports.
2. [Architecture](architecture.md) — system boundaries and delivery contracts.
3. [Design](design.md) — active scope and implementation rationale.
4. [Folder structure](folder-structure.md) — planned layout and current repository comparison.
5. [Status](Status.md) — implementation and gate state.
6. [Logs](logs.md) — append-only history.

## Key Project Documents

- `Aegis_8-Week_Plan_with_MCP.md` — delivery source for the active LLM07 scope and MCP sequence.
- `Aegis-Architecture.pdf` — broader product architecture.
- `Aegis-Folder-Structure-Guide.pdf` — team-facing annotated directory tree.

The current assessment scope is **OWASP LLM07 System Prompt Leakage** using direct, plain-language
disclosure requests against authorized web targets. Jailbreak methods remain excluded.

## Agent Skills

The `.agents/skills/` folder contains skills for AI coding agents working on this project.
As of 2026-10-16 a skills audit was performed: 74 irrelevant skills (blockchain scanners,
fuzzing tools, C/C++/Rust tooling, Trailmark graph tools) were removed, leaving **54 skills**
that are directly relevant to the Python/FastAPI/Playwright/TypeScript/Electron/MCP stack.

## Startup

Run the full stack (engine + desktop) with a single command from the repo root:

```powershell
.\run_aegis.ps1
```

This script auto-detects `.venv`, installs desktop npm deps on first run, starts both processes,
and opens the browser at `http://127.0.0.1:3000/`. Press `Ctrl+C` to stop everything cleanly.

