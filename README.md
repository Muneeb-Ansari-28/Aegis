# Aegis - Automated Red-Teaming & Security Assessment for LLMs

Aegis is an automated red-teaming and security assessment workbench for LLMs and LLM-powered applications. It enables security teams and developers to calibrate against web-based AI targets, discover attack surfaces via multi-tier reconnaissance, and run bounded vulnerability assessments.

## OWASP Top 10 for LLM Applications (2026) Taxonomy
Aegis aligns with the canonical **OWASP Top 10 for LLM Applications (2026)** framework:
- **LLM01**: Prompt Injection
- **LLM02**: Sensitive Information Disclosure
- **LLM03**: Excessive Agency
- **LLM04**: Supply Chain
- **LLM05**: Data and Model Poisoning
- **LLM06**: Unbounded Consumption
- **LLM07**: Misinformation
- **LLM08**: Hidden Context Exposure *(Active Execution Pipeline)*
- **LLM09**: Vector and Embedding Weaknesses
- **LLM10**: Improper Output Handling

### Current Assessment Scope & Multi-Category Readiness
- **Implemented Pipeline**: **LLM08 Hidden Context Exposure** uses planner-approved direct disclosure prompts, canary and prompt-overlap checks, refusal filtering, and a rubric-based judge. Prompt IDs and categories are constrained to the current plan.
- **Profile-Guided Multi-Category Workflow**: Passive profiling begins when the URL is submitted. The user's explicit authorization is required before active benign probes run after calibration, and Tier 3 static inspection runs only for a project path supplied for that recon run. The deterministic planner returns applicability, implementation status, and selectable scope for all 10 OWASP 2026 categories.
- **Scope Transparency**: Applicable under-development categories are shown as disabled with reasons; unknown and not-applicable categories are available under "Show all 10 categories". "Run all ready categories" selects every backend-verified executable category (currently `LLM08`). Each selected category receives its own attempt budget and outcome.
- **Authorization**: Scans must only be conducted against authorized local or private-network targets with explicit written permission.

## Architecture
- **Control Plane & Backend Engine (`engine/`)**: FastAPI application on `http://127.0.0.1:8765` implementing state machines, SQLite persistence, Playwright browser connectors, Ollama LLM integration, and ChromaDB vector store.
- **Desktop Client (`desktop/`)**: Fast, responsive React + TypeScript workspace built with Vite (`http://localhost:5173`), featuring live scan telemetry, step-by-step target calibration, and interactive findings inspection.
- **Scaffolded Modules**: Electron desktop packaging (`desktop/electron/`) and MCP tool servers (`engine/app/mcp/`) are scaffolded for future enterprise packaging.

## Quick Start
1. **Pull Models**:
   ```powershell
   .\scripts\setup_models.ps1
   ```
2. **Start Backend Engine**:
   ```powershell
   cd engine
   ..\.venv\Scripts\python main.py
   ```
3. **Start Desktop Workspace**:
   ```powershell
   cd desktop
   npm install
   npm run dev
   ```
4. Access Aegis at `http://localhost:5173` in your browser.
