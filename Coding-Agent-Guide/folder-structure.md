# Aegis Folder Structure

This reference compares the repository layout with `Aegis_8-Week_Plan_with_MCP.md`. The plan's active assessment category is LLM07 System Prompt Leakage. The main project areas are present as a broad scaffold; file presence does not prove feature completion or acceptance-gate passage.

## Assessment

| Area | Assessment |
|---|---|
| Python engine, APIs, schemas, adapters, agents, KB, RAG, MCP, tests | Present; runtime behavior and plan gates remain unverified. |
| Electron/React desktop shell | Source files are present; integration remains unverified. |
| Weak and hardened targets | Present and now use a fake system prompt/canary for LLM07 checks. |
| Database migrations | Alembic scaffolding exists; migration versions remain to be added. |
| Proxy/UI application-scanning tracks | Broader architecture tracks; outside this eight-week delivery. |
| Additional services, templates, installer, website, and docs | Support or future-facing additions; they do not conflict with the plan. |

The scan scope uses direct, plain-language disclosure requests. Jailbreaks, role impersonation, overrides, obfuscation, safeguard bypass, and real secret extraction remain excluded. The team-facing [annotated folder guide PDF](../Aegis-Folder-Structure-Guide.pdf) lists current files with one-line purposes.

## Current structure notes

The repository tree follows the plan's main structure. Active LLM07 assets include `engine/app/agents/prompts/judge_rubric_llm07.md`, `engine/app/kb/02_ATTACK_TECHNIQUES/llm07_direct_disclosure.json`, `engine/app/kb/03_PROMPT_LIBRARY/fixed/llm07_direct_disclosure.json`, `engine/app/kb/03_PROMPT_LIBRARY/templates/llm07_disclosure_request.json`, and `engine/app/kb/05_EVALUATION_RULES/llm07_rules.json`.

Keep generated caches and runtime data outside source control. Keep Pydantic schemas and desktop TypeScript types aligned, and add Alembic revisions when persistent schemas change.
