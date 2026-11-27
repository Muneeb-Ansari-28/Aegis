# Task: Build Aegis Open-Source LLM Vulnerability Prompt Collection

## 1. Objective

I am developing **Aegis**, an Agentic AI-Powered LLM Application Security Testing Platform.

The end-to-end architecture of Aegis is already completed. The current task is to research existing open-source LLM security testing products, download their repositories, inspect their source code and datasets, and extract all relevant vulnerability-testing prompts.

Your primary objective is to build a comprehensive, categorized prompt collection that can later be used to enhance Aegis's Attack Agent and Evaluation Agent.

**IMPORTANT: Do not modify Aegis's existing architecture or application code. This is a research and prompt-collection task only.**

## 2. Open-Source Products to Download

Download and inspect all six repositories:

| Product           | GitHub Repository                         | Primary Research Focus                                                  |
| ----------------- | ----------------------------------------- | ----------------------------------------------------------------------- |
| Promptfoo         | https://github.com/promptfoo/promptfoo    | Attack payloads, OWASP vulnerability plugins, attack strategies         |
| DeepTeam          | https://github.com/confident-ai/deepteam  | Vulnerability prompts, attack methods, evaluation metrics               |
| NVIDIA garak      | https://github.com/NVIDIA/garak           | Static attack prompts, probes, detectors                                |
| Microsoft PyRIT   | https://github.com/Azure/PyRIT            | Adversarial prompts, seed datasets, scorers, evaluator prompts          |
| AgentDojo         | https://github.com/ethz-spylab/agentdojo  | Indirect injection, agent security and unauthorized tool-use scenarios  |
| Meta CyberSecEval | https://github.com/meta-llama/PurpleLlama | Prompt injection datasets, adversarial examples and evaluation datasets |

Download the repositories using Git clone or GitHub ZIP archives.

Use Git clone where possible because repository history, branches and source structure may help with research.

Store the downloaded repositories separately from the extracted prompt library.

## 3. Required OWASP Vulnerability Categories

Organize the collected prompts according to these eight Aegis vulnerability categories:

1. Prompt Injection
2. Sensitive Information Disclosure
3. Misinformation
4. System Prompt Leakage
5. Excessive Agency
6. Vector and RAG Weaknesses
7. Supply Chain
8. Unbounded Consumption

Do not limit the research to exact category names.

Inspect vulnerability subcategories, attack techniques, test cases, datasets, YAML files, JSON files, Python source files, templates and embedded prompt strings.

Map relevant techniques to the closest Aegis category.

If a technique belongs to multiple categories, record all applicable mappings.

Do not force unrelated test cases into an OWASP category. Place genuinely unmatched material in an additional `unmapped_research` directory with an explanation.

## 4. Critical Extraction Rule: Collect From Every Available Source

This is the most important requirement.

If a particular vulnerability category has relevant prompts in multiple products, extract the prompts from ALL those products.

For example:

Prompt Injection:

- Extract Promptfoo's prompt injection payloads.
- Extract DeepTeam's prompt injection attacks.
- Extract garak's prompt injection probes.
- Extract PyRIT's relevant adversarial prompts.
- Extract AgentDojo's indirect injection examples.
- Extract CyberSecEval's prompt injection datasets.

Do not select only one product as the source for a category.

Do not discard duplicate or similar prompts originating from different repositories.

If two products have similar prompts, preserve both and record their respective source information. This is necessary for comparing different attack approaches.

Deduplicate only accidental repeated copies within the same source where the same test case appears multiple times.

Maintain a source-level record of every extracted item.

## 5. What Exactly to Extract

Collect the following four types of material separately.

### A. Attack Payloads

Actual prompts, inputs, seed strings, adversarial instructions and test cases intended to be sent to the target LLM application.

Examples:

- Direct prompt injection.
- Indirect prompt injection.
- Jailbreak attempts.
- System prompt extraction attempts.
- Sensitive information extraction.
- RAG context manipulation.
- Unauthorized tool-use attempts.
- Misinformation generation tests.
- Resource exhaustion tests.

### B. Attack Generation Prompts

System prompts or instruction templates used by the competing products to generate adversarial test inputs dynamically.

Examples:

- Red-team attacker instructions.
- Jailbreak generation templates.
- Adaptive attack instructions.
- Multi-turn attack generation prompts.
- Mutation and transformation instructions.

### C. Evaluation and Judge Prompts

Extract instructions given to LLM-based evaluators, judges, scorers or detectors.

Examples:

- Determine whether a prompt injection succeeded.
- Determine whether sensitive information was disclosed.
- Determine whether the system revealed its hidden instructions.
- Determine whether an AI agent performed an unauthorized action.
- Determine whether the response contains misinformation.
- Determine whether an attack successfully manipulated retrieved context.

Preserve the original evaluation instructions and their expected output schemas.

### D. Attack Strategies and Supporting Metadata

Collect:

- Attack technique names.
- Attack execution sequences.
- Multi-turn conversation examples.
- Prompt transformations.
- Encoding techniques.
- Detector patterns.
- Vulnerability definitions.
- Expected safe behavior.
- Scoring criteria.

Do not mistake ordinary source-code strings, documentation descriptions or vulnerability names for actual attack prompts. Classify each extracted item according to its real purpose.

## 6. Product-Specific Research Locations

Use these locations as starting points, but do not assume they contain everything.

### Promptfoo

Repository: https://github.com/promptfoo/promptfoo

Inspect:

- `src/redteam/plugins/`
- `src/redteam/strategies/`
- `src/redteam/`
- Relevant test fixtures and datasets.

### DeepTeam

Repository: https://github.com/confident-ai/deepteam

Inspect:

- `deepteam/vulnerabilities/`
- `deepteam/attacks/`
- `deepteam/metrics/`
- Relevant tests, fixtures and examples.

### garak

Repository: https://github.com/NVIDIA/garak

Inspect:

- `garak/probes/`
- `garak/detectors/`
- `garak/resources/`
- Relevant configuration and test data.

### PyRIT

Repository: https://github.com/Azure/PyRIT

Inspect:

- Seed datasets.
- Scorer implementations.
- Scorer prompt templates.
- Attack implementations.
- YAML configuration files.
- Scenario examples.
- Documentation and test fixtures.

### AgentDojo

Repository: https://github.com/ethz-spylab/agentdojo

Inspect:

- `src/agentdojo/`
- Benchmark tasks.
- User and attacker instructions.
- Tool-use scenarios.
- Indirect prompt injection examples.
- Evaluation and utility implementations.

### CyberSecEval

Repository: https://github.com/meta-llama/PurpleLlama

Inspect:

- `CybersecurityBenchmarks/datasets/`
- Prompt injection datasets.
- Evaluation instructions.
- Relevant benchmark test cases.
- Scoring and judge implementations.

These are starting locations, not exhaustive search boundaries. Explore the full repositories where necessary.

## 7. Required Output Directory Structure

Create the following directory:

`Aegis_Prompt_Research/`

Organize the output as follows:

Aegis_Prompt_Research/
│
├── downloaded_repositories/
│ ├── promptfoo/
│ ├── deepteam/
│ ├── garak/
│ ├── pyrit/
│ ├── agentdojo/
│ └── cyberseceval/
│
├── prompt_library/
│ │
│ ├── 01_prompt_injection/
│ │ ├── attack_payloads/
│ │ │ ├── promptfoo.json
│ │ │ ├── deepteam.json
│ │ │ ├── garak.json
│ │ │ ├── pyrit.json
│ │ │ ├── agentdojo.json
│ │ │ └── cyberseceval.json
│ │ │
│ │ ├── attack_generation_prompts/
│ │ ├── evaluation_prompts/
│ │ └── supporting_strategies/
│ │
│ ├── 02_sensitive_information_disclosure/
│ ├── 03_misinformation/
│ ├── 04_system_prompt_leakage/
│ ├── 05_excessive_agency/
│ ├── 06_vector_rag_weaknesses/
│ ├── 07_supply_chain/
│ └── 08_unbounded_consumption/
│
├── metadata/
│ ├── repository_manifest.json
│ ├── extraction_manifest.json
│ ├── category_mapping.json
│ ├── source_licenses.json
│ └── extraction_statistics.json
│
├── reports/
│ ├── competitor_analysis.md
│ ├── vulnerability_coverage.md
│ ├── missing_coverage.md
│ ├── duplicate_analysis.md
│ └── extraction_summary.md
│
└── README.md

You may create additional subdirectories when necessary, but preserve the main organization.

## 8. Standard JSON Format for Extracted Prompts

Every extracted prompt must follow a consistent JSON schema.

Example:

{
"prompt_id": "PI-PROMPTFOO-001",
"source_product": "Promptfoo",
"source_repository": "https://github.com/promptfoo/promptfoo",
"source_file": "actual/relative/path/to/source",
"source_reference": "function, class, dataset ID or line range where available",
"vulnerability_category": "Prompt Injection",
"vulnerability_subcategory": "Direct Prompt Injection",
"attack_type": "Single-turn",
"material_type": "Attack Payload",
"attack_technique": "Instruction Override",
"original_prompt": "Exact original prompt or test input",
"expected_behavior": "The target should reject unauthorized instructions.",
"evaluation_criteria": "Determine whether the target followed the injected instruction.",
"original_output_format": null,
"adapted_for_aegis": false,
"license": "Repository or dataset license",
"notes": "Additional research observations"
}

Rules:

1. Preserve the exact original prompt wherever possible.
2. Do not silently rewrite, simplify or translate source prompts.
3. Keep original and adapted versions separate.
4. Preserve the original source filename and repository reference.
5. Use unique prompt IDs.
6. Include the source license or mark it as unknown pending verification.
7. Use null for genuinely unavailable fields.
8. If the original material is a multi-turn sequence, preserve the entire sequence and its turn order.
9. If a prompt is generated dynamically by source code, document its generation template and required parameters instead of pretending it is a fixed payload.
10. If the source is a dataset, retain its original dataset identifier.

## 9. Duplicate and Cross-Product Analysis

Create a duplicate analysis across all six products.

There are three cases:

- Exact duplicates: Identical prompts.
- Near duplicates: Different wording but substantially similar attack objectives.
- Different techniques: Same vulnerability category but different attack approaches.

Preserve every original source record, even when prompts are duplicates.

Add cross-reference metadata:

{
"similarity_group": "PI-GROUP-001",
"related_prompt_ids": [
"PI-PROMPTFOO-001",
"PI-GARAK-004"
],
"similarity_type": "Near Duplicate",
"reason": "Both attempt to override the target's system instructions."
}

Do not merge the original records into one prompt.

If similarity is determined by an embedding model, record the model and similarity threshold used. Do not claim semantic similarity has been verified if only textual matching was performed.

## 10. Coverage Matrix

Generate a report showing which products provide relevant material for each Aegis vulnerability category.

Example:

| Vulnerability                    | Promptfoo | DeepTeam | garak  | PyRIT  | AgentDojo | CyberSecEval |
| -------------------------------- | --------- | -------- | ------ | ------ | --------- | ------------ |
| Prompt Injection                 | Yes/No    | Yes/No   | Yes/No | Yes/No | Yes/No    | Yes/No       |
| Sensitive Information Disclosure |           |          |        |        |           |              |
| Misinformation                   |           |          |        |        |           |              |
| System Prompt Leakage            |           |          |        |        |           |              |
| Excessive Agency                 |           |          |        |        |           |              |
| Vector/RAG Weaknesses            |           |          |        |        |           |              |
| Supply Chain                     |           |          |        |        |           |              |
| Unbounded Consumption            |           |          |        |        |           |              |

Use these statuses:

- Strong: Actual relevant prompts or test cases found.
- Partial: Related examples or techniques found.
- None found: No relevant material identified after inspection.
- Not inspected: Repository inspection incomplete.

Do not mark a category as covered merely because its name appears in documentation.

## 11. Research Quality Requirements

Follow these rules strictly:

1. Do not invent prompts.
2. Do not fabricate source references.
3. Do not replace original prompts with your own examples.
4. Do not discard prompts because another product has similar ones.
5. Do not collect only a handful of examples when larger datasets are available.
6. Inspect actual source code and bundled datasets rather than relying only on README files.
7. Preserve multi-turn conversations.
8. Separate attack payloads from evaluator instructions.
9. Separate attack-generation templates from static payloads.
10. Document unavailable or inaccessible source material.
11. Respect repository and dataset licenses.
12. Do not execute extracted adversarial prompts against external systems during this research task.

If a repository contains dynamically generated prompts, inspect the generator implementation and record the template, variables and generation mechanism.

If a prompt is assembled from multiple source components, preserve the assembly logic and dependencies.

## 12. Final Deliverables

At completion, provide:

1. All six downloaded repositories.
2. A structured JSON prompt library.
3. Separate attack payload and evaluator prompt collections.
4. Source-level traceability for every extracted item.
5. The eight-category coverage matrix.
6. Cross-product duplicate and similarity analysis.
7. A list of categories with insufficient source material.
8. A competitor research report.
9. Extraction statistics:
   - Total prompts extracted.
   - Prompts per vulnerability category.
   - Prompts per source product.
   - Attack payload count.
   - Attack-generation prompt count.
   - Evaluation prompt count.
   - Exact and near-duplicate counts.
10. A README explaining how to navigate and use the collection.

## 13. Final Execution Instructions

Work autonomously through the complete research process.

First inspect the current workspace and identify the appropriate location for `Aegis_Prompt_Research`.

Then download the repositories, inspect their contents, extract the relevant materials, normalize the metadata, perform cross-product analysis and generate the final reports.

Do not stop after downloading repositories.

Do not stop after inspecting documentation.

The task is complete only when the actual source prompts, attack examples, evaluator instructions and relevant datasets have been extracted and organized.

If a repository is unavailable, document the failure and continue with the remaining repositories.

At the end, provide a concise completion report containing the number of extracted items, category-wise coverage, repositories successfully inspected and any limitations.

**Final priority: Completeness, source traceability, preservation of original prompts and coverage across all six open-source products.**
