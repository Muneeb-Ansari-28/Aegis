# Aegis System Architecture

This guide summarizes the system boundaries and contracts for the current eight-week delivery. The full product architecture remains in `Aegis-Architecture.pdf`; the delivery sequence and active category are defined by `Aegis_8-Week_Plan_with_MCP.md`.

## Active scope

The initial scanner assesses OWASP LLM07 System Prompt Leakage through direct, plain-language disclosure requests against authorized targets. The local weak and hardened chatbots use a fake system prompt with the `AEGIS-CANARY-7731` canary. Deterministic canary and n-gram overlap checks are combined with triage and rubric judging.

Jailbreaks, role impersonation, instruction overrides, encoding or obfuscation, safeguard bypass, and real secret extraction are out of scope. LLM01 and the other OWASP categories remain taxonomy references or future scope, not active scan categories.

## Core components and contracts

- FastAPI engine with deterministic orchestrator and scan state/budget handling.
- Playwright web connector producing the Unified Turn Record.
- Attack Agent uses fixed and templated direct requests with safe wording rephrases.
- Evaluation Agent combines deterministic checks, triage, and structured rubric verdicts.
- Risk scoring stays pure Python; MCP servers expose existing module functions as tools.
- Electron/React desktop client communicates with the engine over localhost REST and WebSocket.

The complete planned folder layout and module gates are in the eight-week plan. Broader application scanning and packaging tracks are later work.
