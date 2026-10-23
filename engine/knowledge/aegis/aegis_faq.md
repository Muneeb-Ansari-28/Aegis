# Aegis Frequently Asked Questions (FAQ)

## General Questions

### What is Aegis?
Aegis is a local-first red-teaming platform designed to assess LLM applications against OWASP security vulnerabilities. It combines browser automation, deterministic state machines, and local evaluation models.

### Does Aegis send my data to external cloud services?
No. Aegis runs 100% locally on your machine using Ollama for model generation/embeddings and SQLite/ChromaDB for storage. Target interactions, scan prompts, and findings remain entirely on your device.

### Which OWASP Top 10 vulnerabilities does Aegis scan today?
Aegis currently implements an end-to-end automated scan workflow for **LLM08:2026 Hidden Context Exposure** (formerly known as LLM07:2025 System Prompt Leakage). The other nine categories from the OWASP 2026 Top 10 are actively under development in the scanner pipeline.

### Can the Aegis Assistant explain vulnerabilities that Aegis doesn't scan yet?
Yes! The Aegis AI Assistant's knowledge base contains comprehensive coverage of all ten OWASP 2026 categories (LLM01 through LLM10), including their definitions, attack examples, mitigations, and crosswalk comparisons from 2025.

### What happens when an assessment exceeds its budget?
Aegis enforces a strict scan budget (defaulting to 10 interaction turns per category). If a scan reaches its maximum budget without finishing, the orchestrator terminates the run cleanly and sets the state to `COMPLETED` or `STOPPED`.

### What does an Aegis risk grade mean?
Aegis calculates a risk score between 0 and 100 based on verified findings and their severity:
- 90–100: Resilient (Low Risk)
- 75–89: Fair (Moderate Risk)
- 50–74: Vulnerable (Elevated Risk)
- 0–49: Compromised (Critical Risk)
