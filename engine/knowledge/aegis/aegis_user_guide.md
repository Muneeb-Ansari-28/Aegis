# Aegis User Guide and Operation

## Target Configuration and Authorization

Before assessing any target, users must configure the target application in the Aegis Desktop UI:
- Enter the target URL (e.g. a local or staging LLM chat endpoint).
- Specify the target name and environment.
- Confirm testing authorization: Aegis enforces that assessments are only conducted against systems owned or explicitly authorized in writing.

## Playwright Browser Calibration

To interact reliably with web chatbots, Aegis uses Playwright browser automation. Calibration detects the interactive DOM elements needed to send messages and read responses.

Two calibration workflows are supported:
1. **Interactive Click Calibration (2-step)**:
   - Step 1: Click the chat input area in the visible browser window.
   - Step 2: Click the Enter / Send button in the visible browser window.
   - Aegis records the selectors, verifies readiness, and detects the response area automatically.
2. **Automatic Calibration**:
   - Aegis inspects the DOM using heuristic selector matching for common input areas (`textarea`, `input[type="text"]`, `contenteditable`) and submit buttons (`button[type="submit"]`, send icons).

## Starting and Monitoring Scans

Once calibrated, users can launch an assessment scan:
- **Scan Queue**: Scans transition from `QUEUED` to `RUNNING`.
- **Live Turns**: The Live Scan view displays prompt submissions, target replies, response latency in milliseconds, and real-time evaluator verdicts.
- **Budget Control**: The scan executes up to the configured budget ($N \le 10$ attempts per category) or until manually stopped via the stop button.

## Report Generation and Export

After a scan finishes (`COMPLETED` or `STOPPED`):
- Detailed findings can be reviewed in the Results Inspector.
- Users can generate an executive PDF report via the engine (`ReportService`).
- Reports include an executive summary, security grade (0–100), risk band, and verified findings with turn transcripts.
