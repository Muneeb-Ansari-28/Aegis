# Aegis System Architecture

This guide summarizes the system boundaries, agent contracts, and execution pipelines for the Aegis project per the master specification and implementation plan.

## Active scope

Aegis assesses LLM applications against the canonical OWASP GenAI/LLM Top 10 (2026) taxonomy with priority scanning on OWASP LLM08 Hidden Context Exposure, LLM01 Prompt Injection, LLM03 Excessive Agency, LLM10 Improper Output Handling, LLM07, and LLM02. The local weak and hardened chatbots use a fake system prompt with the `AEGIS-CANARY-7731` canary. Deterministic canary and n-gram overlap checks are combined with triage and rubric judging.

Jailbreaks, role impersonation, instruction overrides, encoding or obfuscation, safeguard bypass, and real secret extraction are out of scope.

## Core components and contracts

- FastAPI engine with deterministic orchestrator and scan state/budget handling.
- **Recon Agent (Step 0a)**: Multi-tier target profiling (Tier 1 passive network/signatures + active benign probing; Tier 2 local port discovery; Tier 3 static project scanning).
- **Deterministic Test Planner (Step 0b)**: Pure-Python rule engine translating `TargetProfile` into a prioritized, budgeted `TestPlan` with safe fallback.
- Playwright web connector producing the Unified Turn Record.
- Attack Agent uses fixed and templated direct requests with safe wording rephrases.
- Evaluation Agent combines deterministic checks, triage, and structured rubric verdicts.
- Risk scoring stays pure Python; MCP servers expose existing module functions as tools.
- Electron/React desktop client communicates with the engine over localhost REST and WebSocket.

## Pre-Scan Reconnaissance Agent (Module 2.5 / Step 0a)

The Recon Agent (`engine/app/recon/`) profiles the target before vulnerability scanning begins. It constructs a corroborated `TargetProfile` adhering to the architectural invariant: **"Unknown is not absent"**.

1. **Tier 1 — Network & Web Profiling**:
   - **Passive Fingerprinting** (`PassiveNetworkCollector`): Inspects HTTP traffic, headers (e.g. `server`, `x-powered-by`), WebSocket frames, DOM globals, loaded scripts, well-known endpoints (`/openapi.json`), and DOM input/submit/response candidate detection.
   - **Technology Signatures** (`ai_stack.yaml` & `SignatureMatcher`): Versioned regex and header rules identifying OpenAI, Ollama, LangServe, Streamlit, Gradio, Chainlit, SSE, Vercel AI SDK, RAG payload keys, and session memory.
   - **Active Benign Probing** (`ProbeRunner`): Dispatches 5–8 non-hostile inquiry prompts (scope, RAG citation probe, memory recall with token `AegisCyan42`, output rendering, tool invocation query). All probe interactions are recorded as `scan_turns` with `category="RECON"`.
   - **Site Type Classification** (`SiteTypeClassifier`): Structured fuzzy classifier backed by local Ollama (`llama3.2` / `qwen3:4b`) using `JSONGuard` with deterministic keyword fallback.
2. **Tier 2 — Localhost Discovery** (`LocalDiscovery`):
   - Scans common AI and application development ports (`3000, 5173, 8000, 8501, 7860, 11434, 1234, 8001, 8002`) using `psutil` to map running processes, command lines, and active servers.
3. **Tier 3 — Static Code Inspection** (`StaticProjectScanner`):
   - When a project directory is provided, inspects dependency manifests (`requirements.txt`, `pyproject.toml`, `package.json`, `docker-compose.yml`), Python AST imports (e.g., `langchain`, `llama_index`, `chromadb`), and environment variable keys (`.env` privacy guard: strictly reads variable names, **never** variable values).
4. **Profile Corroboration** (`ProfileBuilder`):
   - Corroborates evidence across tiers, assigns confidence levels (`HIGH`, `MEDIUM`, `LOW`, `UNKNOWN`), and persists to the `target_profiles` database table via `ReconService`.

## Deterministic Test Planner (Module 2.5 / Step 0b)

The Test Planner (`engine/app/agents/planner/`) determines the execution plan for the active scan based on the corroborated `TargetProfile`.

1. **Pure-Python Rule Engine** (`rules.py`):
   - Zero LLM involvement in test planning logic.
   - Generates a prioritized list of OWASP categories with per-category turn budgets ($N \le 10$):
     - `LLM08` (Hidden Context / RAG Leakage): prioritized when RAG or vector DBs are detected.
     - `LLM01` (Prompt Injection): prioritized when custom system instructions or delimiters are detected.
     - `LLM03` (Excessive Agency): prioritized when agentic tool calling or API integrations are detected.
     - `LLM10` (Improper Output Handling): prioritized when markdown, HTML, code execution, or JSON rendering is detected.
     - Fallback: Defaults to safe baseline execution (`LLM08`, `LLM01`) when characteristics are unknown.
2. **Dynamic Prompt Filtering** (`prompt_filter.py`):
   - Evaluates prompt library metadata (`requires` and `applicable_when`) against the target profile to select prompts tailored to the target's verified capabilities.

## Website Scanning Module & Playwright Connector (Module 2)

The Playwright web connector (`engine/app/adapters/playwright_web.py`) bridges the deterministic orchestrator to web chatbot targets:
1. **Interface Detection:**
   - Heuristically detects input boxes (`textarea`, `input[type="text"]`, `[contenteditable]`), submit controls (`button#send`, `button[type="submit"]`, or `Enter` key fallback), and assistant response bubbles (`.chat-message.assistant`, `[data-message-author-role="assistant"]`, `#chat-box > *:last-child`).
   - Saved `TargetCalibrationConfig` selectors remain authoritative. Before submission, calibration and scanning share a bounded readiness check that opens a supported launcher only when necessary and verifies a visible, editable, actionable input.
   - Headed Chromium contexts follow the native window (`no_viewport=True`); non-persistent headless contexts retain the deterministic 1280x800 viewport. No machine-specific resolution or display scaling is configured.
2. **Prompt Dispatch & Submission:**
   - Clears, focuses, and fills the prompt into the target input locator.
   - Dispatches submission by clicking the submit button or issuing a synthetic `Enter` keypress on the input.
3. **Streaming-Aware Stabilization:**
   - Snapshots baseline response content before dispatch.
   - Periodically polls the assistant reply container (every 200ms) until text content ceases mutating across a stability threshold (e.g. 800ms), ensuring complete token-stream capture.
4. **Unified Turn Record Normalization:**
   - Formats every interaction into the canonical `TurnRecord` schema, tracking `turn_id`, `scan_id`, `turn_index`, `prompt`, `response`, `latency_ms`, `status` (`success`, `timeout`, `error`), and DOM metadata.
   - Only successful turns enter vulnerability evaluation. A connector error/timeout is persisted with diagnostic text and a null verdict, emitted as a failed turn, and terminates the scan as `FAILED`. No database migration is required. Replay exposes connector status and suppresses old verdicts attached to known connector-error markers without rewriting historical rows.
5. **DOM Calibration Flow (`web_calibration.py`):**
   - **Automated Calibration:** Detects input, Send, and response elements after opening the chatbot as necessary. The API uses a visible browser; headless calibration remains supported.
   - **Interactive Calibration:** Visible browser session injecting `CALIBRATION_OVERLAY_SCRIPT`, enabling user click-to-capture on input and Send. The response selector is detected automatically. The user still controls opening the chatbot during interactive capture. Both modes retain the existing saved selector format.

The complete planned folder layout and module gates are in the eight-week plan. Broader application scanning and packaging tracks are later work.


## Results, findings, and reporting data flow

`desktop/src/App.tsx` uses local view selection, not a URL router. Dashboard and History actions set the selected scan ID and open `desktop/src/views/FindingsInspector.tsx`. History discovery remains browser-local (up to 100 entries); backend persistence does not currently supply an engine-wide history list to this UI. `ReportViewer.tsx` is a delegating wrapper, not the active Results route.

The orchestrator persists turns/verdicts and linked findings in `ScanTurnEntity` / `FindingEntity`. Backend `RiskScorer` supplies severity. `FindingsService` reads these records and exposes list/detail/summary models from `schemas/finding.py`. `ScanService` exposes persisted turn replay, including connector status and nullable verdicts. The Inspector loads summary, findings, and turns through the existing API client on selection or manual refresh; it does not continuously poll Results. A request-version guard rejects stale aggregate loads. The timeline is a presentation of persisted turns, not a complete lifecycle event log.

PDF download uses `GET /reports/{scan_id}/pdf`: an existing file is reused, otherwise `ReportService` compiles database records through `ReportingAgent`, Jinja2 and xhtml2pdf and stores the PDF under the application-data reports directory. Metadata and explicit regeneration endpoints also exist; the current UI does not expose regeneration or report preview. See [API reference](../docs/api.md) for contracts and [Status.md](Status.md) for verification limits. These backend capabilities predate Milestone 5; no backend contracts changed in the redesign.


## High-Speed Deterministic Evaluator & Refusal Engine (Module 4)

The evaluation pipeline combines deterministic offline pattern matching with an LLM rubric judge:
1. **Deterministic Pre-Filtering (`engine/app/agents/evaluation/deterministic.py`)**:
   - **Canary Check**: Flags planted validation canaries (`AEGIS-CANARY-7731`) at 100% confidence.
   - **High-Value Secret Detection (OWASP LLM02)**: Evaluates Dora regex signatures for AWS access/secret keys, GitHub PATs, Slack tokens, Stripe live keys, and OpenAI API keys.
   - **Container & Sandbox Escape Heuristics (OWASP LLM10 / LLM03)**: Detects container breakout probing (Docker socket `/var/run/docker.sock`, Kubernetes service tokens, Linux capabilities `/proc/self/status`, and mount table inspection).
   - **PII & Financial Card Validation (OWASP LLM02)**: Evaluates SSNs, emails, private keys, and credit card numbers verified via the Luhn checksum algorithm (`luhn_validate`).
   - **System Prompt Overlap**: Trigram and character shingle overlap against known system prompts.
   - **Universal Refusal Pre-Filter (`REFUSAL_MARKS`)**: Evaluates 28 canonical refusal markers from `agentic_security`. If the response contains refusal indicators and no exploit signals, it returns `exploited=False` with 95% confidence, bypassing the LLM judge and saving ~70% of evaluation latency.
2. **LLM Rubric Judge (`judge.py` & `judge_rubric_llm08.md`)**:
   - Enforces the **Summarized-Result Exploitation Principle**: accurate summaries or descriptions of internal rules or tool execution outcomes count as successful exploits.

## Deterministic Buff Mutation Engine & Attack Agent (Module 3)

The attack generation layer (`engine/app/agents/mutators.py` and `attack_agent.py`) incorporates deterministic non-jailbreak prompt transformations:
1. **Buff Transformers**:
   - `Base64Mutator`: Wraps directives in Base64 encoding.
   - `ROT13Mutator`: Encodes directives via ROT13 Caesar cipher.
   - `CharCodeMutator`: Converts instructions into ASCII integer sequences.
   - `DelimiterMutator`: Encapsulates directives in Markdown fences, XML tags, or code comments.
2. **Autonomous Refusal Adaptation**:
   - When the Evaluator flags a refusal on turn $N$, `AttackAgent.generate_prompt` immediately pivots to an encoded or smuggled buff variant on turn $N+1$ without incurring LLM token costs.

## Scan Cost & Financial Telemetry Estimator

The cost module (`engine/app/core/cost_estimator.py`) models token pricing across commercial APIs (Claude, OpenAI, DeepSeek, Mistral) and local models (`ollama` = $0.00). Integrates with `ReportingAgent` to calculate prompt tokens, response tokens, and total estimated scan cost (USD) for inclusion in executive summaries and PDF reports.


## Multi-Category Assessment Pipeline & Dynamic UI Telemetry (Module 3 & 5)

The scan engine supports dynamic category routing across OWASP GenAI Top 10 2026 vulnerability classes:
1. **Dynamic Category Mapping (`AttackAgent` & `KBLoader`)**:
   - `AttackAgent(category=category)` initializes attack sequences by dynamically loading the corresponding prompt library (`kb/03_PROMPT_LIBRARY/fixed/<category_file>.json`) and template catalogues.
   - Attack vectors strictly focus on security and integrity vulnerabilities:
     - `LLM01`: Instruction overrides, translation smuggling, delimiter escaping, and prefix injection.
     - `LLM03`: Excessive agency, tool invocation probing, unauthorized tool parameter tampering.
     - `LLM07`: Misinformation generation, factual manipulation, direct constraint disclosure.
     - `LLM08`: Vector and RAG corpus leakage, context boundary extraction, embedding proximity forcing.
     - `LLM10`: Improper output handling, zero-click Markdown tracking pixels (`![tracker](uri)`), URI exfiltration.
   - Harmful content jailbreaks (DAN, illegal acts, toxic content) are strictly excluded by design.
2. **Category-Aware Orchestration & Findings Persistence (`Orchestrator` & `ScanService`)**:
   - `Orchestrator` tracks the active category, tagging each executed `TurnRecord` and transactional `ScanTurnEntity` with `category` and `attempt_in_category`.
   - Identified exploits generate `FindingEntity` records tagged to the evaluated vulnerability class with automated risk rating via `RiskScorer`.
   - `ScanStatusResponse` and `ScanTurnResponse` schemas return the active category to support seamless live monitoring and persisted replay.
3. **Dynamic Frontend Assessment Lifecycle**:
   - **Wizard Configuration**: `NewAssessment.tsx` dynamically populates the Test Scope selection with supported categories, their descriptions, and validation rules.
   - **Live Assessment Telemetry**: `App.tsx` (`LiveScanPage`) tracks the active scan category in real time via WebSockets and HTTP polling, animating the OWASP category progress list, highlighting the active module, and rendering category-tailored prompt tags and exploit detection badges.
   - **Findings Inspection & Evidence Replay**: `FindingsInspector.tsx` resolves category codes dynamically via `CATEGORY_NAMES` and summary telemetry, presenting category-specific scope definitions, test case replay, and audit timelines without hardcoded single-category assumptions.
