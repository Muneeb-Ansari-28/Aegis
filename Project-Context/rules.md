# Aegis — Coding Agent & Developer Rules

> [!CAUTION]
> These rules are **MANDATORY**. Every coding agent and developer **MUST** follow them without exception. Violation of any rule may compromise the integrity of the Aegis project, introduce security vulnerabilities, or break deterministic guarantees that the architecture depends on. If you are unsure whether an action violates a rule, **stop and ask** before proceeding.

---

## Table of Contents

1. [Post-Implementation Reporting (MANDATORY)](#1-post-implementation-reporting-mandatory)
2. [Architecture Constraints (DO NOT VIOLATE)](#2-architecture-constraints-do-not-violate)
3. [Folder Structure Rules](#3-folder-structure-rules)
4. [Code Quality Standards](#4-code-quality-standards)
5. [Database Rules](#5-database-rules)
6. [MCP Rules](#6-mcp-rules)
7. [Security Rules](#7-security-rules)
8. [Logging Rules](#8-logging-rules)
9. [Git Rules](#9-git-rules)
10. [Testing Gates](#10-testing-gates)
11. [Dependency Rules](#11-dependency-rules)
12. [Documentation Rules](#12-documentation-rules)

---

## 1. Post-Implementation Reporting (MANDATORY)

After **EVERY** implementation task — no matter how small — the agent or developer **MUST** produce a structured report. This is non-negotiable. Skipping a report means the change is untracked, unverifiable, and a liability.

### What Must Be Reported

| Requirement | Description |
|---|---|
| **WHAT was done** | Precise description of every file created, modified, or deleted. Include paths relative to the project root. |
| **WHY it was done** | The rationale behind the change. Which module or gate does it serve? Which section of the architecture does it implement or support? |
| **IF anything was removed** | Explicit explanation of **WHY** it was removed, what it was replaced with (if anything), and **confirmation** that no other component depends on the removed code. If removal causes downstream impact, that impact must be documented. |
| **IF anything was changed from the plan** | Explain the deviation. Justify why the original plan was not followed. Reference the specific section of the architecture document that was deviated from. |

### Reporting Format

Every implementation report **MUST** use the following template exactly:

```
### Implementation Report
**Date**: YYYY-MM-DD
**Contributor**: [Name]
**Module**: [Module number and name]
**Files Changed**:
- `path/to/file.py` — [created/modified/deleted] — [brief description]
**What Was Done**: [description]
**Why**: [rationale]
**Removals**: [list any removed code/files with reasons, or "None"]
**Deviations from Plan**: [list any deviations with justification, or "None"]
**Gate Impact**: [which gate this affects and current gate status]
```

### Reporting Rules

- Reports are **appended** to `Coding-Agent-Guide/logs.md`. They are never inserted, reordered, or overwritten.
- A report must be filed **immediately** after the implementation is complete — not at the end of the day, not in a batch.
- If a single task touches multiple modules, file **one report per module** affected.
- If a task is abandoned or rolled back, a report must still be filed explaining what was attempted and why it was reverted.

> [!IMPORTANT]
> No implementation is considered "done" until its report has been filed. If there is no report, the work does not officially exist.

---

## 2. Architecture Constraints (DO NOT VIOLATE)

These constraints are the foundational invariants of the Aegis system. They exist to ensure determinism, security, and separation of concerns. Violating any of these constraints will introduce unpredictable behavior and is grounds for immediate rollback.

### 2.1 — The Orchestrator Is a Deterministic Python State Machine

The orchestrator decides what runs next using **pure Python logic** — explicit state transitions, if/else chains, or lookup tables. No LLM, no generative AI, no probabilistic model may influence control flow.

- ✅ `if state == SCANNING: next_state = EVALUATING`
- ❌ `next_step = llm.decide("what should we do next?")`

> [!WARNING]
> An LLM deciding control flow means the system's behavior is non-reproducible. This violates the core design principle of Aegis. **NEVER** allow this.

### 2.2 — Generative AI Never Invents Risk Scores

Risk scoring is **pure Python math**. Risk scores are computed from deterministic formulas based on structured inputs (severity, exploitability, impact, confidence). No LLM may generate, adjust, or "estimate" a risk score.

- ✅ `score = severity_weight * severity + impact_weight * impact`
- ❌ `score = llm.evaluate("how risky is this finding?")`

### 2.3 — The Unified Turn Record Is the Single Contract

The **Unified Turn Record** (UTR) is the canonical data structure that every connector must normalize to. It is the single interface between the target interaction layer and the evaluation layer.

- Every connector (HTTP, browser, WebSocket, etc.) **MUST** produce a valid UTR.
- Every evaluator **MUST** consume UTRs and nothing else.
- No component may bypass the UTR by passing raw connector-specific data to an evaluator.

### 2.4 — Pydantic Schemas Are the Single Source of Truth

All data shapes are defined as Pydantic models in `engine/app/schemas/`. These schemas are authoritative.

- If a schema says a field is `Optional[str]`, it is `Optional[str]` everywhere.
- If a connector produces data that doesn't fit the schema, the **connector** is wrong — not the schema (unless a formal schema change is approved).
- TypeScript types in `desktop/src/types/` must mirror the Pydantic schemas exactly.

### 2.5 — Model Names Live ONLY in `config.py`

Model identifiers (e.g., `"gpt-4"`, `"claude-3-opus"`, `"llama-3"`) must **never** appear as hardcoded strings in any file other than `config.py`.

- ✅ `model = Config.EVALUATION_MODEL`
- ❌ `model = "gpt-4o-mini"`

This ensures model swaps are a single-line config change, not a project-wide search-and-replace.

### 2.6 — Agent Prompts Live in `agents/prompts/*.md`

All prompts used by LLM-powered agents must be stored as Markdown files in `agents/prompts/`. They must **never** be written as inline Python strings, f-strings, or concatenated string literals.

- ✅ `prompt = load_prompt("agents/prompts/evaluator_system.md")`
- ❌ `prompt = "You are an AI security evaluator. Analyze the following..."`

This ensures prompts are version-controlled, reviewable, and editable without touching Python code.

### 2.7 — Control Flow Stays in Orchestrator Code, Never Behind MCP

Budgets, retries, escalation logic, and scan lifecycle management are **orchestrator responsibilities**. They must be implemented in Python code within the orchestrator module.

- ✅ Orchestrator checks `attempt_count < max_retries` before re-dispatching.
- ❌ An MCP tool decides whether to retry based on its own internal logic.

MCP tools are **stateless executors**. They do what they are told and return results. They do not make decisions.

### 2.8 — Target Responses Are UNTRUSTED DATA

Any data received from a scan target (HTTP responses, DOM content, WebSocket messages, API responses) is **untrusted by default**. It must be:

- Passed as **quoted data** in prompts, never as raw instructions.
- Sanitized before storage or display.
- Never directly interpolated into shell commands, SQL queries, or LLM system prompts.

> [!CAUTION]
> Treating target responses as trusted input opens the door to prompt injection, SQL injection, and command injection attacks. This is a **security-critical** constraint.

---

## 3. Folder Structure Rules

The Aegis folder structure was designed intentionally and is considered **final from Day 1**. It reflects the modular architecture and must be preserved.

### Hard Rules

| Rule | Detail |
|---|---|
| **No new top-level directories** | The top-level directories (`engine/`, `desktop/`, `agents/`, `docs/`, `tests/`, `Coding-Agent-Guide/`, etc.) are fixed. Do **NOT** add new sibling directories at the project root. |
| **No reorganizing existing packages** | Do not move, rename, or merge existing packages or modules without **explicit written approval** from the project owner. |
| **New files within existing packages are allowed** | You may add new `.py`, `.md`, `.ts`, or other files inside existing directories as needed by the implementation plan. |
| **Files marked `(later)` are stubs** | Some files in the architecture plan are marked `(later)` — they are placeholders for future modules. Do **NOT** implement them before their scheduled module. Creating empty stub files with a `# TODO: Module X` comment is acceptable. |
| **All `__init__.py` files must exist** | Every Python package directory must contain an `__init__.py` file. Do **NOT** delete them, even if they are empty. They are required for Python's package resolution. |

### Consequences of Violation

- Adding a top-level directory will break import assumptions and CI paths.
- Reorganizing packages will break cross-module imports and may invalidate existing tests.
- Implementing `(later)` files prematurely creates untested code with no integration path.

> [!NOTE]
> If you genuinely believe the folder structure needs modification, document your reasoning in a proposal and submit it for review. Do not make the change first.

---

## 4. Code Quality Standards

All code contributed to Aegis must meet the following quality bars. These are enforced both by automated tools and by review.

### 4.1 — Linting and Type Checking

- All Python code must pass **flake8** with the project's configured rules (see `setup.cfg` or `.flake8` if present).
- All Python code must pass **mypy** in strict mode. Type annotations are required on all function signatures.
- Fix lint and type errors **before** committing. Do not commit code with known lint failures and a "fix later" comment.

### 4.2 — Docstrings

- **Every** new function, method, and class must have a docstring.
- Docstrings must describe: what the function does, its parameters, its return value, and any exceptions it raises.
- Use Google-style or NumPy-style docstrings consistently within a module.

### 4.3 — Unit Tests

Unit tests are **required** for the following components:

| Component | Why |
|---|---|
| **Risk Scorer** (`risk_scorer.py`) | Risk scores must be deterministic and verifiable. Every formula must have test coverage. |
| **JSON Guard** (`json_guard.py`) | The parse-and-retry mechanism must be proven to handle malformed LLM outputs correctly. |
| **Deterministic Detector** | Detection logic must be tested against known-good and known-bad inputs. |
| **Any new pure-logic module** | If it contains business logic without external dependencies, it must have unit tests. |

### 4.4 — Integration Tests

Integration tests are **required** for:

- **Connector flows**: Verify that each connector (HTTP, browser, WebSocket) can interact with a mock target and produce valid Unified Turn Records.
- **Full scan orchestration**: Verify that the orchestrator correctly transitions through all states from scan initiation to report generation.

### 4.5 — Benchmark Tests

- **Evaluation judge accuracy**: The LLM judge must achieve **≥ 90% accuracy** on a labelled benchmark dataset of conversation pairs.
- Benchmark results must be logged and tracked over time. Regressions below 90% block the gate.

### 4.6 — JSON Output Enforcement

- The evaluation judge must produce **100% valid JSON output**. No exceptions.
- This is enforced by the `json_guard.py` module, which implements parse-and-retry logic.
- If the LLM produces invalid JSON, `json_guard` must retry up to the configured limit. If all retries fail, the failure must be logged and surfaced — never silently swallowed.

---

## 5. Database Rules

Aegis uses a local SQLite database (upgradable to PostgreSQL) managed by SQLAlchemy ORM and Alembic migrations.

### 5.1 — Runtime Data Location

- All runtime data (databases, logs, cached models) lives in **`%APPDATA%\Aegis`** on Windows (or the platform equivalent).
- Runtime data must **NEVER** be stored inside the repository directory.
- The application must create the `%APPDATA%\Aegis` directory on first run if it does not exist.

> [!WARNING]
> Storing database files in the repo will cause them to be committed to git, bloating the repository and potentially leaking sensitive scan data.

### 5.2 — Schema Changes Require Alembic Migrations

- **Never** modify database tables by hand (e.g., raw SQL `ALTER TABLE` statements).
- All schema changes must be expressed as Alembic migration scripts.
- Migration scripts must be tested: apply the migration to an existing database and verify data integrity.
- Downgrade paths should be provided when feasible.

### 5.3 — Entity Definitions

- All database entities are defined via **SQLAlchemy ORM** in `models/entities.py`.
- Entity classes must use explicit `__tablename__` declarations.
- Relationships must use SQLAlchemy's `relationship()` with proper `back_populates` or `backref`.

---

## 6. MCP Rules

MCP (Model Context Protocol) is used in Aegis to expose tool interfaces. MCP servers in Aegis must be thin, stateless wrappers — not autonomous decision-makers.

### 6.1 — MCP Servers Are THIN Wrappers

- MCP servers expose tools that delegate to real logic in `adapters/`, `rag/`, `evaluation/`, `risk_scorer.py`, and other core modules.
- MCP servers must **NOT** contain business logic. If you find yourself writing `if/else` decision trees inside an MCP tool handler, the logic belongs in a core module instead.

### 6.2 — Transport Rules

- Use **stdio transport** or **localhost-only** connections.
- **Never** expose an MCP server on a network-accessible port (`0.0.0.0`, public IP, etc.).
- MCP servers are local development tools, not production network services.

### 6.3 — `aegis-target` Owns the Playwright Session

- The `aegis-target` MCP server must own and manage the Playwright browser session for the entire duration of a scan.
- No other component may create its own Playwright instance during a scan.
- Session lifecycle (create → use → close) is managed by `aegis-target`.

### 6.4 — Tool I/O Reuses Pydantic Models

- MCP tool inputs and outputs must reuse the Pydantic models defined in `schemas/`.
- Do **NOT** create separate data classes or dictionaries for MCP tool I/O when a Pydantic model already exists.
- This ensures type consistency between the direct Python API and the MCP layer.

### 6.5 — Build Direct Python Version FIRST

- For every feature, implement the **direct Python version first** (function calls, no MCP).
- Only after the direct version is working and tested, wrap it with an MCP tool interface.
- This ensures the core logic is testable independently of the MCP protocol layer.

> [!TIP]
> This "direct first, MCP second" approach makes debugging significantly easier. If something breaks, you can immediately determine whether the issue is in the core logic or the MCP layer.

---

## 7. Security Rules

Aegis is a security testing tool. It must be used responsibly, and its implementation must enforce ethical and legal guardrails.

### 7.1 — Authorization Requirement

- Only scan systems you **OWN** or have **WRITTEN PERMISSION** to test.
- The tool must not facilitate unauthorized access to any system.
- This is not just a guideline — it is a legal requirement in most jurisdictions.

### 7.2 — Consent Screen

- A **consent screen** must be presented during the configuration step, before any scan begins.
- The consent screen must clearly state:
  - What the tool will do (interact with the target system, send prompts, analyze responses).
  - That the user confirms they have authorization to test the target.
  - That scan results will be stored locally.
- The scan must **NOT** proceed until the user explicitly consents.

### 7.3 — Certificate Handling

- **Never** silently install certificates on the user's system.
- If TLS interception is needed (e.g., for proxy-based scanning), the user must be informed and must explicitly approve certificate installation.
- Certificate installation/removal must be logged.

### 7.4 — Proxy and Certificate Endpoints

- Any `proxy/cert` endpoints that handle TLS certificates require **explicit user consent** before activation.
- These endpoints must not be accessible without prior user authorization in the current session.

> [!CAUTION]
> Violating security rules can expose users to legal liability and undermine the trust that Aegis is built on. These rules are absolute.

---

## 8. Logging Rules

All implementation activity must be tracked in the project's implementation log. This log is the authoritative history of what was built, when, and by whom.

### 8.1 — Log Location

- All implementation logs are recorded in **`Coding-Agent-Guide/logs.md`**.

### 8.2 — Log Format

Every log entry must follow this exact format:

```
feature was [implemented/updated/deleted] = brief summary by "[Name]" at [time], [date]
```

`[Name]` must be exactly one of **Muneeb**, **Salman**, or **Shahzaman**. The named person is the responsible project contributor for the task, including work completed with AI assistance. Do not use an AI, tool, or assistant name as the contributor. If the responsible person is not clear, ask before adding the log entry.

**Examples:**

```
Turn Record schema was implemented = added the shared Pydantic contract by "Muneeb" at 14:32, 2026-10-10
risk_scorer.py was updated = aligned deterministic scoring with documented risk rules by "Salman" at 09:15, 2026-10-11
legacy_utils.py was deleted = replaced by core/helpers.py after confirming no remaining imports by "Shahzaman" at 11:00, 2026-10-12
```

### 8.3 — Append-Only Policy

- Logs are **append-only**.
- **Never** delete, modify, or reorder existing log entries.
- If a previous log entry contains an error, add a **correction entry** below it rather than editing the original.

```
[CORRECTION] Previous entry for risk_scorer.py (2026-10-10) misstated the risk formula; actual change was documented-rule weighting by "Salman" at 09:30, 2026-10-11
```

> [!IMPORTANT]
> The append-only policy exists to maintain an auditable history. If entries can be edited or deleted, the log loses its value as a trustworthy record.

---

## 9. Git Rules

Git hygiene is essential for a multi-contributor project. These rules ensure a clean, navigable commit history.

### 9.1 — Commit Message Format

- Every commit message **must** reference the module number it relates to.
- Format: `Module X: <brief description of change>`

**Examples:**

```
Module 1: Add Turn Record Pydantic schema
Module 2: Implement evaluation judge with json_guard retry
Module 3: Add orchestrator state machine with budget tracking
Module 4: Generate styled PDF report with finding evidence
Module 5: Wrap aegis-target as MCP server with stdio transport
```

- If a commit spans multiple modules, list them: `Module 1, 3: Shared schema update for orchestrator integration`

### 9.2 — Files That Must NEVER Be Committed

The following must never appear in a commit:

| Pattern | Reason |
|---|---|
| `__pycache__/` | Python bytecode cache — platform-specific, auto-generated |
| `*.pyc` | Compiled Python files |
| `.env` | Environment variables — may contain secrets (API keys, tokens) |
| `node_modules/` | Node.js dependencies — installed via `npm install` |
| `*.db`, `*.sqlite`, `*.sqlite3` | Database files — runtime data, not source code |

### 9.3 — `.gitignore` Policy

- The `.gitignore` file is **already configured** for the project.
- Do **NOT** modify `.gitignore` without a documented justification.
- If you need to add a new ignore pattern, explain why in the commit message and ensure it does not accidentally ignore source files.

---

## 10. Testing Gates

Aegis development is organized into modules, each ending with a **gate** — a set of pass/fail criteria that must all be satisfied before proceeding to the next module. Gates are non-negotiable checkpoints.

### Gate 1 — Foundation

| Criterion | Pass Condition |
|---|---|
| Database created on start | Application creates the SQLite database in `%APPDATA%\Aegis` on first launch without errors. |
| Turn Record frozen | The Unified Turn Record Pydantic schema is finalized and passes validation tests with sample data. |
| Test bot runs locally | A minimal test chatbot runs locally and can be targeted by the scanner for integration testing. |

### Gate 2 — Evaluation

| Criterion | Pass Condition |
|---|---|
| 100% valid JSON from judge | The evaluation judge produces parseable JSON output on **every** invocation, enforced by `json_guard.py`. Zero parse failures in the test suite. |
| Verdict accuracy ≥ 90% | On the labelled benchmark dataset, the judge's verdicts (exploited / not exploited / uncertain) match ground truth at least 90% of the time. |

### Gate 3 — Orchestration

| Criterion | Pass Condition |
|---|---|
| Weak bot → exploit found and stopped | When scanning a deliberately weak bot, the orchestrator finds an exploit, logs it, and terminates the scan. |
| Hardened bot → 10 attempts, "not exploited" | When scanning a hardened bot, the orchestrator exhausts 10 attempts, concludes "not exploited", and terminates cleanly. |
| Stop works mid-scan | A user-initiated stop command halts the scan gracefully at any point, preserving partial results. |

### Gate 4 — Reporting

| Criterion | Pass Condition |
|---|---|
| Styled PDF produced | The report generator outputs a properly formatted PDF with all required sections. |
| Every finding's evidence matches its DB row | Each finding in the PDF report has evidence text that exactly matches the corresponding database record. No data mismatch. |

### Gate 5b — MCP Integration

| Criterion | Pass Condition |
|---|---|
| MCP scan results match direct version | A scan run through the MCP interface produces identical results to the same scan run via direct Python calls. |
| Killed `aegis-target` server detected and handled | If the `aegis-target` MCP server is killed mid-scan, the orchestrator detects the failure, logs it, and handles it gracefully (retry or abort with clear error). |

> [!NOTE]
> Gates are cumulative. Gate 3 assumes Gates 1 and 2 still pass. If a later change breaks an earlier gate, that regression must be fixed before proceeding.

---

## 11. Dependency Rules

Dependency management must be disciplined to avoid environment drift, version conflicts, and unreproducible builds.

### 11.1 — Python Dependencies

- All Python dependencies must be declared in **`requirements.txt`** (production) or **`requirements-dev.txt`** (development/testing only).
- **No ad-hoc `pip install`** commands in code, scripts, or documentation without also updating the requirements file.
- If you need a new dependency, add it to the appropriate requirements file **first**, then install it.

### 11.2 — Node.js Dependencies

- All Node.js dependencies must be declared in **`desktop/package.json`**.
- **No global installs** (`npm install -g`). All dependencies must be local to the project.
- Use `npm install` (or `npm ci` for reproducible builds) — never `yarn` or `pnpm` unless the project explicitly adopts them.

### 11.3 — Version Pinning

- **Pin major versions** to avoid breaking changes from upstream updates.
- Use `~=` (compatible release) or `>=X.Y,<X+1` notation in Python.
- Use `^X.Y.Z` or explicit ranges in `package.json`.
- After adding or updating a dependency, test that all existing tests still pass.

---

## 12. Documentation Rules

Documentation is not optional. It is a first-class deliverable alongside code.

### 12.1 — Status Tracking

- Update **`Coding-Agent-Guide/Status.md`** after completing any module or gate.
- Status updates must include: module name, completion date, gate pass/fail status, and any blockers.

### 12.2 — Implementation Logs

- Update **`Coding-Agent-Guide/logs.md`** after every implementation session.
- Follow the format specified in [Section 8: Logging Rules](#8-logging-rules).

### 12.3 — API Documentation

- Keep **`docs/api.md`** in sync with actual API endpoints.
- When an endpoint is added, modified, or removed, the API documentation must be updated in the **same commit** or immediately after.
- API docs must include: endpoint path, HTTP method, request/response schemas, error codes, and example payloads.

### 12.4 — TypeScript / Pydantic Sync

- TypeScript types in **`desktop/src/types/`** must mirror the Pydantic schemas in **`engine/app/schemas/`** exactly.
- When a Pydantic schema changes, the corresponding TypeScript type must be updated before the change is considered complete.
- Consider using automated code generation tools to maintain this sync where possible.

> [!TIP]
> A good practice is to review `desktop/src/types/` and `engine/app/schemas/` side-by-side after any schema change to catch drift early.

---

## Quick Reference Checklist

Use this checklist before marking any task as complete:

- [ ] Implementation report filed in `Coding-Agent-Guide/logs.md`
- [ ] No architecture constraints violated (Section 2)
- [ ] No new top-level directories created (Section 3)
- [ ] All new functions have docstrings (Section 4)
- [ ] Required tests written and passing (Section 4)
- [ ] Database changes use Alembic migrations (Section 5)
- [ ] MCP tools are thin wrappers only (Section 6)
- [ ] Security rules followed — consent, authorization, no silent certs (Section 7)
- [ ] Log entry added to `Coding-Agent-Guide/logs.md` (Section 8)
- [ ] Commit message references module number (Section 9)
- [ ] No forbidden files committed (Section 9)
- [ ] Relevant gate criteria still passing (Section 10)
- [ ] Dependencies declared in requirements files (Section 11)
- [ ] Status.md, logs.md, and api.md updated as needed (Section 12)
- [ ] TypeScript types in sync with Pydantic schemas (Section 12)

---

*This document is the law of the Aegis project. When in doubt, follow the rules. When the rules are unclear, ask for clarification. Never assume an exception exists unless it is explicitly granted.*

---

## 13. Implementation Completion Report

After each implementation session, tell the user what changed and why. Keep the report concrete and reviewable:

- Name the files or behavior changed and summarize what was implemented, updated, or fixed.
- Explain the reason for each material design or structural choice.
- If anything was removed, identify it and explain why it was safe or necessary to remove.
- State what was verified and what remains unverified; never report a gate as passed based only on files existing.
- Append a matching entry to `Coding-Agent-Guide/logs.md` with the responsible project contributor's approved name and local time/date. AI assistance is not listed as the contributor.
- Update `Coding-Agent-Guide/Status.md` when implementation progress or gate evidence changes.

Do not silently remove project files or features. Explain deletions in the log and user-facing completion report.
