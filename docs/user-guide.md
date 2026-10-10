# Aegis User Guide

## Assessment scope

The current scan category is OWASP LLM07 System Prompt Leakage. Use direct plain-language requests only, and scan targets you own or have written permission to assess. Jailbreaks, role impersonation, instruction overrides, obfuscation, and real-secret extraction are excluded.

## Getting Started

1. Run `scripts/setup_models.ps1` to pull required models.
2. Launch the engine: `cd engine && python main.py`.
3. Launch the desktop UI: `cd desktop && npm run dev`.
