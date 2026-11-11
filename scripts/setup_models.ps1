# Pull required local models into Ollama for Aegis
Write-Host "Pulling configured models into Ollama..." -ForegroundColor Cyan

# Main LLM model for Attack, Recon, Judge, and Assistant agents
ollama pull llama3.2:latest

# Embedding model for RAG knowledge base
ollama pull nomic-embed-text:latest

Write-Host "Model pull complete." -ForegroundColor Green
Write-Host ""
Write-Host "To index the knowledge base, run:" -ForegroundColor Cyan
Write-Host "  .\.venv\Scripts\python -m app.rag.indexer (from engine directory)" -ForegroundColor White
