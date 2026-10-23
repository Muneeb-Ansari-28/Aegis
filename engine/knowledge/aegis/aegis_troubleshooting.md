# Aegis Troubleshooting Guide

## Engine Connection Issues

- **Symptom**: Desktop UI displays "Error connecting to local Aegis Engine".
- **Resolution**:
  - Verify that the FastAPI engine is running on `http://127.0.0.1:8765`.
  - Start the engine using the root startup script `.\run_aegis.ps1` or run `python -m app.main` from within `engine/`.
  - Check `http://127.0.0.1:8765/api/v1/health` in a browser or curl to confirm healthy engine status.

## Ollama and Local Model Issues

- **Symptom**: Assistant replies "Ollama service unavailable" or timeouts occur during generation.
- **Resolution**:
  - Ensure the Ollama background daemon is running (`ollama serve` or Windows tray icon).
  - Check listening port: `http://localhost:11434`.
  - Verify installed models using `ollama list`. Required models:
    - Embedding model: `nomic-embed-text:latest`
    - Assistant & Attack model: `llama3.2:latest`
  - If a model is missing, pull it via `ollama pull nomic-embed-text:latest` or `ollama pull llama3.2:latest`.

## Playwright Browser Calibration Failures

- **Symptom**: Automatic calibration cannot find chat input or send button.
- **Resolution**:
  - Switch to **Interactive Click Calibration**:
    1. A visible browser window will open displaying the target application.
    2. Click the chat message input box.
    3. Click the Enter / Send button.
  - Ensure the target URL is accessible locally and does not require complex SSO authentication before displaying the chat interface.

## Vector Store and ChromaDB Reset

- **Symptom**: Outdated search results or empty collection error.
- **Resolution**:
  - Re-run the knowledge base ingestion script: `python scripts/ingest_kb.py`.
  - Ingestion uses deterministic chunk IDs; running the script refreshes existing chunks without creating duplicates.
  - The vector store is located at `%APPDATA%\Aegis\chroma`.
