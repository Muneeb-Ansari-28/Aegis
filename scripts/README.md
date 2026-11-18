# Aegis Automation & Utility Scripts

This directory contains automation, model configuration, knowledge base ingestion, and verification scripts used across the Aegis assessment lifecycle.

---

## Table of Contents

- [Script Inventory](#script-inventory)
- [1. `setup_models.ps1` (Ollama Model Puller)](#1-setup_modelsps1-ollama-model-puller)
- [2. `ingest_kb.py` / `build_kb_index.py` (Vector Store Ingestion)](#2-ingest_kbpy--build_kb_indexpy-vector-store-ingestion)
- [3. `verify_gate4.py` (End-to-End Gate 4 Verification)](#3-verify_gate4py-end-to-end-gate-4-verification)
- [4. `run_benchmark.py` (Judge Rubric Benchmarks)](#4-run_benchmarkpy-judge-rubric-benchmarks)
- [Related Root Scripts](#related-root-scripts)

---

## Script Inventory

| Script | Type | Description |
| :--- | :--- | :--- |
| `setup_models.ps1` | PowerShell | Pulls required local models into Ollama (`qwen`, `llama-guard3`, `nomic-embed-text`) |
| `ingest_kb.py` | Python | Parses markdown knowledge base files and indexes semantic chunks into ChromaDB |
| `build_kb_index.py` | Python | Convenience wrapper calling `app.rag.indexer.index_knowledge_base` |
| `verify_gate4.py` | Python | Executes automated scan against weak-bot, asserts DB findings, generates PDF, and validates text fidelity |
| `run_benchmark.py` | Python | Benchmark harness for validating judge accuracy against labelled prompt-response pairs |

---

## 1. `setup_models.ps1` (Ollama Model Puller)

Pulls the local LLMs required by the active Aegis configuration into your Ollama instance:
```powershell
.\scripts\setup_models.ps1
```

### Models Pulled:
- **Base / Attack / Judge / Assistant Model**:
  `ollama pull hf.co/mradermacher/Huihui-Qwen3-4B-Instruct-2507-abliterated-GGUF:Q4_K_M` *(or `qwen2.5:3b` / `llama3.2:latest` depending on `.env` configuration)*
- **Fast CPU Triage Model**:
  `ollama pull llama-guard3:1b`
- **RAG Embedding Model**:
  `ollama pull nomic-embed-text:latest` *(or `nomic-embed-text:v1.5`)*

---

## 2. `ingest_kb.py` / `build_kb_index.py` (Vector Store Ingestion)

Ingests all markdown documents located in `engine/knowledge/` into the persistent ChromaDB collection at `%APPDATA%\Aegis\chroma`.

```powershell
# From repository root:
.\.venv\Scripts\python scripts\ingest_kb.py
```

### Ingestion Details:
- Chunks text into coherent blocks with 30-word overlap.
- Assigns deterministic, idempotent chunk IDs using SHA-256 hashes.
- Embeds chunks using `NomicEmbedder` with task-prefixed queries (`search_document:`).
- Persists metadata including source file, OWASP category risk ID, section name, and chunk index.

---

## 3. `verify_gate4.py` (End-to-End Gate 4 Verification)

Performs programmatic end-to-end verification of Milestone Gate 4:
1. Spawns an in-process instance of `weak-bot` on a dynamic loopback port.
2. Executes an automated scan using `Orchestrator` and `PlaywrightWebAdapter`.
3. Confirms exploit detection (`attack_success = True`) and verifies persistence in SQLite (`scan_turns`, `findings`).
4. Generates a styled executive PDF audit report using `ReportService`.
5. Uses `pypdf` to extract text from the generated PDF and asserts that ground-truth findings, canaries, and prompts match SQLite records with 100% fidelity.

```powershell
.\.venv\Scripts\python scripts\verify_gate4.py
```

---

## 4. `run_benchmark.py` (Judge Rubric Benchmarks)

Harness for evaluating LLM judge accuracy against labelled ground-truth pairs in `engine/tests/benchmarks/benchmark_pairs.json`:
```powershell
.\.venv\Scripts\python -m pytest engine/tests/benchmarks/test_judge_benchmarks.py -v
```

---

## Related Root Scripts

### `run_aegis.ps1` (All-in-One Launcher)
Located in the repository root. Validates environment dependencies, starts both the FastAPI engine (`:8765`) and Vite desktop client (`:3000`), monitors process health, opens the browser automatically, and performs graceful teardown on `Ctrl+C`:
```powershell
.\run_aegis.ps1
```

