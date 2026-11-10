# Aegis Folder Structure

This reference compares the repository layout with `Aegis_8-Week_Plan_with_MCP.md`. The project supports multiple core OWASP GenAI Top 10 2026 categories: LLM01 (Prompt Injection), LLM03 (Excessive Agency), LLM07 (Misinformation / Direct Disclosure), LLM08 (Vector and RAG Weaknesses / Hidden Context Exposure), and LLM10 (Improper Output Handling). The main project areas are present as a broad scaffold; file presence does not prove feature completion or acceptance-gate passage.

## Assessment

| Area | Assessment |
|---|---|
| Python engine, APIs, schemas, adapters, agents, KB, RAG, MCP, tests | Implemented with multi-category scanning support (LLM01, LLM03, LLM07, LLM08, LLM10), persisted findings, and PDF services. Historical test/gate evidence and pending integration limits are recorded in [Status.md](Status.md). |
| Electron/React desktop shell | Shell, Overview, four-step assessment wizard, dynamic Live Scan, and Results Inspector are implemented. Milestone 5 visual approval and full desktop-to-engine acceptance remain pending. |
| Weak and hardened targets | Present and use synthetic system prompts/canaries for disclosure and injection checks. |
| Database migrations | Alembic scaffolding exists; migration versions remain to be added. Auto-migration handles dynamic schema extensions safely. |
| Proxy/UI application-scanning tracks | Broader architecture tracks; outside this eight-week delivery. |
| Additional services, templates, installer, website, and docs | Support or future-facing additions; they do not conflict with the plan. |

The scan scope strictly excludes harmful jailbreaks (DAN, illegal acts, toxic content, hate speech), focusing exclusively on security vulnerabilities: prompt injection, system prompt extraction, excessive tool authorization, RAG data leakage, and unsafe output encoding.

## Current structure notes

The repository tree follows the plan's main structure. Active LLM assets include:
- `engine/app/agents/prompts/judge_rubric_llm08.md`: Rubric for evaluating context leakage.
- `engine/app/kb/01_OWASP/2026/`: Canonical OWASP GenAI Top 10 2026 categories (LLM01-LLM10).
- `engine/app/kb/02_ATTACK_TECHNIQUES/`: Attack technique definitions (`llm01_prompt_injection.json`, `llm03_excessive_agency.json`, `llm07_direct_disclosure.json`, `llm08_vector_rag_leakage.json`, `llm10_improper_output.json`).
- `engine/app/kb/03_PROMPT_LIBRARY/fixed/`: Seed prompts tagged with requirements metadata for LLM01, LLM03, LLM07, LLM08, and LLM10.
- `engine/app/kb/03_PROMPT_LIBRARY/templates/`: Parametric attack templates (`llm07_disclosure_request.json`, `llm08_context_saturation.json`).
- `engine/app/kb/04_TEST_CASES/test_cases.json`: Enlisted test cases for all supported categories (LLM01, LLM03, LLM07, LLM08, LLM10).
- `engine/app/kb/05_EVALUATION_RULES/`: Evaluation rules (`llm01_rules.json`, `llm03_rules.json`, `llm07_rules.json`, `llm08_rules.json`, `llm10_rules.json`).
- `engine/app/kb/loader.py`: Knowledge base loader with category-filtered lookup methods.

Pre-scan reconnaissance and test planning components:
- `engine/app/recon/`: Multi-tier reconnaissance engine (`fingerprint.py`, `network_collector.py`, `probe_runner.py`, `classifier.py`, `local_discovery.py`, `static_scanner.py`, `profile_builder.py`, `signatures/ai_stack.yaml`).
- `engine/app/agents/planner/`: Deterministic test planner (`rules.py`, `prompt_filter.py`).
- `engine/app/schemas/target_profile.py`: `FieldEvidence` and `TargetProfile` schemas.
- `engine/app/schemas/test_plan.py`: `CategoryPlan` and `TestPlan` schemas.
- `engine/app/services/recon_service.py`: Target profiling orchestration and persistence.

Multi-category vulnerability scan engine & desktop views (2026-11-10):
- `engine/app/agents/attack_agent.py`: Multi-category attack generation with dynamic prompt loading.
- `engine/app/agents/orchestrator.py`: Dynamic category scanning lifecycle orchestration.
- `engine/app/services/scan_service.py`: Scan lifecycle management supporting LLM01, LLM03, LLM07, LLM08, and LLM10.
- `desktop/src/components/NewAssessment.tsx`: Test Scope selector enlisting supported OWASP categories.
- `desktop/src/App.tsx`: Dynamic Live Scan monitoring with category-aware telemetry and progress indicator.
- `desktop/src/views/FindingsInspector.tsx`: Dynamic category-aware findings, metrics, and evidence presentation.

Keep generated caches and runtime data outside source control. Keep Pydantic schemas and desktop TypeScript types aligned, and add Alembic revisions when persistent schemas change.

Baseline security tooling and evaluation components (2026-11-07):
- `engine/app/agents/mutators.py`: Deterministic Buff Mutation Engine (`Base64Mutator`, `ROT13Mutator`, `CharCodeMutator`, `DelimiterMutator`).
- `engine/app/core/cost_estimator.py`: Token consumption and financial cost calculation matrix.
- `engine/app/kb/03_PROMPT_LIBRARY/templates/llm08_context_saturation.json`: Many-shot conversational padding templates.
- `engine/app/kb/03_PROMPT_LIBRARY/variations/prompt_variations.json`: Formal registry of non-jailbreak prompt injection variations.
- `docs/baseline_tools_and_prompts_analysis.md`: Master reference catalog reverse-engineering Garak and Agentic Security.
