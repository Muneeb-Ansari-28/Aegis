# Aegis 40% Milestone: 8-Week Plan (With MCP)

Scope: web-based scanning with Playwright, covering the configuration module, orchestrator, attack, evaluation and risk scoring agents, for one OWASP category. In this version the agents reach the connector, knowledge base, evaluation checks and risk code through **MCP (Model Context Protocol) tools**, while the orchestrator stays a deterministic Python state machine.

## Recommended category: LLM07, System Prompt Leakage

I'd pick this one over Prompt Injection (LLM01) for these reasons:

- **You can build ground truth.** On your own test chatbot you plant a system prompt containing a unique canary string (e.g. `AEGIS-CANARY-7731`) and fake "secret" rules. Leakage can then be checked partly by code (exact match, n-gram overlap) before any LLM judge is involved. This makes the Evaluation Agent far easier to validate.
- **It uses your own example.** §8.7 of the architecture already describes partial disclosure ("I can't reveal it, but my instructions tell me to prioritize…"), so the success/failure indicators are already designed.
- **The attack set is small.** Instruction override, role play, "repeat everything above", translation and encoding tricks, and context wrapping cover most of it, and they map directly onto your mutation menu (§8.6).
- **LLM01 is a cheap stretch goal.** The whole pipeline is category-agnostic, so adding LLM01 later only needs new KB records.

## Architecture decision: MCP as the tool layer

MCP is a **tool layer**, not a replacement for the pipeline. The orchestrator stays plain Python (§7.1: no LLM routing in the control plane). The agents and the orchestrator act as **MCP clients** that call tools exposed by small **MCP servers**, each of which is a thin wrapper over code that already exists.

| MCP server | Tools it exposes | Wraps |
| --- | --- | --- |
| `aegis-target` | `open_target`, `calibrate_target`, `send_prompt` (returns a Turn Record), `reset_session`, `close_target` | `adapters/` |
| `aegis-kb` | `get_owasp_record`, `retrieve_attack_seeds`, `get_eval_criteria`, `list_mutation_strategies` | `rag/` and `kb/` |
| `aegis-eval` | `canary_check`, `overlap_score` (deterministic) | `agents/evaluation/deterministic.py` |
| `aegis-risk` | `compute_severity`, `compute_grade` | `agents/risk_scorer.py` |

Why this is worth doing:

- It makes "one engine, many connectors" (§4) stronger. A future Application Scanner is just another MCP server exposing the same `send_prompt` tool, so the orchestrator never changes.
- Tools are discoverable and independently testable.
- It gives you a clear answer when the supervisor asks how MCP is used.

What stays out of MCP:

- **Control flow.** Budgets, retries and escalation stay in orchestrator code. The LLM never decides what runs next.
- **Risk math.** It may sit behind a tool for consistency, but the computation remains pure Python. Generative AI never invents risk scores.

Two usage modes:

1. **Orchestrator-driven (build first).** Orchestrator code calls tools through the MCP client and hands results to the agents. Predictable, easy to test, and reliable with a 4B model.
2. **Agent-driven tool calling (optional).** Qwen3-4B receives a tool list and chooses calls itself. Limit this to the Attack Agent with only `retrieve_attack_seeds` and `list_mutation_strategies`, and fall back to mode 1 if the model returns a malformed tool call.

Build order: implement the direct Python version first (Weeks 2–5) so Gates 1–3 pass, then put MCP over it in Module 5b. That way the refactor cannot block the core loop.

## Module-wise plan (8 weeks)

| # | Module | Weeks | Output |
| --- | --- | --- | --- |
| 1 | Foundation and test target | 1 | Repo, engine skeleton, DB, Turn Record, vulnerable test chatbot |
| 2 | Configuration module and Playwright connector | 2–3 | Register and calibrate a web target, send a prompt, get a Turn Record |
| 3 | Knowledge base (LLM07) and Attack Agent | 3–4 | Seeds, templates, mutations, PAIR-style loop input |
| 4 | Evaluation Agent | 4–5 | Triage, judge and canary check returning a structured verdict |
| 5 | Orchestrator | 5–6 | State machine with budget N ≤ 10 and feedback loop |
| 5b | MCP tool layer | 6 | Four MCP servers plus a client; the orchestrator calls tools over MCP |
| 6 | Risk scoring, persistence, minimal report | 6–7 | Deterministic score, findings in SQLite, PDF |
| 7 | Integration, minimal UI, hardening, demo | 7–8 | End-to-end scan from a config screen |

The orchestrator is built mid-plan, but I'd create a **skeleton with mock agents in Week 2**, so every later module plugs into a working loop instead of being integrated at the end.

## Detailed breakdown

### Module 1: Foundation and test target (Week 1)

| Step | Time |
| --- | --- |
| Set up the repo per the final folder structure below (engine/, desktop/, test-targets/), FastAPI hello-world, config | 1 day |
| Define the **Unified Turn Record** (Pydantic model) and the base connector interface | 1 day |
| Create the SQLAlchemy models and SQLite DB (targets, scans, scan_turns, findings) | 1 day |
| Install Ollama and pull Qwen3-4B-Q4 and Llama-Guard-3-1B. Benchmark speed and VRAM on your hardware | 1 day |
| Build the **vulnerable test chatbot** (simple web chat UI plus a local LLM with a canary system prompt, with a weak and a hardened variant) | 1 day |

**Gate 1:** the DB is created on start, the Turn Record is frozen, and the test bot runs locally.

### Module 2: Configuration module and Playwright connector (Weeks 2–3)

| Step | Time |
| --- | --- |
| Target API: `POST /targets`, plus validation (URL, name, type) | 1 day |
| Playwright connector: open the page, type into the input, click send | 2 days |
| Streaming-aware response capture (poll until the text is stable) | 1.5 days |
| Calibration flow: visible browser, the user clicks the input and the reply area, selectors are recorded and saved to `calibration_config` | 2.5 days |
| Manual login support (the user signs in inside the Playwright window, then the session is reused) | 1 day |
| Normalize to a Turn Record (latency, status, timestamp, attempt number) | 0.5 day |
| **Orchestrator skeleton with mock agents** (a loop that runs end-to-end with fake attack and judge). Calls adapters directly for now; MCP comes in Module 5b | 1.5 days |

**Gate:** you can calibrate the test bot once, then send 20 prompts without any manual copy-paste and get 20 valid Turn Records.

### Module 3: Knowledge base and Attack Agent (Weeks 3–4)

| Step | Time |
| --- | --- |
| Write the LLM07 OWASP record (JSON, versioned "2025") with indicators and techniques | 1 day |
| Prompt library: 15–25 fixed and template prompts with metadata (technique, difficulty, mutation_allowed) | 2 days |
| Define the mutation menu (rephrase, persona change, contextual framing, encoding, multi-turn) as named strategies | 1 day |
| Embeddings and vector store (nomic-embed plus ChromaDB), with retrieval filtered by category | 1.5 days |
| Attack Agent v1: select a seed, fill template variables, send (no mutation yet) | 1 day |
| Attack Agent v2: mutation using the previous refusal plus the judge's rationale, constrained to a named strategy | 2.5 days |

**Gate 3:** a failed attempt produces a *different*, strategy-labelled prompt, and it is logged.

### Module 4: Evaluation Agent (Weeks 4–5)

| Step | Time |
| --- | --- |
| Deterministic **canary and overlap detector** (exact match, fuzzy match, n-gram overlap against the known system prompt) | 1.5 days |
| Stage 1 triage with Llama-Guard-3-1B (safe/unsafe filter) | 1 day |
| Stage 2 judge: Qwen3-4B with a rubric, output as the JSON verdict from §8.7 | 2 days |
| Parse-and-retry for strict JSON (max 3 retries, then a safe default) | 1 day |
| Build a **benchmark set of ~50 labelled prompt/response pairs** (clear fail, partial leak, full leak, fabricated prompt) | 1.5 days |
| Tune the rubric against the benchmark | 1.5 days |

**Gate 2:** 100% valid JSON, and verdict accuracy measured on the benchmark (set a target, e.g. ≥ 90%).

Design note: for LLM07 you have ground truth, so let the deterministic detector override or cross-check the LLM judge. This makes your judge's accuracy demonstrable in front of evaluators.

### Module 5: Orchestrator (Weeks 5–6)

| Step | Time |
| --- | --- |
| Replace the mocks with the real Attack, Connector and Evaluation agents | 1.5 days |
| State machine: states (QUEUED, RUNNING, COMPLETED, STOPPED, FAILED), per-category budget N ≤ 10 | 2 days |
| Escalation node: stop on the first confirmed exploit, loop back with feedback if the budget remains | 1.5 days |
| Error handling: connector timeouts, a locator that no longer works, model JSON failures, a graceful stop | 2 days |
| Scan endpoints (`start`, `status`, `stop`) plus the WebSocket live log | 2 days |

**Gate 3 (loop):** against the weak bot the loop finds a leak and stops. Against the hardened bot it uses all 10 attempts and reports "not exploited". `stop` works mid-scan.

### Module 5b: MCP tool layer (Week 6)

Add this once the direct loop passes its gate, so the refactor stays low-risk.

| Step | Time |
| --- | --- |
| Install the official `mcp` Python SDK. Build `mcp/client.py` (one long-lived session per server, call helper, timeouts) and the `aegis-target` server, then switch the orchestrator to call `send_prompt` over MCP | 1 day |
| `aegis-kb` and `aegis-eval` servers (retrieval and the deterministic canary check) | 1 day |
| `aegis-risk` server, plus session lifecycle (start with the scan, stop on `stop`, crash recovery and restart) | 0.5 day |
| Tests: a server that crashes, a tool timeout, and a malformed tool result | 0.5 day |
| Optional: agent-driven tool calling for the Attack Agent (mode 2), with fallback to mode 1 | 1 day |

**Gate 5b:** the full scan against the weak and hardened bots gives the same results over MCP as the direct version, and a killed `aegis-target` server is detected and handled without hanging the scan.

Implementation notes:

- `aegis-target` must own the Playwright session for the whole scan, otherwise logins and calibration are lost between calls. Keep one persistent client session per server.
- Use the stdio transport or localhost only. Never expose a network port.
- Tool inputs and outputs reuse the Pydantic models in `schemas/`, so the Turn Record stays the single contract.

### Module 6: Risk scoring, persistence and report (Weeks 6–7)

| Step | Time |
| --- | --- |
| Risk engine: Severity = Base Weight × Confidence, and Grade = 100 − penalties, in pure Python with unit tests (same input gives the same score) | 1.5 days |
| Persist turns and findings (with `turn_id` linking each finding to its evidence) | 1 day |
| Findings endpoint plus remediation text for LLM07 | 1 day |
| Reporting: Jinja2 template plus ReportLab PDF (summary, score, evidence prompt/response pairs, remediation, and a **"Not Tested"** section for the other categories) | 2.5 days |
| Optional: Qwen3-4B drafts the executive summary (keep the numbers deterministic) | 1 day |

**Gate 4:** the scan produces a styled PDF, and every finding's evidence matches its row in the database.

### Module 7: Integration, minimal UI and demo (Weeks 7–8)

| Step | Time |
| --- | --- |
| Minimal Electron + React app: **Target Config** (with the calibration button), **Start Scan** with live log, and a results/findings view | 4 days |
| End-to-end test runs against the weak bot, the hardened bot, and at least one real third-party chatbot you have permission to test | 2 days |
| Bug fixing, edge cases (slow responses, CAPTCHAs, changing selectors) | 2 days |
| Documentation, demo script, and a demo video as backup | 1.5 days |
| Buffer | 1.5 days |

## Final project folder structure

This layout is final from day 1 to the last day. Create every folder and file in Week 1. Files marked `(later)` are empty stubs with a docstring naming the phase that owns them, so the tree never changes.

```
aegis/
├── README.md
├── .gitignore
├── .env.example                      # engine port, Ollama URL, model names
├── .github/workflows/ci.yml          # lint + unit tests
│
├── engine/                           # Python backend (FastAPI) :8765
│   ├── main.py                       # entry point; also used as the packaged sidecar
│   ├── requirements.txt                # includes the `mcp` SDK
│   ├── requirements-dev.txt
│   ├── pytest.ini
│   ├── alembic.ini
│   ├── migrations/versions/          # schema migrations
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── router.py             # mounts all routes
│   │   │   ├── health.py             # engine + Ollama readiness check
│   │   │   ├── targets.py            # register, calibrate
│   │   │   ├── scans.py              # start / status / stop
│   │   │   ├── findings.py           # findings + evidence
│   │   │   ├── reports.py            # report.pdf
│   │   │   ├── proxy.py              # (later) proxy + cert install/cleanup
│   │   │   └── websocket.py          # live telemetry
│   │   ├── core/
│   │   │   ├── config.py             # settings
│   │   │   ├── paths.py              # user-data dirs (%APPDATA%\Aegis)
│   │   │   ├── database.py           # SQLAlchemy session lifecycle
│   │   │   ├── events.py             # in-process event bus feeding the WebSocket
│   │   │   ├── logging.py
│   │   │   └── errors.py             # typed errors (ConnectorTimeout, JudgeJSONError...)
│   │   ├── models/
│   │   │   └── entities.py           # targets, scans, scan_turns, findings, reports
│   │   ├── schemas/                  # Pydantic contracts
│   │   │   ├── turn_record.py        # Unified Turn Record
│   │   │   ├── verdict.py            # judge verdict JSON
│   │   │   ├── target.py
│   │   │   ├── scan.py
│   │   │   └── finding.py
│   │   ├── adapters/                 # connectors
│   │   │   ├── base.py               # connector interface
│   │   │   ├── registry.py           # target_type -> adapter
│   │   │   ├── playwright_web.py     # website connector
│   │   │   ├── web_calibration.py    # visible-browser selector capture
│   │   │   ├── proxy_app.py          # (later) mitmproxy Track A
│   │   │   ├── uia_app.py            # (later) pywinauto Track B
│   │   │   └── cert_manager.py       # (later) root CA install/cleanup
│   │   ├── agents/
│   │   │   ├── orchestrator.py       # deterministic state machine
│   │   │   ├── state.py              # scan states, budgets, transitions
│   │   │   ├── attack_agent.py       # seed selection + mutation
│   │   │   ├── evaluation/
│   │   │   │   ├── deterministic.py  # canary / n-gram overlap
│   │   │   │   ├── triage.py         # Llama-Guard-3-1B
│   │   │   │   ├── judge.py          # Qwen3-4B rubric judge
│   │   │   │   └── evaluator.py      # combines the three, returns the verdict
│   │   │   ├── risk_scorer.py        # pure Python, no LLM
│   │   │   ├── reporting_agent.py    # executive summary + narratives
│   │   │   └── prompts/              # system prompts as files, not inline strings
│   │   │       ├── attack_system.md
│   │   │       ├── judge_rubric_llm07.md
│   │   │       └── report_summary.md
│   │   ├── llm/
│   │   │   ├── ollama_client.py      # one wrapper for all model calls
│   │   │   └── json_guard.py         # parse-and-retry for strict JSON
│   │   ├── rag/
│   │   │   ├── embedder.py           # nomic-embed-text-v1.5
│   │   │   ├── vector_store.py       # ChromaDB/FAISS
│   │   │   ├── indexer.py            # KB files -> embeddings
│   │   │   └── retriever.py          # attack path vs evaluation path
│   │   ├── kb/                       # data only, versioned
│   │   │   ├── loader.py
│   │   │   ├── 01_OWASP/2025/        # LLM01.json ... LLM10.json
│   │   │   ├── 02_ATTACK_TECHNIQUES/
│   │   │   ├── 03_PROMPT_LIBRARY/{fixed,templates,mutations}/
│   │   │   ├── 04_TEST_CASES/
│   │   │   ├── 05_EVALUATION_RULES/
│   │   │   ├── 06_RISK_RULES/
│   │   │   └── 07_REFERENCES/
│   │   ├── mcp/                      # MCP tool layer
│   │   │   ├── client.py             # session manager + call helper (one session per server)
│   │   │   ├── tool_schemas.py       # shared input/output models (reuses schemas/)
│   │   │   └── servers/
│   │   │       ├── target_server.py  # aegis-target: wraps adapters/
│   │   │       ├── kb_server.py      # aegis-kb: wraps rag/ and kb/
│   │   │       ├── eval_server.py    # aegis-eval: wraps evaluation/deterministic.py
│   │   │       └── risk_server.py    # aegis-risk: wraps risk_scorer.py
│   │   ├── services/                 # business logic between API and agents
│   │   │   ├── target_service.py
│   │   │   ├── scan_service.py       # starts/stops orchestrator runs
│   │   │   └── report_service.py     # ReportLab compilation
│   │   └── templates/
│   │       ├── report.html
│   │       └── assets/               # logo, fonts, CSS for the PDF
│   └── tests/
│       ├── unit/                     # risk scorer, json_guard, deterministic detector
│       ├── integration/              # connector vs test-targets, full scan
│       ├── benchmarks/               # 50 labelled judge pairs + runner
│       └── fixtures/
│
├── desktop/                          # Electron + React + TypeScript
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── electron-builder.yml          # (later) packaging config
│   ├── electron/                     # main process
│   │   ├── main.ts                   # window lifecycle
│   │   ├── preload.ts                # safe bridge to the renderer
│   │   └── engine-manager.ts         # spawns/monitors the Python engine
│   └── src/                          # renderer
│       ├── main.tsx
│       ├── App.tsx
│       ├── views/
│       │   ├── Dashboard.tsx
│       │   ├── TargetConfig.tsx
│       │   ├── LiveTelemetry.tsx
│       │   ├── FindingsInspector.tsx
│       │   └── ReportViewer.tsx
│       ├── components/               # severity badge, log stream, evidence pair...
│       ├── hooks/                    # useScanSocket, useScanStatus
│       ├── store/                    # app state
│       ├── api/                      # typed client for localhost:8765
│       └── types/                    # mirrors engine schemas
│
├── installer/                        # (later) AegisSetup.exe build
│   ├── build.ps1                     # PyInstaller engine + electron-builder
│   └── assets/
│
├── test-targets/                     # intentionally vulnerable chatbots
│   ├── weak-bot/                     # leaks easily, canary in system prompt
│   ├── hardened-bot/                 # resists all attempts
│   └── README.md
│
├── website/                          # (later) Next.js product site
│
├── scripts/
│   ├── setup_models.ps1              # pulls Qwen3-4B, Llama-Guard, nomic
│   ├── build_kb_index.py             # rebuild the vector store
│   └── run_benchmark.py              # judge accuracy against the labelled set
│
└── docs/
    ├── architecture/                 # the architecture PDF
    ├── api.md
    ├── user-guide.md
    └── demo/
```

### Changes from the original structure, and why

1. **Database and runtime data live outside the repo.** `engine/database/aegis_local.db` breaks once installed, because `Program Files` is not writable. `core/paths.py` points to `%APPDATA%\Aegis\`, which holds the SQLite DB, the Chroma store, reports, browser profiles (saved logins) and logs.
2. **Reporting Agent added.** The architecture has one, but the original folder had only a `reports.py` route. Now there is `reporting_agent.py` and `services/report_service.py`.
3. **Evaluation split into a package.** Triage, the LLM judge and the deterministic canary check are separate, testable files. `evaluator.py` is the only thing the orchestrator calls.
4. **New `schemas/` folder.** The Turn Record, the verdict and the API payloads are Pydantic models, which avoids circular imports.
5. **New `llm/` and `rag/` packages.** Ollama calls and retrieval code are not scattered across agents. `json_guard.py` is where the Gate 2 requirement (100% valid JSON) lives.
6. **New `services/` layer.** API routes stay thin, and scan start/stop logic lives in one place.
7. **Agent prompts as files** (`agents/prompts/`). Tuning the judge rubric means editing a `.md` file, not a Python string.
8. **Application Scanner split in two.** `proxy_app.py` (mitmproxy), `uia_app.py` (pywinauto) and `cert_manager.py` are separate stubs, since they are different tracks with different dependencies.
9. **Electron main process added.** `main.ts`, `preload.ts` and `engine-manager.ts` launch and monitor the Python engine, plus `components/`, `hooks/` and `store/` for the renderer.
10. **KB versioned by folder** (`01_OWASP/2025/`), matching the architecture's §8.4 rule. A new OWASP edition becomes a sibling folder.
11. **Alembic migrations**, because the schema will evolve after day 1.
12. **`tests/`, `scripts/`, `.env.example` and CI**, because Gates 2 and 4 are test-driven.
13. **`installer/`** is separate from `desktop/`, since packaging bundles the Python engine as well as Electron.
14. **New `mcp/` package.** The MCP servers are thin wrappers, so `adapters/`, `rag/`, `evaluation/deterministic.py` and `risk_scorer.py` remain the real implementations and nothing else is reorganized. The package exists from day 1 as stubs and is filled in during Module 5b.

### Decisions to settle early so the tree stays final

- **Config format.** `.env` for development only. User settings live in `%APPDATA%`.
- **Model names** live in `config.py`, never inline, so swapping Qwen3-4B for another model touches no other file.
- **One schema source of truth.** Pydantic in `engine/app/schemas/`, with `desktop/src/types/` mirroring it. If drift becomes a problem, generate the TypeScript types from the engine's OpenAPI spec.

## Risks and how to handle them

- **Hardware.** Qwen3-4B plus Llama-Guard plus the embedder need enough VRAM and RAM. Benchmark in Week 1, and if it's too tight, run Llama-Guard on CPU as the architecture doc already suggests.
- **Calibration on messy real sites.** Iframes, shadow DOM and custom widgets will cause trouble. Don't try to support everything. Document what works and what doesn't.
- **Small-model reliability.** A 4B model can produce weak mutations and inconsistent judging. This is why the benchmark and the deterministic canary check matter.
- **Target responses are untrusted data.** A chatbot's reply flows into the Attack Agent's context for the next mutation, so the target could try to inject instructions into your own attacker model. Pass responses as quoted data, never as instructions, and keep the tools available to the model narrow so an injected reply cannot cause harm.
- **Extra process boundary.** MCP servers are separate processes, so crashes, timeouts and orphaned browsers must be handled. Gate 5b covers this.
- **Small-model tool calling is unreliable.** This is why orchestrator-driven mode is the default and agent-driven mode is optional.
- **Only scan systems you own or have written permission to test.** Put a consent screen in the config step.

## What to cut if you fall behind

In order:

1. Agent-driven tool calling for the Attack Agent (keep orchestrator-driven MCP).
2. The LLM-written executive summary.
3. The `aegis-eval` and `aegis-risk` MCP servers (call those modules directly; keep only `aegis-target` and `aegis-kb` on MCP).
4. The WebSocket live stream (poll `status` instead).
5. The Electron polish (keep only the config screen and use the PDF as the results view).
6. The multi-turn mutation.

## Not in scope for this 40%

The Application Scanner (mitmproxy, pywinauto), the other 9 categories, packaging as `AegisSetup.exe`, and the website with Firebase auth. Also optional and out of scope: exposing Aegis itself as an MCP server (`start_scan`, `get_findings`, `get_report`) so clients like Claude Desktop can launch scans. It is a small addition and a good demo, if time remains.
