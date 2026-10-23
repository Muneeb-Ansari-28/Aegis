# Aegis Security and LLM Glossary

## Core Terms and Definitions

### Retrieval-Augmented Generation (RAG)
An architectural technique that enhances LLM generation by retrieving relevant documents or chunks from an external knowledge store (such as a vector database) and providing them as grounded reference context in the model prompt.

### Vector Embeddings
Dense mathematical vector representations (lists of floating-point numbers) of text semantics. In Aegis, the `nomic-embed-text` model converts text passages into 768-dimensional embedding vectors.

### Cosine Similarity and Cosine Distance
A mathematical metric that measures the angular distance between two normalized vectors in multi-dimensional space. In vector search, lower cosine distance indicates higher semantic relevance between the query vector and document vector.

### System Prompt
Initial non-user-facing instructions provided by application developers to establish an LLM's persona, operating rules, constraints, tool capabilities, and security boundaries.

### Hidden Context Exposure (LLM08:2026)
The security risk where an attacker extracts, reconstructs, or infers non-user-facing instructions, system prompts, operational context, or internal configuration from an LLM application. Formerly known in OWASP 2025 as System Prompt Leakage (LLM07:2025).

### Prompt Injection (LLM01:2026)
An attack where untrusted user input alters the intended instructions or control flow of an LLM system, causing it to disregard prior instructions or perform unauthorized actions.

### Canary Token
A unique, synthetic tracking string (e.g. `AEGIS_CANARY_abc123`) embedded into system prompts or data pipelines to act as an unforgeable detection marker when unauthorized leakage or data extraction occurs.

### Unified Turn Record (UTR)
The canonical data contract in Aegis representing a single round of interaction (prompt, response, latency, strategy, verdict) between the test engine and the target system.
