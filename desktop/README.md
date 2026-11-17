# Aegis Desktop (Frontend Workspace)

The **Aegis Desktop Workspace** is a high-performance single-page security assessment client built with React 18, TypeScript, Tailwind CSS, and Vite. It provides an intuitive, real-time interface for target onboarding, Playwright browser calibration, multi-tier reconnaissance profiling, live scan telemetry, and interactive findings inspection.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Technology Stack](#technology-stack)
- [Directory Structure](#directory-structure)
- [Application Flow & Views](#application-flow--views)
  - [1. Dashboard (`Dashboard.tsx`)](#1-dashboard-dashboardtsx)
  - [2. New Assessment & Target Setup (`NewAssessment.tsx`)](#2-new-assessment--target-setup-newassessmenttsx)
  - [3. Live Telemetry (`LiveTelemetry.tsx`)](#3-live-telemetry-livetelemetrytsx)
  - [4. Findings Inspector (`FindingsInspector.tsx`)](#4-findings-inspector-findingsinspectortsx)
  - [5. AI Assistant & RAG Querying](#5-ai-assistant--rag-querying)
- [State Management & Custom Hooks](#state-management--custom-hooks)
  - [Scan Store (`store/scanStore.ts`)](#scan-store-storescanstorets)
  - [Assessment Wizard Hook (`useAssessmentWizard.ts`)](#assessment-wizard-hook-useassessmentwizardts)
  - [WebSocket Telemetry Hook (`useScanSocket.ts`)](#websocket-telemetry-hook-usescansocketts)
- [API Client & Authentication](#api-client--authentication)
- [Installation & Running Locally](#installation--running-locally)
- [Build & Packaging](#build--packaging)
- [Troubleshooting & FAQs](#troubleshooting--faqs)

---

## Overview

The desktop workspace connects directly to the Aegis Engine (`http://127.0.0.1:8765`) over localhost HTTP and WebSocket connections. It abstracts the complexities of automated red-teaming into a guided workflow:
1. **Target Registration**: Add target URL and optional project path.
2. **DOM Calibration**: Auto-detect or interactively click to capture chat selectors.
3. **Reconnaissance & Test Planning**: Inspect corroborated target profile and review the deterministic test plan across all 10 OWASP 2026 categories.
4. **Active Scan & Telemetry**: Watch real-time turn dispatches, token latency, and evaluation verdicts via WebSocket streaming.
5. **Findings & PDF Reporting**: Review prompt/response evidence pairs, risk scores, and download executive PDF reports.

---

## Key Features

- **Guided Assessment Wizard**: Multi-step wizard guiding users through Target Info -> Calibration -> Reconnaissance -> Scope Selection -> Launch.
- **Dual-Mode Calibration**:
  - *Automated Mode*: Inspects DOM heuristics in the target browser to detect input fields, submit buttons, and assistant message bubbles.
  - *Interactive Mode*: Opens a headed browser with an injected click-to-capture overlay for custom web applications.
- **OWASP 2026 Multi-Category Scope Transparency**:
  - Displays all 10 canonical categories (`LLM01` through `LLM10`).
  - Highlights currently executable categories (e.g. `LLM08 Hidden Context Exposure`) while clearly explaining dependencies for categories currently under development.
- **Real-Time Telemetry Stream**: WebSocket-driven live event log showing turn index, category, prompt dispatch, token response latency, and evaluation verdicts.
- **Evidence Inspection**: Structured evidence views showing exact prompts sent, target responses received, highlighted leaks, and actionable remediation steps.
- **Executive PDF Export**: One-click download of styled, tamper-evident audit reports with executive summaries and financial token cost metrics.

---

## Technology Stack

- **Framework**: [React 18](https://react.dev/) + [TypeScript 5](https://www.typescriptlang.org/)
- **Bundler & Dev Server**: [Vite 5](https://vitejs.dev/)
- **Styling**: [Tailwind CSS 3](https://tailwindcss.com/) + PostCSS + Autoprefixer
- **Icons**: [Lucide React](https://lucide.dev/)
- **Markdown Rendering**: [react-markdown](https://github.com/remarkjs/react-markdown) + [remark-gfm](https://github.com/remarkjs/remark-gfm)
- **Packaging (Scaffolded)**: Electron configuration for cross-platform desktop installer distribution.

---

## Directory Structure

```
desktop/
├── src/
│   ├── api/                 # Engine API communication client
│   │   └── client.ts        # Typed fetch client with session bootstrapping & error handling
│   ├── assets/              # Static SVG diagrams and graphics
│   ├── components/          # Reusable UI widgets and layout shells
│   │   ├── ApplicationShell.tsx # Global sidebar, navigation, and system status indicator
│   │   ├── EvidencePair.tsx     # Side-by-side prompt and target response viewer
│   │   ├── LogStream.tsx        # Terminal-style telemetry log streamer
│   │   ├── MarkdownRenderer.tsx # GitHub-flavored markdown renderer
│   │   ├── NewAssessment.tsx    # Multi-step target calibration and launch wizard
│   │   ├── Overview.tsx         # Quick metrics, active targets, and recent scans
│   │   ├── SeverityBadge.tsx    # Styled badge for CRITICAL, HIGH, MEDIUM, LOW, INFO
│   │   └── SourcesView.tsx      # RAG citation and knowledge base source viewer
│   ├── hooks/               # Custom React hooks
│   │   ├── useAssessmentWizard.ts # Multi-step wizard state & validation
│   │   ├── useScanSocket.ts     # Resilient WebSocket connection for telemetry
│   │   └── useScanStatus.ts     # Polling fallback for scan lifecycle state
│   ├── store/               # In-memory application state
│   │   └── scanStore.ts     # Active target, scan progress, and findings state
│   ├── types/               # TypeScript interfaces and data models
│   │   └── index.ts         # Target, TargetProfile, TestPlan, Scan, Finding, TurnRecord
│   ├── views/               # Primary screen views
│   │   ├── Dashboard.tsx    # Main executive dashboard
│   │   ├── FindingsInspector.tsx # Detailed vulnerability inspection and PDF download
│   │   ├── LiveTelemetry.tsx# Real-time scan telemetry and attempt timeline
│   │   ├── ReportViewer.tsx # Delegating PDF report viewer wrapper
│   │   └── TargetConfig.tsx # Target management and selector calibration view
│   ├── App.tsx              # View router and state coordinator
│   ├── index.css            # Tailwind directives and custom component styles
│   └── main.tsx             # React DOM root entry point
├── package.json             # NPM dependencies and scripts
├── postcss.config.js        # PostCSS configuration
├── tailwind.config.js       # Tailwind CSS design system configuration
├── tsconfig.json            # TypeScript compiler configuration
└── vite.config.ts           # Vite development server and proxy configuration
```

---

## Application Flow & Views

### 1. Dashboard (`Dashboard.tsx`)
The entry point of Aegis. Displays:
- **Engine Status Indicator**: Live connectivity badge for the backend engine and local Ollama daemon.
- **Metrics Overview**: Total targets, scans conducted, verified vulnerabilities, and overall risk grade.
- **Recent Scans List**: Historical assessments with status pills (`COMPLETED`, `RUNNING`, `FAILED`, `INTERRUPTED`). Clicking a scan transitions to the **Findings Inspector**.

### 2. New Assessment & Target Setup (`NewAssessment.tsx`)
A structured 4-step wizard:
- **Step 1: Target Definition**: Specify target name, web URL (e.g. `http://127.0.0.1:8001`), and optional local project directory.
- **Step 2: Calibration**:
  - Launch *Auto-Calibration* to let Playwright detect DOM locators.
  - Or launch *Interactive Calibration* to click the input field and send button directly in an overlay browser window.
- **Step 3: Reconnaissance & Planning**:
  - Run passive fingerprinting and active benign probes (with explicit user authorization).
  - Review the corroborated `TargetProfile` (detected AI framework, streaming protocol, vector DB presence).
  - Review the deterministic `TestPlan` generated across all 10 OWASP categories with SHA-256 revision hash.
- **Step 4: Launch Assessment**: Select executable categories (e.g., `LLM08`), configure attempt budget ($N \le 10$), and trigger scan execution.

### 3. Live Telemetry (`LiveTelemetry.tsx`)
Provides real-time visibility during an active scan:
- **Progress Ring & Dials**: Current category, attempt index, and overall completion percentage.
- **Live Event Log (`LogStream.tsx`)**: Streaming terminal events for turn starts, prompts dispatched, response streaming stabilization, and evaluation verdicts.
- **Turn Timeline**: Historical accordion of turns in the active scan showing latency, prompt strategy, and preliminary findings.
- **Control Actions**: Graceful **Stop Scan** button that safely completes the current turn before terminating.

### 4. Findings Inspector (`FindingsInspector.tsx`)
The primary audit analysis view:
- **Executive Summary Bar**: Target grade, CVSS/OWASP severity distribution (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFO`).
- **Findings Table**: List of confirmed vulnerabilities with category, confidence, and timestamp.
- **Detail Pane**:
  - Description and underlying vulnerability mechanism.
  - **Evidence Pair (`EvidencePair.tsx`)**: Exact attack prompt sent alongside the verbatim response received from the target, with leaked tokens or canaries highlighted.
  - **Remediation Advice**: Concrete guidance and code snippets to mitigate the vulnerability.
- **Report Download**: One-click button to download the finalized executive PDF audit report.

### 5. AI Assistant & RAG Querying
Accessible via the sidebar or finding details:
- Allows operators to ask natural language questions grounded in the OWASP Top 10 (2026) knowledge base.
- Uses `POST /api/v1/assistant/chat` to retrieve semantic chunks from ChromaDB and summarize remediation strategies locally using Ollama.

---

## State Management & Custom Hooks

The frontend employs lightweight, idiomatic React state management without heavy global state libraries:

### Scan Store (`store/scanStore.ts`)
Holds application-wide state:
- `activeTarget`: Selected target metadata and calibration selectors.
- `activeScan`: Running or selected scan entity with budget and attempt counters.
- `findings`: Array of confirmed findings for the current scan.
- `turns`: Array of recorded turns for timeline replay.

### Assessment Wizard Hook (`useAssessmentWizard.ts`)
Manages step transitions, input validation, and asynchronous calibration/recon API calls during target onboarding.

### WebSocket Telemetry Hook (`useScanSocket.ts`)
Connects to `ws://127.0.0.1:8765/api/v1/ws/telemetry/{scan_id}`:
- Automatically handles reconnection and ping/pong keepalives.
- Parses incoming telemetry events (`turn_started`, `turn_completed`, `scan_completed`, `scan_failed`) and appends them to the live event log.

---

## API Client & Authentication

The frontend client in `src/api/client.ts` manages all communications with the engine:
- **Base URL**: `http://127.0.0.1:8765/api/v1` (or proxied via Vite).
- **Session Bootstrapping**:
  - Automatically issues a `POST /api/v1/security/bootstrap` request on initialization.
  - Passes `X-Requested-With: XMLHttpRequest` to prove browser origin credibility.
  - Sets up the secure `aegis_session` cookie for subsequent authenticated API requests.
- **Credentials Mode**: All requests set `credentials: 'include'` to allow session cookies across localhost origins.

---

## Installation & Running Locally

### Prerequisites
- **Node.js**: v18.0.0 or higher (Node 20+ recommended; verified on Node v24)
- **NPM**: v9.0.0 or higher
- **Aegis Engine**: Running on `http://127.0.0.1:8765`

### Development Setup
```powershell
# Navigate to desktop directory
cd desktop

# Install dependencies
npm install

# Start Vite development server
npm run dev
```

The workspace will launch at `http://localhost:5173` (or `http://127.0.0.1:3000` when started via `run_aegis.ps1`).

---

## Build & Packaging

To compile the production frontend assets:
```powershell
cd desktop
npm run build
```
This runs TypeScript type checking (`tsc`) and bundles optimized static assets into `desktop/dist/`.

---

## Troubleshooting & FAQs

- **"Engine Offline / Connection Refused"**:
  Ensure the backend engine is running on `http://127.0.0.1:8765`. Check terminal logs for `python main.py` in the `engine/` directory.
- **"Ollama Not Detected"**:
  Ensure your local Ollama daemon is running (`ollama serve`) and the configured models (`qwen2.5:3b` or `llama3.2`, `nomic-embed-text`) are pulled.
- **"Interactive Calibration Browser Doesn't Open"**:
  Verify Playwright Chromium is installed:
  ```powershell
  .\.venv\Scripts\playwright install chromium
  ```
- **"CORS / 401 Unauthorized Errors in Console"**:
  Ensure you are accessing the desktop UI from an allowed origin (`http://localhost:3000`, `http://127.0.0.1:3000`, `http://localhost:5173`, or `http://127.0.0.1:5173`). The engine rejects untrusted origins by design.

