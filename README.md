# Aegis - Automated Red-Teaming & Security Assessment for LLMs

Aegis is an automated security assessment engine for LLMs and LLM-powered applications. Its current eight-week assessment scope is OWASP LLM07 System Prompt Leakage, using direct plain-language disclosure requests against authorized web targets. Jailbreak methods, role impersonation, instruction overrides, obfuscation, and real secret extraction are excluded.

## Architecture Highlights
- **Deterministic Control Plane:** Python state machine controls scan budgets, retries, and state transitions.
- **MCP Tool Layer:** Target connectors, Knowledge Base, deterministic canary/overlap checks, and risk scoring are exposed through MCP tools.
- **Unified Turn Record:** Pydantic contract tracks each prompt and response.
- **Dual-Role Evaluation:** Deterministic canary detection is paired with triage and rubric-based judging.
- **Desktop Interface:** Electron + React + TypeScript client with live telemetry.

## Directory Structure
- `engine/`: FastAPI engine, orchestrator, agents, MCP servers, adapters, RAG, and KB.
- `desktop/`: Electron + React + TypeScript interface.
- `test-targets/`: Weak and hardened LLM07 test chatbots.
- `installer/`, `website/`: Future distribution and product site.
- `scripts/`: Model setup, KB indexing, and benchmark runner.
- `docs/`: User, API, architecture, and demo documentation.
