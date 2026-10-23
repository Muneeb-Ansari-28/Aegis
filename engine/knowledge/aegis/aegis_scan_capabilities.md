# Aegis Scan Capabilities and Verification Status

## Current Verified Scan Execution Coverage

Aegis distinguishes between **Knowledge Coverage** (what the AI Assistant can explain) and **Scan Execution Coverage** (what the automated red-teaming engine can currently execute against a live target).

### Verified End-to-End Scan Modules
- **LLM08:2026 Hidden Context Exposure** (formerly categorized as LLM07:2025 System Prompt Leakage):
  - **Status**: Implemented and verified end-to-end.
  - **Scope**: Direct, plain-language disclosure requests seeking system prompt instructions, non-user-facing context, and canary markers.
  - **Methodology**: Evaluates target responses using deterministic canary matching, semantic overlap scoring, and an LLM judge rubric.

### Planned Modules Under Active Development
The following nine OWASP LLM Top 10 2026 vulnerability categories are currently under development in the scanner pipeline:
- **LLM01:2026 Prompt Injection** — Automated scan pipeline in development; not yet verified end-to-end.
- **LLM02:2026 Sensitive Information Disclosure** — Automated scan pipeline in development.
- **LLM03:2026 Excessive Agency** — Automated scan pipeline in development.
- **LLM04:2026 Supply Chain** — Automated scan pipeline in development.
- **LLM05:2026 Data and Model Poisoning** — Automated scan pipeline in development.
- **LLM06:2026 Unbounded Consumption** — Automated scan pipeline in development.
- **LLM07:2026 Misinformation** — Automated scan pipeline in development.
- **LLM09:2026 Vector and Embedding Weaknesses** — Automated scan pipeline in development.
- **LLM10:2026 Improper Output Handling** — Automated scan pipeline in development.

## Assistant Capability Transparency Rule

When users ask whether Aegis can scan for a category other than LLM08 (such as "Can Aegis scan for LLM01 Prompt Injection?" or "Can Aegis scan for LLM03?"):
- The assistant must state clearly and transparently that only **LLM08 Hidden Context Exposure** is currently implemented and verified for end-to-end scanning.
- The assistant must explain the vulnerability concept and mitigations from its knowledge base, but must never fabricate or imply that an automated scan execution exists for unfinished modules.
