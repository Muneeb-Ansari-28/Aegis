# Aegis User Guide

## Assessment scope

The current scan category is OWASP LLM07 System Prompt Leakage. Use direct plain-language requests only, and scan targets you own or have written permission to assess. Jailbreaks, role impersonation, instruction overrides, obfuscation, and real-secret extraction are excluded.

## Getting Started

1. Run `scripts/setup_models.ps1` to pull required models.
2. Launch the engine: `cd engine && python main.py`.
3. Launch the desktop UI: `cd desktop && npm run dev`.


## Inspect assessment results

Open an assessment from Overview's Recent Assessments, Scan History's Inspect action, or Results & findings. The Results view uses the selected scan (falling back to active/latest local history); when multiple local records exist, use the scan selector. History is specific to this browser profile, not a complete list of engine database records.

Overview summarizes evaluated prompts, persisted findings and severity counts, key findings, recorded test cases, assessment metadata and metrics. Open a key finding to inspect its linked evidence; Findings expands prompt/response/remediation details, Evidence lists all returned turns, and Timeline presents their recorded timestamps/outcomes. Use Refresh to retrieve updates; this view does not continuously poll.

Export PDF downloads the existing backend report, generating it when no file exists. The UI requires loaded metadata and a terminal scan status. There is no separate report preview or regenerate control. Errors offer retry; unavailable data must not be interpreted as zero findings or proof of security. Connector diagnostics are not evaluated chatbot responses.

The Milestone 5 layout is implemented and fixture-tested, but visual approval and live Results/PDF integration acceptance remain pending. See [current status and limitations](../Project-Context/Status.md) before relying on assessment or PDF conclusions.
