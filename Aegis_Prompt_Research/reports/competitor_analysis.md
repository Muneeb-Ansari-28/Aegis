# Aegis Competitor & Ecosystem Analysis: Open-Source LLM Security Testing Tools

**Published Date:** November 2026  
**Subject:** Comparative Deep-Dive into 6 Open-Source LLM Red-Teaming & Vulnerability Assessment Products  
**Prepared For:** Aegis Engineering & Threat Research Team  

---

## 1. Executive Overview

This report presents an architectural and capability analysis of the six leading open-source LLM security testing tools: **Promptfoo**, **DeepTeam (Confident AI)**, **NVIDIA Garak**, **Microsoft PyRIT**, **AgentDojo (ETH Zurich SpyLab)**, and **Meta CyberSecEval (Purple Llama)**.

As part of the **Aegis Open-Source LLM Vulnerability Prompt Collection** project, each repository's codebase, data schemas, attack generation engines, evaluation frameworks, and prompt datasets were inspected and ingested.

| Product | Maintainer | Primary Architecture | Focus Area | Prompt Representation | Core License |
|---|---|---|---|---|---|
| **Promptfoo** | Promptfoo Inc. | TypeScript / Node.js CLI & Web UI | Red-teaming plugins & CI/CD assertion testing | YAML config + TypeScript plugins | MIT |
| **DeepTeam** | Confident AI | Python library & orchestration engine | Dynamic multi-turn attacks & OWASP/Agentic vulns | Python vulnerability templates + classes | Apache-2.0 |
| **Garak** | NVIDIA | Python modular probing framework | Static probe generators & heuristic detectors | Python classes + JSON/TSV data assets | Apache-2.0 |
| **PyRIT** | Microsoft AI Red Team | Python SDK & extensible red-team orchestration | Adversarial prompting, converters & ASSERT scoring | YAML templates + behavior definitions | MIT |
| **AgentDojo** | ETH Zurich (SpyLab) | Python simulated tool environment | Indirect prompt injection & tool misuse benchmarking | Python task suites + YAML injection vectors | MIT |
| **CyberSecEval** | Meta (Purple Llama) | Python benchmark harness | Quantitative security evaluations & canary tests | JSON test datasets + automated LLM judges | MIT |

---

## 2. In-Depth Product Profiles

### 2.1 Promptfoo
- **Repository:** `https://github.com/promptfoo/promptfoo`
- **Architecture & Approach:** Promptfoo is built around a declarative configuration paradigm (`promptfooconfig.yaml`). Users define providers (OpenAI, Anthropic, local endpoints), prompt templates, and plugins. It runs tests concurrently, scoring responses using deterministic assertions (regex, contains) or model-graded rubrics. Its red-teaming subsystem generates automated adversarial variations across OWASP LLM categories.
- **Strengths:**
  - Extremely fast execution with rich Web UI and terminal reporting.
  - Native CI/CD integration patterns (GitHub Actions, GitLab CI).
  - Clean declarative test definitions.
  - Generative red-teaming plugins that dynamically adapt to the target application's domain.
- **Limitations:**
  - Less sophisticated multi-turn conversation simulation compared to PyRIT or DeepTeam.
  - Minimal stateful agentic environment simulation (primarily tests direct HTTP endpoints).
  - Heavy reliance on external LLM calls to generate red-team payloads on the fly.
- **Prompt Storage Format:**
  - Red-team plugins in `src/redteam/plugins/*.ts` define `DEFAULT_EXAMPLES` and rubric generator functions (`getGraderConfig`).
- **Unique Vectors:**
  - Broken Function Level Authorization (BFLA/BOLA) prompt probes.
  - Administrative debug masquerading (`debug-access`).
  - Competitor mention extraction and brand integrity testing.
- **Value to Aegis:**
  - High-value evaluation rubrics for judging subtle vulnerabilities like BFLA and debug mode bypasses.
  - Clean separation between test examples and grading assertions.

---

### 2.2 DeepTeam (Confident AI)
- **Repository:** `https://github.com/confident-ai/deepteam`
- **Architecture & Approach:** Python framework designed specifically for automated adversarial red teaming against LLM applications and autonomous agents. Organizes attacks into 37 distinct vulnerability classes, each paired with a dedicated attack engine (SingleTurn, Linear, Crescendo, TreeSearch).
- **Strengths:**
  - Best-in-class multi-turn Crescendo and Tree-Search jailbreak engines.
  - Direct mapping to OWASP Top 10 for LLMs and agent-specific risk taxonomies (BFAC, BFLA, SSRF, SQLi).
  - Rich evaluation metric rubrics that provide quantitative scoring (0.0 to 1.0) with chain-of-thought justification.
- **Limitations:**
  - Tightly coupled to commercial DeepEval / Confident AI ecosystem conventions.
  - Slower execution when running iterative tree-search attacks due to high LLM token consumption.
- **Prompt Storage Format:**
  - Python vulnerability definitions in `deepteam/vulnerabilities/*.py` storing vulnerability descriptions, default attack prompts, and generation templates.
  - Attack orchestration prompts in `deepteam/attacks/*.py`.
- **Unique Vectors:**
  - Multi-turn Crescendo attacks (`crescendo.py`) that gradually escalate from benign background discussion to policy violations over 5-10 turns.
  - Server-Side Request Forgery (SSRF) and SQL injection probes adapted specifically for LLM tool environments.
- **Value to Aegis:**
  - Direct algorithmic blueprint for Aegis's multi-turn adaptive attack orchestration.
  - Highly structured evaluation rubrics with explicit criteria for passing vs failing responses.

---

### 2.3 NVIDIA Garak
- **Repository:** `https://github.com/NVIDIA/garak`
- **Architecture & Approach:** Garak operates as a vulnerability scanner for LLMs, modeled after traditional vulnerability scanners like Nmap and Nessus. It pairs **Probes** (input generators) with **Detectors** (evaluation logic) and **Buffs** (input mutation transformers).
- **Strengths:**
  - Massive repository of curated academic and historical attack payloads (DAN, PromptInject, RealToxicityPrompts).
  - Deterministic and reproducible: probes emit fixed or pseudo-randomly seeded prompt sets.
  - Built-in Package Hallucination probes detecting Python, Ruby, JavaScript, Rust, and Go package fabrication.
  - Lightweight execution without requiring heavy GPU or LLM dependencies for basic detectors (uses regexes, keyword matching, and fast classifiers).
- **Limitations:**
  - Primarily static and single-turn; lacks adaptive multi-turn agent conversation modeling.
  - Evaluation detectors can have high false-positive or false-negative rates when relying solely on regexes.
- **Prompt Storage Format:**
  - Python probe modules in `garak/probes/*.py` defining class attributes (`prompts = [...]`, `tags`, `goal`).
  - Raw JSON and TSV data files in `garak/data/` (e.g. `dan/*.json`, `truefalse_falseclaims.txt`, `book_cloze.tsv`).
- **Unique Vectors:**
  - **Package Hallucination / Slopsquatting:** Probing for fabricated third-party libraries across multiple languages (`packagehallucination.py`).
  - **Riley Goodside Probes:** Linguistic continuation tricks, JSON schema coercion, and token repetition exploits (`goodside.py`).
  - **Glitch Tokens & Divergence:** Identifying adversarial tokens that cause tokenizers to crash or trigger infinite loops (`glitch.py`, `divergence.py`).
- **Value to Aegis:**
  - Unmatched static seed library for supply chain and system prompt extraction attacks.
  - Buff mutation strategies (encoding, capitalization, paraphrasing) for payload transformation.

---

### 2.4 Microsoft PyRIT (Python Risk Identification Tool)
- **Repository:** `https://github.com/microsoft/PyRIT`
- **Architecture & Approach:** Developed by the Microsoft AI Red Team, PyRIT is an enterprise-grade AI red-teaming SDK. It decouples targets (APIs, endpoints) from attack orchestrators (Crescendo, PAIR, Tree of Attacks) and scoring agents (LLM judges, substring scorers, self-ask evaluators). It includes the **ASSERT** (AI Safety Standardized Evaluation of Risks & Threats) dataset.
- **Strengths:**
  - Mature enterprise architecture with complete database-backed tracking of conversations and artifacts.
  - Comprehensive library of 90+ parameterized jailbreak templates (`datasets/jailbreak/templates/*.yaml`).
  - Rigorous 52 ASSERT behavioral failure rubrics defining exact boundaries for agentic and conversational risks.
  - Modular converters for payload encoding (Base64, ROT13, Leetspeak, Unicode, AsciiArt).
- **Limitations:**
  - High setup complexity and extensive dependency stack.
  - Primarily SDK-focused; lacks a turnkey out-of-the-box CLI for simple ad-hoc scanning.
- **Prompt Storage Format:**
  - YAML template files with metadata (`name`, `description`, `authors`, `parameters`, `value`).
  - JSON datasets (`many_shot_examples.json`).
  - Python scoring modules with standardized system prompts in `pyrit/score/`.
- **Unique Vectors:**
  - **Many-Shot In-Context Priming:** Exploiting long-context windows with hundreds of pre-filled compliant turns to lower safety guardrails (`many_shot_examples.json`).
  - **Converter Ensembles:** Chaining multiple encoding strategies to bypass input content filters.
  - **ASSERT Rubrics:** Enterprise behavioral guidelines for agentic failures (goal drift, flawed action plans, actionability failures).
- **Value to Aegis:**
  - Standardized YAML templates for prompt injection and jailbreak payloads.
  - Invaluable evaluation criteria for Aegis's Evaluation Agent to judge complex agent failure modes.

---

### 2.5 AgentDojo (ETH Zurich SpyLab)
- **Repository:** `https://github.com/ethz-spylab/agentdojo`
- **Architecture & Approach:** AgentDojo is a benchmark framework specifically engineered to evaluate **Indirect Prompt Injection** and **Excessive Agency** in tool-using LLM agents. Rather than sending prompts directly to the LLM, AgentDojo simulates realistic multi-application ecosystems (Banking, Slack, Travel Booking, Workspace) where untrusted attacker instructions reside inside carrier data (emails, bills, calendar invites, web pages).
- **Strengths:**
  - The gold standard for evaluating indirect prompt injection against tool-equipped agents.
  - Realistic multi-tenant environments with concrete tool sets (APIs for sending money, managing calendar, reading drive files).
  - Dual metric evaluation: **Utility** (did the agent solve the user's task?) vs. **Security** (did the agent execute the attacker's injected goal?).
- **Limitations:**
  - Specialized benchmark rather than a general-purpose security scanner.
  - Focuses exclusively on agent tool workflows; does not cover broader conversational risks (misinformation, hate speech).
- **Prompt Storage Format:**
  - Python task suites (`injection_tasks.py` defining malicious goals, `user_tasks.py` defining user instructions).
  - YAML injection vectors (`injection_vectors.yaml`) specifying where injections are planted.
  - JSON benchmark run traces recording the exact injected strings and tool invocation sequences.
- **Unique Vectors:**
  - Indirect prompt injection embedded inside legitimate structured data (e.g. invoice memo, landlord notice, flight review).
  - Cross-tool data exfiltration (e.g., reading user's Google Drive files and emailing them to an external attacker address).
  - Financial fraud via agent delegation (e.g., tricking banking agent into sending wire transfers to an attacker IBAN).
- **Value to Aegis:**
  - Critical repository for Aegis's agentic attack capabilities (testing autonomous agents with tools).
  - Real-world indirect injection templates that circumvent conventional chat-level guardrails.

---

### 2.6 Meta CyberSecEval (Purple Llama)
- **Repository:** `https://github.com/meta-llama/PurpleLlama`
- **Architecture & Approach:** Developed by Meta's AI Security team, CyberSecEval is an open-source evaluation suite designed to quantify LLM safety risks across cybersecurity domains. It evaluates direct/indirect prompt injection, code interpreter sandbox escapes, insecure code autocomplete (CWE vulnerabilities), autonomous cyber offensive uplift, and MITRE ATT&CK adherence.
- **Strengths:**
  - Massive, empirically validated benchmark datasets with thousands of curated test cases.
  - Standardized LLM-as-a-Judge evaluation methodology with unambiguous boolean scoring questions.
  - Covers low-level code generation vulnerabilities (CWE insertion in C, C++, Python, JavaScript).
- **Limitations:**
  - Static benchmark dataset; does not provide an interactive scanner or dynamic multi-turn attacker agent.
  - Datasets can become outdated as frontier models memorize benchmark test cases.
- **Prompt Storage Format:**
  - Structured JSON files (`prompt_injection.json`, `interpreter.json`, `autocomplete.json`, `mitre_benchmark.json`).
  - Python test generators and verifier scripts (`canary_exploit/`, `base_test_generator.py`).
- **Unique Vectors:**
  - **Code Interpreter Sandbox Escapes:** 500 prompts testing whether code interpreter agents can be coerced into reading `/etc/shadow`, binding raw sockets, or escalating privileges.
  - **Insecure Autocomplete:** Code completion prompts mapped to specific CWEs (e.g. SQL injection, command injection, insecure deserialization) to test if LLMs recommend insecure patterns.
  - **MITRE ATT&CK Mapping:** Prompts systematically testing LLM willingness to assist in adversary TTPs (persistence, credential dumping, lateral movement).
- **Value to Aegis:**
  - High-volume, high-quality ground-truth datasets for prompt injection and code execution risks.
  - Clear, concise judge questions that can directly enrich Aegis's Evaluation Agent prompts.

---

## 3. Comparative Summary & Strategic Value Matrix

| Capability Dimension | Promptfoo | DeepTeam | Garak | PyRIT | AgentDojo | CyberSecEval |
|---|---|---|---|---|---|---|
| **Direct Prompt Injection** | Strong | Strong | Strong | Strong | Partial | Strong |
| **Indirect Prompt Injection** | Partial | Partial | Partial | Partial | **Strong (Industry Lead)** | Strong |
| **Multi-Turn Adaptive Attacks** | Partial | **Strong (Crescendo/Tree)** | Weak | **Strong (PAIR/Orchestrator)** | Partial | None (Static) |
| **Agent Tool Abuse Testing** | Moderate | Moderate | Moderate | Moderate | **Strong (Realistic APIs)** | Moderate |
| **Supply Chain / Code Risks** | Weak | Weak | Moderate (Pkg Hallucination) | Weak | Weak | **Strong (CWE Autocomplete)** |
| **System Prompt Canary Testing**| Moderate | Moderate | Strong (Goodside) | Moderate | Moderate | **Strong (Benchmark-grade)** |
| **Automated Evaluation Rubrics**| Strong | **Strong (Chain-of-Thought)** | Moderate (Heuristics) | **Strong (ASSERT Rubrics)** | Strong (State Diff) | **Strong (Boolean Judges)** |
| **Ease of CI/CD Integration** | **Strong (CLI/GitHub Action)** | Moderate | Moderate | Moderate | Weak (Research Bench) | Moderate |

---

## 4. Key Takeaways for Aegis Architecture

1. **Attack Generation:** Combine **PyRIT's** parameterized templates (as seeds) with **DeepTeam's** Crescendo/Tree mutation algorithms and **Garak's** token-level buffs to generate high-yield adaptive attacks.
2. **Agentic & Tool Testing:** Ingest **AgentDojo's** indirect injection patterns and **CyberSecEval's** interpreter payloads to test Aegis's ability to evaluate tool-calling agent systems.
3. **Evaluation Rigor:** Blend **CyberSecEval's** concise boolean judge queries with **DeepTeam's** multi-point criteria and **PyRIT's** ASSERT behavioral definitions to produce Aegis's dual-tier evaluation engine.
