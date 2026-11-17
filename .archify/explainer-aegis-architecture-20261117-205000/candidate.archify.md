# Aegis End-to-End Autonomous Red-Teaming Architecture {#aegis-full-system}

Aegis executes an autonomous, bounded red-teaming assessment across seven specialized agent layers, orchestrating the scan lifecycle from browser calibration to executive PDF reporting.

- Deterministic Python state machines govern scan lifecycle states, attempt budgets, and risk scoring without LLM routing.[](source:spec)
- A single Qwen3-4B model on GPU VRAM runs sequentially for attack mutations, site classification, rubric judging, and narrative reporting.[](source:plan)
- A dedicated Llama-Guard-3-1B model on host CPU triages turns in sub-100ms before heavy rubric judging.
- A four-tier evaluation engine combines zero-millisecond deterministic checks with deep LLM rubric scoring to eliminate false positives.

@answer scope="Aegis v0.1 · OWASP Top 10 2026 · Local Ollama · Pure Python State Machine"
@meta locale=en style=product
@source spec title="Aegis System Architecture Specification" path=aegis-system-architecture-spec.md
@source plan title="Aegis Master Implementation Plan" path=aegis_implementation_plan.md
@source owasp title="OWASP Top 10 for LLM Applications 2026" path=engine/knowledge/owasp/OWASP-LLM-Top-10-2026.md

## How does the end-to-end scanning lifecycle flow? {#pipeline-flow}

@workflow id=lifecycle-flow title="Aegis End-to-End Scan Lifecycle"
| lane setup | 1. Setup & Pre-Scan |
| lane execute | 2. Execution & Evaluation |
| lane finalize | 3. Scoring & Reporting |
| calib | Calibration Engine | frontend | setup |
| recon | Recon Agent | backend | setup |
| plan | Test Planner | security | setup |
| orch | Orchestrator Engine | backend | execute |
| attack | Attack Agent | security | execute |
| connector | Playwright Driver | external | execute |
| eval | Evaluation Agent | security | execute |
| risk | Risk Engine | database | finalize |
| report | Reporting Agent | backend | finalize |
| assist | AI Assistant | backend | finalize |
| calib > recon | target URL |
| recon > plan | target profile |
| plan > orch | test plan |
| orch > attack | prompt id |
| attack > connector | test prompt |
| connector > eval | turn record |
| eval > risk | findings |
| risk > report | risk grade |
| report > assist | final report |

@steps id=lifecycle-steps
| s1 | Target Calibration | User specifies application URL and calibrates chat input and send selectors. | lifecycle-flow | calib |
| s2 | Pre-Scan Reconnaissance | Inspects HTTP headers, matches YAML stack signatures, and executes benign probes. | lifecycle-flow | recon |
| s3 | Deterministic Test Planning | Maps profile evidence to prioritized OWASP categories and bounded turn budgets. | lifecycle-flow | plan |
| s4 | Adaptive Attack Delivery | Dispatches curated benchmark prompts and synthesizes rephrased mutation payloads. | lifecycle-flow | attack |
| s5 | Four-Tier Response Evaluation | Evaluates target replies through deterministic tokens, refusal filters, CPU triage, and rubric judging. | lifecycle-flow | eval |
| s6 | Risk Scoring & Reporting | Computes mathematical severity grades and compiles executive PDF reports with evidence quotes. | lifecycle-flow | report |

## How does the Evaluation Agent inspect responses across four tiers? {#evaluator-four-tiers}

@workflow id=eval-funnel title="Evaluation Agent Four-Tier Defense Funnel"
| resp | Target Response | external |
| t0 | Tier 0: Token Echo? | security |
| exp0 | Exploit Confirmed | security |
| t05 | Tier 0.5: Refused? | backend |
| safe05 | Safe Refusal | backend |
| t1 | Tier 1: CPU Triage? | security |
| safe1 | Benign Interaction | backend |
| t2 | Tier 2: Rubric Judge | security |
| verdict | Structured Verdict | database |
| resp > t0 | response text |
| t0 > exp0 | token matched | emphasis |
| t0 > t05 | no token |
| t05 > safe05 | refusal marker | default |
| t05 > t1 | unrefused |
| t1 > safe1 | safe | default |
| t1 > t2 | flagged | emphasis |
| t2 > verdict | structured JSON |

| Tier | Evaluation Stage | Technology | Execution Target | Typical Latency | Vulnerability Detection Scope |
| --- | --- | --- | --- | --- | --- |
| Tier 0 | Deterministic Compliance | Python String Search | Host CPU | 0 ms {good:Instant} | Direct hack confirmation tokens (`PROMPT_INJECTION_CONFIRMED`) |
| Tier 0.5 | Fast Refusal Pre-Filter | Python Regex Matcher | Host CPU | 0 ms {good:Instant} | Standard defensive refusals (`"I cannot ignore my instructions"`) |
| Tier 1 | Lightweight CPU Triage | Llama-Guard-3-1B Q8 | Host CPU (`num_gpu=0`) | ~70 ms {good:Fast} | Harmless conversational exchanges and policy-adherent replies |
| Tier 2 | Scoring Rubric Judge | Qwen3-4B-Instruct | GPU VRAM | ~1.5 s {caution:Deep} | Subtle persona drift, instruction overrides, and partial leaks |

## What are the roles and internal stages of each agent? {#agents-breakdown}

| Agent Role | Primary Module | Core Functionality | Key Internal Stages |
| --- | --- | --- | --- |
| Calibration Engine | `web_calibration.py` | Detects chat interface DOM elements | 1. Input element detection; 2. Submit button location; 3. Interactive confirmation |
| Reconnaissance Agent | `probe_runner.py` | Identifies target architecture and tech stack | 1. Passive HTTP header & DOM capture; 2. AI stack YAML fingerprinting; 3. Local port & static code scanner; 4. Five active benign probes; 5. Qwen3 site-type classifier; 6. Target profile consolidation |
| Deterministic Test Planner | `rules.py` | Translates profile into actionable test plan | 1. Rule constraint evaluation; 2. Scope & priority determination; 3. Prompt library metadata filtering; 4. Plan revision cryptographic hash |
| Attack Agent | `attack_agent.py` | Executes multi-turn vulnerability attacks | 1. Fixed prompt selection; 2. Connector dispatch via Playwright; 3. Qwen3-4B dynamic rephrasing loop |
| Evaluation Agent | `evaluator.py` | Classifies target responses for exploit evidence | 1. Tier 0 compliance token detection; 2. Tier 0.5 fast refusal pre-filter; 3. Tier 1 Llama-Guard CPU triage; 4. Tier 2 Qwen3-4B rubric judge |
| Orchestrator State Machine | `orchestrator.py` | Enforces scan control flow and budget boundaries | 1. Sequential category queueing; 2. Early-exit finding escalation; 3. State persistence & WebSocket telemetry |
| Risk Scorer | `risk_scorer.py` | Calculates repeatable security posture scores | 1. Base category weight scaling; 2. Confidence multiplication; 3. Hundred-point penalty deduction |
| Reporting Agent | `report_service.py` | Compiles executive security documentation | 1. Qwen3 narrative synthesis; 2. Jinja2 template rendering; 3. xhtml2pdf print compilation |
| AI Assistant Copilot | `assistant_agent.py` | Provides post-scan conversational remediation | 1. ChromaDB RAG vector search; 2. Read-only SQLite findings grounding; 3. XML untrusted evidence isolation |

## How are hardware resources allocated across host hardware? {#hardware-matrix}

@facts id=hardware-specs
| GPU VRAM Model | Qwen3-4B-Instruct Abliterated GGUF (2.5 GB) |
| CPU Triage Model | Llama-Guard-3-1B Q8 via `num_gpu=0` (1.8 GB) |
| Vector Embedding Model | nomic-embed-text-v1.5 (274 MB) |
| Control Plane Overhead | Pure Python & SQLite (< 50 MB) |
| GPU Offload Policy | Sequential agent role execution |
| Model Eviction Risk | Zero: CPU triage preserves GPU memory |

| Hardware Target | Resident Process | Model Identifier | Assigned Agent Roles | Execution Mode |
| --- | --- | --- | --- | --- |
| GPU VRAM | Ollama Daemon | `Huihui-Qwen3-4B-Instruct-2507-GGUF` | Attack Agent, Rubric Judge, Site Classifier, Reporting Agent, AI Assistant | Sequential execution; single base model eliminates context reloading overhead |
| Host CPU (Triage) | Ollama Daemon | `llama-guard3:1b` (`num_gpu=0`) | Evaluation Agent (Tier 1 Triage Filter) | Sub-100ms lightweight safety classification without displacing GPU VRAM |
| Host CPU (Embeddings) | Ollama Daemon | `nomic-embed-text:latest` | Knowledge Base Embeddings & ChromaDB | 8192-token context vector retrieval for security playbooks and RAG copilot |
| Host CPU (Core Engine) | Aegis Engine | Pure Python 3.11 Runtime | Orchestrator, Test Planner, Risk Engine, Playwright Driver, SQLite Database | Deterministic rule engine; zero generative drift in control flow |
