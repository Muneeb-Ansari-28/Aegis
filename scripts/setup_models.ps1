# Pull required local models into Ollama for Aegis
Write-Host "Pulling configured models into Ollama..." -ForegroundColor Cyan

# Main LLM model for Attack, Recon, Judge, and Assistant agents (Qwen3-4B Instruct Abliterated GGUF)
ollama pull hf.co/mradermacher/Huihui-Qwen3-4B-Instruct-2507-abliterated-GGUF:Q4_K_M

# Fast Triage model (Llama Guard 3 1B)
ollama pull llama-guard3:1b

# Embedding model for RAG knowledge base
ollama pull nomic-embed-text:latest

Write-Host "Model pull complete." -ForegroundColor Green
Write-Host ""
Write-Host "To index the knowledge base, run:" -ForegroundColor Cyan
Write-Host "  .\.venv\Scripts\python -m app.rag.indexer (from engine directory)" -ForegroundColor White
