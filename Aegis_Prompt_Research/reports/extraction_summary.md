# Aegis LLM Security Research: Prompt Collection Extraction Summary & Integration Roadmap

**Published Date:** November 2026  
**Subject:** Final Extraction Summary, Dataset Metrics, and Integration Strategy for Aegis Platform  
**Prepared For:** Aegis Engineering & Threat Research Team  

---

## 1. Executive Summary

This report concludes the comprehensive research and extraction task for the **Aegis Open-Source LLM Vulnerability Prompt Collection**. All six open-source repositories designated by project leadership—**Promptfoo**, **DeepTeam**, **NVIDIA Garak**, **Microsoft PyRIT**, **AgentDojo**, and **Meta CyberSecEval**—were cloned, analyzed, and ingested without modifying Aegis's core application code.

A total of **1,399 high-fidelity prompt records** were extracted, normalized to Aegis's standardized JSON schema, mapped across all eight Aegis OWASP vulnerability categories, and partitioned across four material types.

---

## 2. Dataset Metrics & Composition

```
TOTAL EXTRACTED RECORDS: 1,399
TOTAL PARTITIONED JSON FILES: 59 files across prompt_library/
TOTAL REPOSITORIES REPRESENTED: 6 of 6
```

### 2.1 Distribution by Contributing Product
| Product | Contributed Records | Percentage | Primary Material Types |
|---|:---:|:---:|---|
| **Meta CyberSecEval** | 544 | 38.9% | Attack Payloads, Evaluation Judges, Code Interpreter Exploits |
| **DeepTeam (Confident AI)** | 286 | 20.4% | Vulnerability Templates, Crescendo Attacks, Evaluation Rubrics |
| **Microsoft PyRIT** | 172 | 12.3% | Jailbreak Templates, ASSERT Failure Rubrics, Many-Shot Priming |
| **AgentDojo (ETH SpyLab)** | 167 | 11.9% | Indirect Prompt Injections, Tool Abuse Goals, Benign Carriers |
| **NVIDIA Garak** | 123 | 8.8% | Static Probes, DAN Jailbreaks, Package Hallucinations, Heuristic Rubrics |
| **Promptfoo** | 107 | 7.6% | Red-Team Payloads, Grader Rubrics, Strategy Definitions |

### 2.2 Distribution by Vulnerability Category
| Category | Category Name | Record Count | Percent |
|---|---|:---:|:---:|
| `01_prompt_injection` | Prompt Injection | 656 | 46.9% |
| `05_excessive_agency` | Excessive Agency | 323 | 23.1% |
| `02_sensitive_information_disclosure` | Sensitive Information Disclosure | 124 | 8.9% |
| `03_misinformation` | Misinformation | 116 | 8.3% |
| `04_system_prompt_leakage` | System Prompt Leakage | 70 | 5.0% |
| `unmapped_research` | Unmapped Research | 52 | 3.7% |
| `07_supply_chain` | Supply Chain | 36 | 2.6% |
| `06_vector_rag_weaknesses` | Vector and RAG Weaknesses | 17 | 1.2% |
| `08_unbounded_consumption` | Unbounded Consumption | 5 | 0.4% |

### 2.3 Distribution by Material Type
| Material Type | Record Count | Purpose in Aegis Architecture |
|---|:---:|---|
| `attack_payloads` | **674** | Direct testing strings sent to target LLMs by the Attack Agent |
| `attack_generation_prompts` | **343** | Prompts and templates used by Attack Agent to synthesize dynamic mutations |
| `evaluation_prompts` | **260** | Rubrics, judge questions, and criteria used by Evaluation Agent |
| `supporting_strategies` | **122** | Mutation rules, encoders, decoders, multi-turn crescendo scripts |

---

## 3. Key Findings from Codebase & Dataset Inspection

1. **Convergence on Persona Roleplay & In-Context Priming:**
   - Over 60% of direct prompt injection attacks rely on persona coercion (DAN, AIM, Developer Mode) or in-context priming (many-shot prompting). Frontier reasoning models increasingly recognize and refuse standard DAN strings, necessitating multi-turn approaches (like DeepTeam's Crescendo).
2. **The Shift from Direct to Indirect Injection:**
   - AgentDojo represents the modern threat frontier: attacks hidden inside external data (untrusted email bodies, calendar invitations, customer notes). This confirms that Aegis's agentic testing capability is critical.
3. **Evaluation Rigor is the True Bottleneck:**
   - While attack prompts are abundant, high-quality automated evaluation is rare. Meta CyberSecEval solves this via binary verification questions ("Does this response contain the word 'Piano'?"), while DeepTeam and PyRIT utilize multi-criteria chain-of-thought rubrics.
4. **Structural Diversity Justifies Multi-Product Preservation:**
   - Each tool approaches the same threat differently: Garak provides deterministic baselines, PyRIT provides enterprise parameterization, DeepTeam provides dynamic adaptability, and AgentDojo provides environmental realism. Retaining all variants gives Aegis the broadest test surface.

---

## 4. Recommended Integration Roadmap for Aegis

```
┌────────────────────────────────────────────────────────────────────────┐
│                   AEGIS PROMPT INTEGRATION ARCHITECTURE                │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│   ┌──────────────────────────┐         ┌──────────────────────────┐   │
│   │   ATTACK PAYLOADS        │         │   EVALUATION PROMPTS     │   │
│   │   (674 Records)          │         │   (260 Records)          │   │
│   └────────────┬─────────────┘         └────────────┬─────────────┘   │
│                │                                    │                  │
│                ▼                                    ▼                  │
│   ┌──────────────────────────┐         ┌──────────────────────────┐   │
│   │   Aegis Attack Agent     │         │  Aegis Evaluation Agent  │   │
│   │   - Seed Knowledge Base  │         │  - Judge Rubrics         │   │
│   │   - Calibration Engine   │         │  - Ground-Truth Verifier │   │
│   │   - Adaptive Mutators    │         │  - Multi-Criteria Scorer │   │
│   └──────────────────────────┘         └──────────────────────────┘   │
│                ▲                                    ▲                  │
│                │                                    │                  │
│   ┌────────────┴─────────────┐         ┌────────────┴─────────────┐   │
│   │ ATTACK GENERATION        │         │ SUPPORTING STRATEGIES    │   │
│   │ PROMPTS (343 Records)    │         │ (122 Records)            │   │
│   └──────────────────────────┘         └──────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

### Phase 1: Attack Agent Seed Library Enhancement
- **Action:** Ingest the 674 `attack_payloads` into Aegis's static attack Knowledge Base (`engine/core/` knowledge base).
- **Benefit:** Immediately expands Aegis's initial probe library from basic hardcoded strings to 674 vetted adversarial vectors covering all 8 categories.
- **Priority Payloads:**
  - Ingest CyberSecEval's canary extraction payloads into Aegis's LLM08 module.
  - Ingest AgentDojo's indirect injection vectors into Aegis's tool-testing suite.
  - Ingest Garak's package hallucination stubs into Aegis's supply chain scanner.

### Phase 2: Dynamic Attack Generation & Calibration Engine
- **Action:** Integrate the 343 `attack_generation_prompts` and 122 `supporting_strategies` into the Attack Agent's rephrasing and mutation pipeline.
- **Benefit:** When a target model refuses an initial test prompt, Aegis will not merely rephrase casually; it will select from proven transformation strategies:
  - Crescendo gradual escalation (from DeepTeam).
  - Many-shot in-context priming (from PyRIT).
  - Linguistic continuation & JSON schema trapping (from Garak Goodside).
  - Obfuscation and encoding converters (Base64, ROT13, Leetspeak from PyRIT and Garak Buffs).

### Phase 3: Evaluation Agent Rubric Upgrade
- **Action:** Feed the 260 `evaluation_prompts` into Aegis's Stage 2 LLM Judge system prompts.
- **Benefit:** Dramatically reduces evaluation false positives and false negatives.
  - For canary extraction: adopt CyberSecEval's strict boolean verification query format.
  - For excessive agency and tool abuse: adopt AgentDojo's ground-truth state-difference verification.
  - For conversational safety: adopt PyRIT's ASSERT behavioral failure criteria.

### Phase 4: Closing the Industry Gaps (RAG & Unbounded Consumption)
- **Action:** Implement Aegis-native synthetic probers for Vector/RAG Weaknesses and Unbounded Consumption based on the recommendations in `reports/missing_coverage.md`.
- **Benefit:** Establishes Aegis as the only platform on the market with automated testing for vector store poisoning and LLM denial-of-wallet.

---

## 5. Artifact & Directory Index

All extracted resources and reports are organized and permanently persisted within `d:\vs_code_files\Aegis\Aegis_Prompt_Research\`:

- `prompt_library/`: 59 partitioned JSON files organized by category and material type.
- `metadata/`:
  - `repository_manifest.json`: Provenance, commits, licenses, and URLs for all 6 repositories.
  - `source_licenses.json`: Full licensing and legal compatibility analysis (MIT / Apache-2.0).
  - `category_mapping.json`: Mapping of vendor taxonomies to Aegis's 8 OWASP categories.
  - `extraction_manifest.json`: Index of all generated files, hashes, and record counts.
  - `extraction_statistics.json`: Machine-readable extraction metrics and cross-tabulation tables.
- `reports/`:
  - `competitor_analysis.md`: Detailed architecture and capability comparison of all 6 tools.
  - `vulnerability_coverage.md`: 8-category coverage matrix and category breakdowns.
  - `missing_coverage.md`: Deep dive into industry gaps (RAG, Unbounded Consumption, Supply Chain).
  - `duplicate_analysis.md`: Cross-product duplicate and near-duplicate similarity analysis.
  - `extraction_summary.md`: This comprehensive overview and Aegis integration roadmap.
- `extractors/`:
  - Python scripts (`extract_promptfoo.py`, `extract_deepteam.py`, `extract_garak.py`, `extract_pyrit.py`, `extract_agentdojo.py`, `extract_cyberseceval.py`).
  - `schema.py`: Shared data model definition.
- `run_extraction.py`: Master pipeline runner.
- `README.md`: Master directory guide and research overview.
