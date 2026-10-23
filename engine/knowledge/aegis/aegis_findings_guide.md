# Aegis Findings and Evaluation Guide

## Finding Structure and Data Model

When Aegis evaluates a target's response during an assessment turn, an exploited interaction generates a verified finding:
- **Category**: The vulnerability identifier (e.g., `LLM08`).
- **Severity**: Deterministically calculated severity rating (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`).
- **Confidence**: Numerical certainty value between 0.0 and 1.0.
- **Evidence**: Prompt submitted, response returned, and extracted leaked strings or canary matches.
- **Strategy**: The disclosure technique used (e.g. fixed disclosure, template variation, semantic probe).
- **Linked Turn**: Exact turn index and timestamp tying the finding to the execution record.

## Evaluation Mechanism

Aegis evaluates turns through a hybrid evaluation pipeline:
1. **Deterministic Canary Detector**: Checks for the exact or normalized presence of canary tokens injected into test targets.
2. **Deterministic Overlap Scorer**: Computes n-gram and token overlap between the target response and known system prompt text.
3. **LLM Judge Rubric**: Invokes a local judge model using a fixed rubric to evaluate semantic leakage when exact strings are obfuscated or paraphrased.
4. **JSON Guard**: Enforces strict Pydantic parsing and schema validation on evaluator outputs with retry mechanisms for malformed outputs.

## Canaries as Detection Aids

- In Aegis test environments, canary strings (e.g. `AEGIS_CANARY_xyz`) act as high-confidence marker tokens.
- **Important**: Canaries are detection aids, not security controls and not secrets. Real-world applications should not rely on canaries to prevent leakage, but rather use them to alert on unauthorized extraction.
