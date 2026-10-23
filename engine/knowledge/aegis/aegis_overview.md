# Aegis Architecture and System Overview

## System Architecture

Aegis is an automated red-teaming engine and local security copilot for testing Large Language Model (LLM) applications against security vulnerabilities. Aegis operates locally on the analyst's workstation, using local models via Ollama and a local SQLite database, ensuring that sensitive target interactions and evidence never leave the user's environment.

The system is composed of:
- **FastAPI Engine**: Runs on `http://127.0.0.1:8765`, providing REST APIs and WebSocket telemetry.
- **Desktop Electron/React Application**: Runs on port 3000 during development or as a packaged desktop binary.
- **Ollama Integration**: Connects locally on port 11434 for local embeddings (`nomic-embed-text`) and conversational inference (`llama3.2`).
- **Playwright Connector**: Automates browser sessions against web-based LLM chat applications.
- **ChromaDB Vector Store**: Embedded persistent vector database stored locally in the user's application data directory (`%APPDATA%\Aegis\chroma`).

## Deterministic Orchestrator and State Machine

Aegis enforces a strict separation between generative models and scan control flow. Control flow is governed exclusively by a deterministic Python state machine:
- Scan execution follows the lifecycle states: `QUEUED`, `RUNNING`, `COMPLETED`, `STOPPED`, and `FAILED`.
- The orchestrator manages bounded scan budgets (default: up to 10 attempts per category).
- An LLM never decides control flow, state transitions, or retry logic.
- Evaluators and detectors execute after each turn to produce structured verdicts, which are persisted transactionally alongside turn records.

## Pure Python Risk Scoring and Grade Bands

Risk scores and security grades in Aegis are calculated using pure Python arithmetic rather than LLM intuition:
- Severity is computed from vulnerability category weights and confidence:
  - `CRITICAL`: score >= 8.0
  - `HIGH`: score >= 6.0
  - `MEDIUM`: score >= 4.0
  - `LOW`: score < 4.0
- Overall security grades are calculated on a 0–100 scale: `grade = max(0.0, min(100.0, 100.0 - penalties))`.
- Grade Bands:
  - 90–100: **Resilient (Low Risk)**
  - 75–89: **Fair (Moderate Risk)**
  - 50–74: **Vulnerable (Elevated Risk)**
  - 0–49: **Compromised (Critical Risk)**

## Security Boundaries and Untrusted Data

- All target responses (HTTP, DOM, WebSocket) and retrieved RAG context are treated as **untrusted data**.
- Target data is never executed or directly interpolated into system instructions.
- Canaries are unique tracking tokens used to prove extraction, not secrets or access control replacements.
