# Pull required local models into Ollama
Write-Host "Pulling models into Ollama..." -ForegroundColor Cyan

ollama pull qwen2.5:3b
ollama pull llama-guard3:1b
ollama pull nomic-embed-text:v1.5

Write-Host "Model setup complete." -ForegroundColor Green
