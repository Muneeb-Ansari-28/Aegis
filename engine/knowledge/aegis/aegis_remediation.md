# Aegis Remediation Playbooks and Guidelines

## LLM08:2026 Hidden Context Exposure Remediation

When an assessment detects Hidden Context Exposure (system prompt leakage), apply these foundational engineering principles:

### Core Remediation Principles
1. **Never place secrets in hidden context**:
   - Strictly remove API keys, passwords, database credentials, internal access tokens, and sensitive personal data from system prompts, tool instructions, and retrieved context.
2. **Do not treat prompt secrecy as a security boundary**:
   - Assume that any instruction, context, or framing provided to the model can eventually be extracted, inferred, or reconstructed by users through adversarial probing.
3. **Enforce authorization in trusted backend code**:
   - Access control, tool permissions, and data boundaries must be validated programmatically by trusted backend logic, never left to the model's willingness to follow system instructions.
4. **Minimize operational detail in system prompts**:
   - Keep system instructions concise and high-level. Avoid detailing backend architecture, internal database schemas, or proprietary business logic in prompt text.
5. **Use defense-in-depth measures**:
   - Deploy post-generation refusal filters, output guardrails, and canary monitoring as supplementary detection layers, while recognizing they are not substitutes for server-side authorization.
6. **Canary tokens are detection aids, not secrets**:
   - Synthetic canary strings embedded in prompt templates serve to detect leakage in logs and telemetry; they do not prevent exposure or protect underlying data.

## Defensive Implementation Patterns

- **Dual-Model Isolation**: Separate public-facing dialogue generation from privileged tool execution.
- **Strict Output Sanitization**: Filter model responses through regex and pattern matching to intercept system signatures or internal markers before delivery to the client.
- **Granular Retrieval Scoping**: Ensure RAG retrievals only retrieve document chunks that the requesting user is cryptographically or organizationally authorized to read.
