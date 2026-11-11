# Aegis User Guide

## Assessment Scope & Guidelines

Aegis is an automated red-teaming workbench designed for authorized security assessments of LLM applications:
- **Canonical Taxonomy**: Aligns with the **OWASP Top 10 for LLM Applications (2026)** framework.
- **Active Execution Pipeline**: **LLM08 Hidden Context Exposure** is fully implemented with automated prompt injection and context disclosure attack vectors, canary token detection, refusal pre-filtering, and an LLM judge.
- **Multi-Category Test Planning**: Target profiling automatically guides test scope across all 10 categories. The assessment wizard lets you select any ready category or click "Run all ready categories" (currently `LLM08`). Under-development categories remain visible with explanatory notes.
- **Authorization Requirement**: Only assess systems you own or have explicit written permission to test. Active probes and attack vectors interact directly with target browsers and APIs.

## Getting Started

### 1. Prerequisites & Model Setup
Install Ollama and ensure local models are pulled:
```powershell
.\scripts\setup_models.ps1
```
This pulls `llama3.2:latest` (main agent model) and `nomic-embed-text:latest` (knowledge base embeddings).

To index the local security knowledge base into ChromaDB:
```powershell
cd engine
..\.venv\Scripts\python -m app.rag.indexer
```

### 2. Launch the Engine & Desktop Client
Start the FastAPI backend:
```powershell
cd engine
..\.venv\Scripts\python main.py
```
*(Runs on `http://127.0.0.1:8765`)*

In a separate terminal, launch the desktop workspace:
```powershell
cd desktop
npm run dev
```
*(Opens at `http://localhost:5173`)*

## Running an Assessment

1. **Target Configuration (Step 0)**:
   - Enter your target web application URL (e.g. `http://127.0.0.1:5173` or `http://localhost:3000`).
   - (Optional) Provide a local project folder for Tier 3 static inspection (reads package manifests and `.env` key names locally; never transmits code).
   - Check the target authorization confirmation box.

2. **Interface Calibration & Reconnaissance (Step 1)**:
   - Click **Automatic calibration** to let Playwright detect the input field, submit button, and response area, or **Manual calibration** to click the target controls in the visible browser window.
   - Passive reconnaissance and loopback inspection start after you submit the URL. The authorization you confirmed on the previous step is required before benign active probes run after calibration. Tier 3 static inspection runs only when you provide a project folder. Review each stage status and inferred capability.

3. **Test Scope & Multi-Category Selection (Step 2)**:
   - The list initially shows categories recon marked applicable; categories still under development are visible but disabled. Select ready categories or click **Run all ready categories** (currently `LLM08`).
   - Toggle **Show all 10 categories** to inspect categories whose applicability is unknown or not applicable.
   - Set the attempt budget per selected category (1 to 10 attempts).

4. **Review & Run (Step 3)**:
   - Confirm configuration and click **Run scan**.
   - Monitor live prompt submissions, model responses, and verdict evaluations on the **Live scan** page.

5. **Results & Reporting**:
   - Inspect confirmed vulnerabilities in **Results & findings**.
   - Export executive PDF audit reports with methodology, category coverage, and remediation playbooks. Partial, failed, or interrupted scans are identified as **INCONCLUSIVE**.
