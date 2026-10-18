# Aegis Frontend Design Foundation — Design V1

> **Date:** 2026-10-17
> **Status:** Approved by the user as Design V1; Milestone 1 shell implemented and verified on 2026-10-17. Individual page redesigns await separate approval.
> **Scope:** Frontend presentation and interaction design for the existing React application in `desktop/`.
> **Primary reference:** User-approved AEGIS Design V1 image, supplied as `codex-clipboard-e87b2120-8324-4ef5-896d-d43442c58027.png` in the project conversation. The image contains Dashboard, New Assessment, Live Scan, Results, palette, and interaction panels. It has not been copied into the repository.

## Authority, evidence, and scope

The user has approved this Design V1 foundation and separately authorized Milestone 1 (application shell and design system). This contract does not authorize unsupported features, backend changes, or later implementation milestones.

- **Reference-defined:** Visual relationships and the explicitly printed palette values in Design V1.
- **Provisional:** Measurements, additional tokens, interaction timings, responsive thresholds, and adaptations not explicitly specified by the image. These were accepted with foundation approval as starting values and remain subject to rendered verification; they are not measurements extracted from the image.
- **Existing behavior:** Capabilities confirmed by source inspection, not by a fresh runtime test.
- **Deferred:** Depicted capabilities that cannot currently be delivered honestly through existing integrations.

Use [README.md](README.md), [rules.md](rules.md), [architecture.md](architecture.md), and [design.md](design.md) for shared engineering rules and scanner scope. Use [Status.md](Status.md) and [logs.md](logs.md) for recorded progress; historical test results are not evidence of a new verification run. This document supplements those sources without replacing scanner architecture or API contracts.

The current user instructions govern this redesign: implementation stays in `desktop/`; authorized milestone documentation uses existing `Project-Context/` conventions. Do not modify the backend, agents, orchestrator, Playwright scanning logic, database, risk scoring, or API endpoints. Stop and explain any backend dependency. Work exclusively on `shahzaman`; commits, pushes, and a PR to `main` each require explicit user authorization. Never merge into `main`.

The initial foundation task created only this document. Subsequent authorized implementation milestones update the relevant existing status and append-only log files.

## 1. Product philosophy and visual direction

AEGIS should feel like a calm, precise cybersecurity workbench. Help the analyst answer: what target is selected, what is authorized, what is happening, and what evidence supports the outcome?

- Prioritize readable evidence and predictable workflows over decorative dashboards.
- Follow the reference's graphite-neutral light surfaces, restrained blue accents, compact navigation, fine borders, and clear hierarchy.
- Use graphite primary action buttons; use blue for selection, links, active navigation, and progress.
- Retain the dark activity console as a deliberate local contrast within the light application.
- Use the reference's pale geometric/shield artwork only as subordinate decoration. It must not displace evidence, convey status, or imply broader scan coverage. Asset production is deferred; no asset or dependency is introduced here.
- Use actual profile names and data. The image's names, counts, findings, timestamps, percentages, and durations are illustrative, not production defaults.
- Avoid hacker-style neon, excessive gradients, oversized card grids, and continuous decorative animation. Keep the reference's subtle accent treatment without reproducing its small composite-image text sizes.

The active scanner remains LLM07 System Prompt Leakage using direct disclosure requests against authorized local/private-network web targets. Do not copy claims of full OWASP coverage into the interface.

## 2. Approved graphite-neutral light theme

These hex values are transcribed from the palette labels in the approved image. Token names and application roles are proposed. The illustration's gradients are not a source for additional exact colors.

| Proposed token | Reference value | Intended role |
|---|---|---|
| `--color-canvas` | `#F6F7F9` | Application background |
| `--color-sidebar` | `#EEF1F5` | Navigation surface |
| `--color-surface` | `#FFFFFF` | Cards, panels, fields |
| `--color-text-primary` | `#1F2937` | Primary text; graphite action background |
| `--color-text-secondary` | `#6B7280` | Secondary text, subject to contrast verification |
| `--color-accent` | `#4F6BED` | Selection, progress, links, focus |
| `--color-success` | `#16A34A` | Successful operation or verified readiness |
| `--color-warning` | `#F59E0B` | Caution, degraded conditions |
| `--color-danger` | `#EF4444` | Error and disclosure emphasis |

Keep status colors sparse. Green means an operation completed or a service was checked successfully; it does not mean a completed scan found no vulnerabilities. Never treat an empty response from an unimplemented findings endpoint as a clean security result.

## 3. Semantic tokens and status language

All values in this section are **provisional**. Use semantic aliases in components so themes can change without rewriting individual views.

| Proposed token | Value | Role |
|---|---|---|
| `--color-border-subtle` | `#E2E6EC` | Decorative panel dividers |
| `--color-border-control` | `#7B8798` | Essential input/control boundary; verify contrast |
| `--color-surface-hover` | `#F1F3F7` | Hover on neutral surfaces |
| `--color-accent-subtle` | `#E9EDFF` | Selected navigation/tab background |
| `--color-accent-text` | `#304CC0` | Links and text on light accent surfaces |
| `--color-action-bg` / `--color-action-text` | `#1F2937` / `#FFFFFF` | Primary action |
| `--color-action-hover` | `#111827` | Hover on graphite primary action |
| `--color-focus-ring` | `#4F6BED` | Keyboard focus outline |
| `--color-console-bg` / `--color-console-text` | `#18212B` / `#E5E7EB` | Activity console |
| `--color-console-muted` | `#AAB4C2` | Console timestamp and metadata |
| `--color-success-text` / `--color-success-bg` | `#166534` / `#ECFDF3` | Readable success badge |
| `--color-warning-text` / `--color-warning-bg` | `#92400E` / `#FFFBEB` | Readable warning badge |
| `--color-danger-text` / `--color-danger-bg` | `#B91C1C` / `#FEF2F2` | Readable error/high-severity badge |
| `--color-critical-text` / `--color-critical-bg` | `#991B1B` / `#FEE2E2` | Critical severity, only when supplied |

The bright reference swatches are not automatically suitable for small text or white-text buttons. Use darker semantic text aliases on pale status backgrounds and verify the final combinations. Do not claim contrast compliance from a palette alone.

| Meaning | Treatment | Truth requirement |
|---|---|---|
| Queued | Neutral clock + “Queued” | Backend lifecycle state |
| Running | Blue indicator + “Running” | Confirmed lifecycle, not merely an open socket |
| Completed | Green check + “Completed” | Lifecycle only; outcome displayed separately |
| Stop requested | Neutral/amber indicator + “Stopping…” | Request acknowledged; wait for terminal status |
| Stopped | Neutral stop icon + “Stopped” | Partial evidence remains accessible |
| Failed | Red icon + “Failed” | Preserve available evidence and error context |
| Connecting / disconnected / stale | Explicit text, neutral/amber | Connection condition is separate from scan outcome |
| Disclosure signal | Red emphasis + “Potential disclosure detected” | Existing turn verdict; do not invent severity |
| No disclosure in a turn | Neutral text + “No disclosure detected in this response” | Not an overall safety guarantee |
| Unavailable / not tested | Neutral badge and explanation | Never substitute zero, green, or “Passed” |

Severity badges must spell out their level. High/critical may share a red family; medium uses amber; low/info use neutral or blue. Never calculate a new severity, grade, or risk score in the frontend.

## 4. Typography, spacing, borders, and elevation

All dimensions and font choices below are **provisional**, because the reference is a scaled multi-screen composition rather than a measured layout specification.

- Retain the existing `Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif` stack. Inter is not bundled; system fallback is acceptable. Adding a font asset requires a separate decision, not an automatic network import.
- Use a 16px root with rem-based typography. Page titles: 24px/32px, weight 600–700; section titles: 18px/26px, weight 600; body and controls: 14px/22px; metadata: 12px/18px. Do not use 8–10px text for essential information.
- Use tabular numerals for counters and durations. Use `ui-monospace, SFMono-Regular, Consolas, monospace` at 13px/20px for logs, IDs, and technical evidence. Never force all prose into monospace.
- Spacing scale: 4, 8, 12, 16, 24, 32, 48px. Typical card padding: 20–24px; card/grid gaps: 16–24px; label-to-control gap: 8px.
- Radius scale: 6px compact controls, 8px cards/inputs/buttons, 12px large overlay panels; pill radius only for status badges and avatars.
- Borders: 1px; selected controls add a clear accent outline or indicator without changing layout dimensions.
- Elevation: flat cards by default; subtle panel shadow `0 1px 2px rgba(15,23,42,0.04)`; overlay shadow `0 12px 32px rgba(15,23,42,0.12)`. Do not apply floating shadows to every card.
- Controls: 40px visual height on desktop with adequate spacing; 44px touch targets where practical. Focus rings must remain visible outside borders.

## 5. Sidebar, top navigation, and application layout

**Reference-defined:** Persistent left navigation, AEGIS mark, blue selected item, bottom workspace identity, restrained header/breadcrumbs, and spacious white content panels.

**Provisional layout:** 224px sidebar, 64px header, 24–32px content gutters, and a centered content region capped at 1440px within the remaining space. Wide data/evidence views may use the available content width. Keep the header and primary actions visible without covering focused content. Allow sidebar scrolling on short windows.

Proposed navigation maps existing behavior to the reference:

| Label | Destination and constraint |
|---|---|
| Overview | Existing dashboard |
| New Assessment | Existing registration/calibration/configuration workflow |
| Live Scan | Preserve access while a scan is selected; do not lose this entry merely because the reference omits it |
| Scan History | Existing browser-local request history; retain search and disclose its scope |
| Results / Findings | Deferred or explicitly unavailable until an honest results view is implemented against existing data |
| Reports | Unavailable while report generation is a stub |
| Assistant | Existing local setup guidance, explicitly not a model chat |
| Settings | Existing local profile/preferences; preserve display-name editing |

Default proposal: omit unsupported navigation/actions rather than add dead buttons. If retaining an unavailable reference item for orientation, show a clear “Unavailable” label and explanation; do not render a working-looking link. This adaptation requires approval.

Breadcrumbs should identify assessment context and lead only to implemented destinations. On child assessment screens, highlight the relevant parent instead of marking unrelated sections active. Use the actual local profile name; do not hardcode “Shahzaman”.

The reference's global search and notification bell are deferred: there is no implemented global findings search or notification center. Preserve the current history search with accurate scope. Engine and Ollama indicators use actual health responses; Playwright readiness is unknown unless backed by verified information. The health endpoint does not establish model availability or Playwright readiness.

## 6. Dashboard (Overview)

**Purpose:** Orient the analyst and provide a clear path to a new assessment or existing activity.

**Reference structure:** Greeting, compact metric row, recent-assessments table, system-status panel, quick actions, and an optional right-side illustration. The primary action is “New assessment”.

- Use the greeting and compact metrics without copying sample counts or growth claims.
- Current safe metrics include locally recorded assessment requests and registered targets. Label local counts “In this browser profile”; local history is capped and is not an engine-wide total.
- Running/completed counts require fresh status reconciliation. Cached history cannot support an unqualified real-time count. Show “Last known” with freshness context or omit these metrics until reliable.
- Findings totals and severity distributions are unavailable. Use an explicit unavailable state or substitute a useful supported metric; do not show zero vulnerabilities by default.
- Recent assessments should preserve target name, category, timestamp, and known status. Distinguish actual attempts from configured budget. Opening a historical run is a proposed frontend refinement, not an existing capability to claim complete.
- Show engine/Ollama health with checking, connected, offline, and retry states. Avoid a permanently green Playwright status.
- Quick actions should be real: New assessment, Scan history, Setup guidance. Defer “Generate report”.
- Decorative shield art belongs in a secondary area only at wide widths. Its copy must describe current LLM07 scope, not all-category coverage.

Required states: initial loading, no assessments, populated history, unavailable/stale data, and engine offline. Keep cached history readable offline with clear labeling.

## 7. New Assessment

**Purpose:** Guide an authorized target from selection through calibration to a valid scan request.

**Reference structure:** Four-step rail beside a focused form panel; Back/Next actions and final review. Proposed rail width: 200px; form width: up to 760px. Both are **provisional**.

1. **Target:** Choose an existing target or enter a name and local/private-network URL. Preserve URL normalization and backend validation messages. Web is the supported connector; desktop is unavailable. Explain authorization and obtain the existing explicit consent before any calibration can open the target.
2. **Interface calibration:** Preserve Automatic calibration and Click to calibrate. Manual mode captures input, then Send/Enter; the response selector is detected automatically. Preserve opening, capture progress, selector saving, completed, failed, and timeout feedback, plus existing selector reuse. Do not reproduce the older documentation's three-click description.
3. **Test scope:** LLM07 is runnable; other OWASP categories are clearly not enabled. Retain the current 1–10 attempt budget and existing payload contract. This redesign does not raise backend budgets or expand assessment scope.
4. **Review & run:** Summarize target URL/name, category, budget, calibration readiness, and authorization. Submit exactly one scan request through the existing integration. The final action reads “Run scan” or “Start assessment”, with a pending state until acknowledged.

Consent placement is a **provisional adaptation**: the reference's final review step must not postpone authorization until after calibration. Keep consent visible before target interaction and visible again in the review summary. It must never be preselected; revocation blocks subsequent target interaction and submission.

Changing a URL or target must invalidate mismatched calibration and require an explicit authorization check for that target. Changing steps must not lose entered values, start duplicate registrations, or re-trigger calibration automatically. Guard against late responses applying selectors to a different target. Preserve user-visible errors near the affected field and an accessible summary when needed.

Step navigation organizes existing operations; it does not invent server-side workflow states. Back remains available when safe, and active-operation restrictions explain why navigation is temporarily constrained. Reuse existing calibration polling/timeouts initially. Leaving a view is not a backend cancellation request.

Required states: blank form, registered target, invalid URL, absent authorization, calibration in progress, saved selectors, calibration failure, unsupported mode/category, pending submission, and request failure with retained form data.

## 8. Live Scan

**Purpose:** Show reliable progress, exact prompt/response evidence, and an accessible stop action.

**Reference structure:** Assessment breadcrumb/title, lifecycle badge, progress bar, content tabs, dark activity console, and a smaller current-activity panel. Proposed wide layout: flexible evidence region plus 280px side panel; dimensions are **provisional**.

- Preserve status polling, WebSocket telemetry, saved-turn replay, deduplication, transcript rendering, and stop requests.
- Show `current_attempt / budget` as attempt progress, not percentage certainty, elapsed-work completion, or risk. An attempt can still be awaiting its response. Early completion may legitimately end below 100% of the budget; do not fabricate remaining turns to fill the bar.
- Scan lifecycle and individual turn status are distinct. A turn's `success`, `timeout`, or `error` must not replace the scan lifecycle badge. Map existing events safely in the frontend without changing backend messages.
- “Stop” requests graceful stopping. After acknowledgment, show “Stopping…” until the backend confirms its terminal state; preserve partial evidence and surface failures. Do not add Pause: no pause/resume contract exists.
- Activity entries use actual events and timestamps where available. Missing data is labeled unavailable, not filled with plausible log lines.
- Initial tab proposal: Activity and Requests & Responses; add Evidence only when it presents real turn verdicts. Do not introduce an “Agent Reasoning” tab: current verdict rationale is an evaluation explanation, not an internal reasoning stream.
- Current-activity text must come from supported telemetry. “Awaiting response or evaluation” is preferable to claiming a precise agent stage without an event. Do not fabricate estimated remaining time.
- Keep exact prompt/response text selectable, safely escaped, and readable with wrapping. Any later collapse/copy control must preserve the original full evidence. Clearly distinguish empty response, pending response, and fetch failure.
- Proposed event console order is chronological with auto-follow only while the reader remains at the end. Offer “Jump to latest” when they scroll away. Existing transcript order is newest-first; changing its default is provisional and must not lose turns or reset selection.
- Connection loss is not scan failure. Show disconnected/stale state while preserving last-known data and status polling. A redesigned shell must not silently stop observation when navigating between views or tabs; subscription/state refactoring requires workflow verification.

Required states: queued, running, waiting for first event, awaiting response/evaluation, stopping, stopped, completed, failed, and disconnected. A scan that stops or fails before its first turn must not retain an indefinite “waiting” spinner.

## 9. Results (Findings)

**Purpose:** Explain the actual outcome and allow evidence inspection without overstating coverage.

**Reference structure:** Outcome heading, overview/findings/evidence/timeline tabs, compact summary cards, severity badges, and expandable finding rows. The composition is approved visual direction; its depicted data and actions are not implemented functionality.

Current constraints: `src/views/FindingsInspector.tsx` and `ReportViewer.tsx` are placeholders. The findings API returns an empty list regardless of persisted findings, and the PDF service writes sample stub bytes. The current client does expose scan status and persisted turns with verdict details. These limitations were inspected, not changed.

- A future frontend-only results view may present real scan status, replayed turns, and available verdict rationale/confidence. Label these as turn-level evaluation results, not a complete findings inventory.
- Do not turn an empty findings response into “No vulnerabilities found”. Explain that aggregate findings retrieval is unavailable while retaining access to actual transcript evidence.
- Do not infer severity from confidence or assign the reference's High/Medium labels. Display severity/remediation only when supplied by a supported, verified source.
- Distinguish completed, stopped, failed, and incomplete-data outcomes. Completed does not mean secure; stopped/failed scans retain partial results.
- Show actual returned prompt/response counts with precise labels. Duration requires reliable timestamps; omit it when unavailable.
- Future finding rows may contain supplied title/category/severity, rationale, linked prompt and response, and supplied remediation. Expand with a keyboard-operable control and preserve raw evidence.
- Evidence/timeline views can use existing turn data, but must disclose incomplete event history. Do not imply a complete audit trail from the bounded live event buffer.
- Full PDF reports and export actions are deferred. Even a local transcript export is a separate feature decision, not authorization inferred from the reference.
- Other OWASP categories remain “Not tested”; no all-category compliance score or clean bill of health is implied.

Required states: available turn evidence, no turns yet, partial evidence, unavailable findings, loading, fetch error with retry, and unknown outcome. Backend-dependent reporting or findings completion must be raised with the user, not implemented automatically.

## 10. Reusable component principles

Build a small set of composable primitives in existing frontend directories when implementation is approved: application shell, navigation item, page heading/breadcrumbs, button/icon button, form field, panel, metric card, status/severity badge, stepper, tabs, progress indicator, evidence block, and feedback states.

- Retain React, TypeScript, Vite, and existing Lucide icons. No additional UI, state, animation, or chart dependency is assumed.
- Separate presentation from API calls and lifecycle logic. Preserve backend field names, nullability, and existing payloads when restructuring.
- Share tokens and component variants instead of duplicating page-specific colors and dimensions. Prefer explicit variants to large configuration objects.
- Use native controls and semantic HTML where practical. Do not require a library to reproduce a simple button, panel, or badge.
- Keep scan lifecycle state separate from view selection and local preferences. Validate incoming state before treating it as a known status; unknown values receive a neutral fallback.
- Keep true loading, empty, offline, unavailable, and error states distinct. Never replace live integrations with demonstration data.
- Preserve existing history search, local profile editing, and assistant guidance even though this document concentrates on four reference screens.

## 11. Hover, focus, micro-interactions, and animation

**Reference-defined:** Slight button darkening/lift, sidebar background transitions, subtle running-status pulse, and a smooth switch transition. A pictured switch does not authorize a new preference or dark-mode control.

**Provisional timings:** 120–160ms hover/pressed feedback; 160–200ms tabs/panels; 180–220ms progress-width transition; a restrained 1.8s status pulse. Use `ease-out` for short transitions. Prefer opacity and transform; avoid layout animation and `transition: all`.

- Primary hover darkens graphite; optional lift is at most 1px on hover-capable devices. Pressed state removes lift. Secondary controls change border/background with no layout shift.
- Keyboard focus uses a 2px ring with 2px offset, independent of hover. Selected navigation has a persistent accent background and accessible current-state indication.
- Busy controls retain a readable label and stable width, prevent duplicate requests, and announce progress. Errors remain visible until resolved or explicitly dismissed.
- Step transitions are brief and do not delay validation, requests, or navigation. Move focus to the new heading or validation error as appropriate.
- Live pulse indicates activity only while confirmed running. Stop it in terminal states. Never animate numeric counts toward invented values.
- Under `prefers-reduced-motion: reduce`, remove lift, pulse, smooth scrolling, and nonessential transitions. Static labels/icons still communicate all states.
- Copy feedback, if later implemented, appears only after clipboard success; provide an error on failure. Do not make critical outcome messages disappear as short-lived toasts.

## 12. Responsive behavior and accessibility

The following viewport thresholds and sizes are **provisional**. Preserve the reference's desktop hierarchy while adapting to actual window size and zoom.

| Available width | Proposed behavior |
|---|---|
| 1280px and wider | Full sidebar, multi-column dashboard, optional illustration, live side panel |
| 1024–1279px | Full sidebar where content fits; remove illustration first; metrics wrap into two columns |
| 768–1023px | Collapsible navigation; single-column major content; step rail becomes compact step navigation |
| Below 768px | Accessible navigation drawer; stacked cards and forms; full-width primary actions; compact header |

Remove the current fixed 780px page minimum during the responsive implementation phase. Target reflow at 320 CSS px and usable text at 200% zoom; inspect desktop layouts through 1440px and beyond. Dense tables may have a labeled, keyboard-accessible local scroll region, but the entire application must not require horizontal scrolling. Long URLs, IDs, and evidence must wrap or have an explicit full-content view.

Accessibility acceptance requirements:

- Semantic landmarks, one clear page heading, logical heading order, skip navigation, and predictable tab order.
- Programmatic labels, field descriptions, associated errors, and text instructions for authorization/calibration. Required state is not communicated through color alone.
- Keyboard access for all actions. Tabs and steppers use the appropriate keyboard behavior and current/selected state. Dialogs/drawers manage focus, Escape dismissal where safe, and focus return.
- Normal text contrast of at least 4.5:1; large text and essential non-text controls at least 3:1. Verify actual rendered combinations, including console content, hover, and focus states.
- At least 24px interactive targets with spacing; target 44px for touch and important actions. Icon-only buttons have accessible names; decorative icons/art are hidden from assistive technology.
- Progress has an accessible label and meaningful current value. Use polite announcements for lifecycle changes and immediate announcements for actionable errors; do not announce every polling tick or transcript token.
- Keep user scroll position and focus stable during telemetry updates. Avoid trapping readers in an auto-scrolling console.
- Show status through text and icon as well as color. Distinguish unavailable results from tested-negative results.

These are design requirements, not a claim of accessibility certification. Verify keyboard use, zoom/reflow, contrast, and assistive-technology output during implementation.

## 13. Future dark-mode compatibility

Light mode is the approved implementation direction. Dark mode is a future capability, not part of this task and not an implied toggle to ship now.

- Keep color, border, elevation, and console roles behind semantic tokens. Future theme selectors can override them without changing component behavior.
- Avoid component-level hardcoded white/black and assumptions that every pale surface means success. Keep status meaning identical across themes.
- Use current-color icons and theme-aware decoration; do not invert screenshots or evidence content.
- Treat the dark console as its own semantic surface in both themes. Recheck its hierarchy against a future dark canvas.
- Review all text, borders, focus rings, disabled states, charts if any, and artwork before enabling a dark palette. No dark hex values are approved here.
- Theme persistence/system preference behavior is deferred until dark mode is explicitly requested.

## 14. Compatibility and verification gate

Source baseline: [App.tsx](../desktop/src/App.tsx), [index.css](../desktop/src/index.css), [API client](../desktop/src/api/client.ts), [telemetry hook](../desktop/src/hooks/useScanSocket.ts), [types](../desktop/src/types/index.ts), and [package scripts](../desktop/package.json). Active views currently live within `App.tsx`; the separate view files are largely placeholders. Styling is primarily global CSS with partial color variables. Tailwind is declared, but its processing setup must be verified before relying on it for new components.

Before every implementation task, identify exact intended files and risks. Preserve and verify the relevant parts of this matrix after significant changes:

| Workflow | Required evidence |
|---|---|
| Target registration/selection | Correct payload, normalization, validation errors, saved-target selection |
| Authorization | No calibration or scan submission without explicit consent; target changes cannot reuse inappropriate consent silently |
| Calibration | Automatic and two-click flows, progress polling, saving selectors, errors, reuse, and stale-result protection |
| Configuration/start | LLM07 and budget preserved; one request per submit; correct target and pending/error states |
| Live observation | Status polling, actual telemetry, saved-turn replay, no lost/duplicated evidence, stable navigation |
| Stop | Stop request sent; acknowledgment distinguished from terminal state; partial evidence retained |
| History/profile/assistant | Existing local persistence/search, profile editing, and truthful local guidance retained |
| Presentation | Reference comparison, responsive layouts, keyboard/focus, zoom, contrast, reduced motion |

Run `npm run build` from `desktop/` after significant frontend changes; the current script runs TypeScript and Vite. No frontend lint/test scripts are currently declared, so do not invent passing results for them. Use available browser verification for affected workflows and report missing services, unavailable targets, tooling limits, or untested paths. Keep fixture/demo content separate from production behavior. A successful build alone does not verify scanner integration.

No build or live scanner test is required to validate this documentation-only change; no runtime compatibility or project gate is newly claimed passed. Later verified milestones follow existing documentation conventions. The user alone decides when a PR is appropriate.

## 15. Approved foundation decisions (page implementation deferred)

1. Provisional typography, spacing, widths, radii, additional semantic colors, elevation, and motion timings; retain reference palette values while using readable darker status text aliases.
2. Four-step assessment structure with authorization before calibration, rather than waiting until final review; confirm target-specific authorization handling.
3. Hide unsupported actions by default, with explicitly labeled unavailable entries only where useful. Defer Pause, Agent Reasoning, global search/notifications, PDF/export, and unsupported scan modes.
4. Adapt Results to actual transcript/verdict data until aggregate findings/reporting are supported; do not reproduce sample severity counts or security claims.
5. Responsive thresholds, compact navigation behavior, and event-console ordering/auto-follow rules.
6. Keep decorative shield artwork optional and defer its asset implementation; use the existing font stack without a new font dependency.

Approval of this foundation selects the proposed design contract. It does not itself authorize backend changes, dependencies, Git operations, or implementation beyond the next explicitly requested task.


## 16. Milestone 1 implementation record — 2026-10-17

- Implemented the semantic light-theme palette, readable status text, spacing/radius/elevation tokens, shared panel/button/heading styling, and existing system font stack. No font or package dependency was added.
- Extracted only sidebar/header presentation into `desktop/src/components/ApplicationShell.tsx`; `App.tsx` still owns page selection, profile, history, scan state and every existing scanner handler. Page component implementations, API client, and telemetry hook remain unchanged.
- Adopted the provisional 224px sidebar, 64px header, 24–32px desktop gutters, 16px narrow gutters, 8px radii, and 140ms subtle transitions. Below 1024px a native modal navigation drawer supplies keyboard isolation, Escape/backdrop dismissal, scroll locking and focus restoration. Desktop resizing closes the drawer. The shell remains within 320px–1440px tested viewports.
- Retained existing destinations including conditional Live scan and profile via Settings/avatar. Help opens the existing local assistant. Removed the nonfunctional shortcut/switch decoration; Playwright availability now reads "Not checked" because health data does not establish it. No global search, notifications, findings/report destinations, theme toggle or other unsupported action was added.
- Added skip-to-content, named navigation, active-page semantics, visible focus rings, reduced-motion handling, and real health-driven status labels. Future themes can override shell semantic tokens; page-specific legacy colors remain for later migration. Dark mode is not implemented.
- Verification: production build passed; Chromium navigation/header actions, 320/390/768/1024/1440px shell bounds, modal keyboard isolation/Escape/backdrop/resize, scroll restoration, same-view form preservation, authorization guard, profile saving, assistant replies and reduced-motion checks passed. Desktop and compact drawer screenshots were visually inspected.
- Browser-only API/WebSocket fixtures verified registration/URL normalization, automatic and completed click-calibration UI, authorized submission payload, conditional Live scan, status polling, telemetry, saved transcript replay, history filtering, returning to the active scan, and stopping. These fixtures were confined to isolated browser tests, not production files or stored engine data.
- Limits: engine offline; no live target calibration, real scanning/Ollama/stop integration, Electron runtime, screen-reader audit, full contrast/zoom audit, or other browser engines verified. Legacy page compositions can scroll horizontally inside the content area at narrow widths; page reflow and remaining page-specific accessibility work are deferred. No backend gate is newly claimed passed. Stop here pending user review of Milestone 1.


### Milestone 1 sidebar refinement — 2026-10-17

Desktop sidebar section gaps now use 16px, with no duplicate top padding on the bottom section. Direct sidebar children keep their natural heights; `overflow-y: auto` remains enabled, so genuinely short windows still scroll without clipping services or workspace identity. Compact drawer spacing and all page content remain unchanged. Chromium measured no overflow at 1366x650 with an extra Live scan-sized navigation item, or 1366x600 with normal navigation; 400/500px-tall windows scroll and retain bottom access. The extra item was a browser DOM layout fixture, not a production navigation change. Build passed; actual user window dimensions, Electron and other browsers were not verified.


### Sidebar scrollbar visibility correction — 2026-10-17

The earlier spacing refinement did not address the requested scrollbar appearance. The desktop `.sidebar` now uses `scrollbar-width: none` plus a scoped `::-webkit-scrollbar` fallback for Chromium/WebKit; native overflow scrolling stays enabled. No width, spacing, page content, main scrollbar or compact drawer styles changed in this correction. Chromium screenshots visually verified at 1366x768 and 1366x400, including the scrolled bottom sections. Wheel and keyboard scrolling, status/profile reachability, main scrolling and compact drawer behavior passed. Physical touchpad input and Firefox/WebKit runtimes were not tested; no input handlers were changed.


## 17. Milestone 2 — Dashboard implementation (2026-10-17)

Implemented Panel 1's compact header, metric row, Recent Assessments beside System Health, and supported Quick Actions below. Decorative artwork remains optional/deferred. The Milestone 1 shell and shared stylesheet are unchanged. Overview presentation now lives in `desktop/src/components/Overview.tsx` with scoped `overview.css`; App passes existing state, profile and refresh/navigation callbacks.

Metrics show capped browser-local request count, last-known completed count, latest request date, and unavailable aggregate findings. No live running count, severity, trend, or security verdict is inferred. Replaced the registered-target snapshot metric to avoid presenting a pending/stale target fetch as an authoritative count. Recent rows show actual saved target/category/request timestamp and explicitly last-known status. Only the currently selected scan has an Open action; View all opens existing history, without inventing historical result retrieval.

Health distinguishes checking, engine offline, Ollama unavailable while engine is offline, disconnected Ollama, connected services, and unchecked Playwright; model readiness is not asserted. Refresh reuses the existing callback with a local pending guard. Quick Actions open existing New Assessment, History and Assistant views. Removed the unsupported desktop-assessment promotional action, while retaining the existing target-mode selector on New Assessment. No report/export action added.

Responsive metrics wrap into two columns, content panels stack, and quick actions stack at narrower widths. The evidence table retains a named keyboard-focusable local horizontal scroll region; dashboard/body bounds remain within 320–1440px tested widths. Scoped hover/focus treatments and global reduced-motion support remain compatible.

Verified: production build; Chromium empty/offline, connected/disconnected, populated history and initial loading states; local counts/last-known labels; Quick Actions, settings, header start, View all, health refresh and selected-scan Open via isolated fixtures; screenshots visually inspected at desktop and 390px width. Other page implementations and scanner handlers compared unchanged against Git. Limits: fixture checks are not live engine/calibration/scan validation; Electron, other browser engines, physical touch devices and full assistive-technology/contrast audits not tested. Milestone 2 awaits visual review; no Git publication authorized.


### Milestone 2 visual correction — 2026-10-17 (awaiting visual approval)

The initial implementation was not visually approved. Comparing a 1280x800 Chromium capture with Panel 1 showed full-width generic metrics, oversized service rows/empty space, Quick Actions below the viewport, and a missing right-side context composition. Corrected Overview to a compact working column plus a 230px security illustration/context rail at wide desktop widths. Four smaller metric cards sit above Recent Assessments and a 166px health panel; three compact Quick Actions sit immediately beneath. Removed the oversized eyebrow/header hierarchy, tightened panel/table typography and spacing, reduced empty-state height, and used smaller unboxed metric icons. Added decorative CSS planes and existing Lucide icons for a shield illustration; no image dependency or external asset added.

Health explanation text remains accessible and available as hover descriptions, while concise real state labels remain visible. Existing refresh/settings and selected-scan/history navigation are preserved. Responsive layouts hide the decorative rail below 1190px and stack the working panels below 650px. The approved application shell is unchanged.

Visual checks: inspected before/after empty/offline and populated fixture screenshots at 1280x800 plus a 390px capture. Both desktop states now show the complete primary dashboard including Quick Actions. Build passes; navigation/refresh checks and no-page-overflow checks at 320/390/768/1024/1280/1440px pass. Remaining intentional differences: approved Milestone 1 shell, real profile/local history metrics, unavailable aggregate findings, unchecked Playwright, setup guidance instead of unsupported report generation, and simplified decorative illustration rather than an exact reproduction. User visual approval is still pending.


### Full-size Dashboard reference refinement — 2026-10-18 (visual approval pending)

The user supplied `AEGIS AI Security Dashboard.png` as the full-size visual authority for this refinement. Earlier Milestone 2 versions remain unapproved. Overview now follows its larger greeting/supporting text, four horizontal icon-led metric cards, five-column Recent Assessments table (Name, Category, Status, Started, Findings), adjacent System Status with visible descriptions, dedicated layered shield artwork, and full-width bottom Quick Actions. Table headers remain visible in the empty state; its outlined New assessment action is retained. Decorative blue geometry/waves are scoped to the dashboard. Consolidated dashboard CSS replaces accumulated overrides.

Added a single local decorative SVG (`desktop/src/assets/security-dashboard.svg`) with layered translucent panels, blue shield, floating evidence cards and an isometric tile. It approximates the reference artwork without adding dependencies or remote assets. Milestone 1 shell and shared stylesheet remain unchanged. Quick Actions keep supported scan/history/setup guidance destinations; selected-scan navigation is on the matching target name so the Findings column can accurately show unavailable. Started displays the saved request timestamp, clarified in the populated-table note.

Total scans reflects capped local history; Running and Completed are explicitly last-known local counts, not reconciled live engine totals. Vulnerabilities and row findings remain unavailable. Service labels reflect actual health inputs; disconnected Ollama and unchecked Playwright are not shown online. Greeting uses the current local hour and existing profile name.

Verification: repeated Chromium captures at 1440x900, visually inspected empty/offline, populated and final disconnected-service fixtures, plus mobile screenshot; adjusted service density and artwork height after comparison so the full dashboard fits 1440x900. Build passed. Existing action destinations, refresh requests, selected-scan target link and six responsive widths (320–1440px) passed; table retains local keyboard-focusable overflow. SVG import typing failure corrected through a bundled asset URL without config changes. No real scan/backend integration, Electron, other browser or full accessibility certification claimed. The preserved shell, honest data/capability substitutions and recreated vector illustration are remaining reference differences. Await user visual approval.


### Milestone 3 — New Assessment wizard — 2026-10-18 (approval pending)

Milestones 1 and 2 were approved and published by the user before this work; historical pending-approval entries above remain as history. The user supplied the full-size New Assessment reference (`codex-clipboard-6b91c016-86bf-4f19-af99-3f8b724dbd74.png`) as visual authority for Milestone 3.

Implemented a vertical four-step desktop rail next to one white form panel, restrained geometric decoration, graphite buttons, selected web card and visibly unavailable desktop card. Below 800px the rail becomes four compact columns; form controls stack at narrow widths. Existing shell and Overview remain unchanged. Step headings receive focus on navigation; labels, alert/status feedback and native keyboard controls remain available.

The four steps are Target Configuration, Interface Calibration, Test Scope, and Review & Run. Unlike the single reference image, Step 1 contains explicit target-specific authorization, while both calibration actions live in Step 2 as requested. Existing target selection reuses saved selectors; editing its name or URL becomes a new target draft, resets consent and discards mismatched selectors. Back/Next retains draft data. New targets register only when calibration is explicitly requested; the returned target is retained even if list refresh is unavailable. Moving to Step 2 alone performs no registration or browser interaction.

Automatic and manual calibration retain the existing API payloads, 90-second manual session, 300ms polls, 95-second client deadline, and up to 20 additional 250ms polls for saved configuration. Manual selection remains input then Send/Enter, with automatic response detection. In-flight wizard navigation is disabled; leaving the page invalidates late calibration results and stops further frontend polling, but is not backend cancellation. Recalibration clears old readiness until the new attempt succeeds. LLM07 is the only category, budget remains 1–10/default 10. Run scan sends the existing payload once per in-flight submission and hands an acknowledged scan to the existing App handler; backend errors retain the form. No backend idempotency contract is added.

Verification: final `npm run build` passed (pre-existing Vite CJS warning). Isolated Chromium fixtures passed validation/consent gates, normalized new-target registration, existing target selector reuse, automatic/manual success, registration/automatic/manual/submission errors, timeout handling using an accelerated test clock, step persistence, target/URL invalidation, budget keyboard controls, exact scan payload, duplicate-click prevention, delayed acknowledgment and Live Scan navigation, locked navigation while calibrating and late-result rejection after leaving. All four steps passed body/main overflow checks at 320/390/768/1024/1440px with no JavaScript runtime exceptions. Four 1440x900 viewport screenshots (full-page capture where content exceeds viewport) and a mobile capture were inspected. Step 1 spacing was refined after comparison; other steps use the same visual language. Test scripts/screenshots are temporary artifacts outside the repository.

Limitations: fixtures verify frontend contracts, not real engine/Playwright integration. No real calibration, scan, Electron, non-Chromium or assistive-technology audit was performed. Leaving the page resets the draft as before; it does not cancel backend operations. Existing APIs provide no cancellation/idempotency feature, so requests already sent cannot be withdrawn. Longer calibration details and short windows scroll normally. The preserved shell, explicit authorization, disabled desktop mode, and separate calibration step are intentional reference adaptations. Await user visual and functional approval; no commit/push/PR.


### Milestone 3 finalization and visual approval — 2026-10-18

Milestone 3 implementation is complete and all four New Assessment wizard screens are visually approved by the user. This supersedes the pending-approval status above. The user authorized committing this milestone and pushing only to origin/shahzaman.

Finalization verification: frontend `npm run build` passed; the existing Vite CJS deprecation warning remains. Chromium fixture checks passed for registration/selection, consent and URL validation, automatic/manual calibration, errors and accelerated timeout handling, selector reuse/invalidation, step persistence, budget keyboard input, exact submission payload and duplicate prevention, and acknowledgment-driven Live Scan navigation. All four steps passed responsive overflow checks at five widths (320–1440px). Dashboard empty state, health refresh, Quick Actions, settings/history and desktop/compact navigation passed additional fixture checks with no runtime errors. Corrected one invalid UTF-8 separator byte in the registered-target fallback option; no behavior or visual design changes.

Live Playwright calibration and end-to-end scanning remain untested. Full integration testing is deferred until all frontend screens are complete. Fixture success is not live scanner verification. No backend/API/scanner changes, dependencies, or run_aegis.ps1 changes are included. No merge, PR, or Milestone 4 work is authorized by this finalization.


### Frontend PR preparation checkpoint — 2026-10-18

This checkpoint supersedes historical pending-approval statements without removing the history.

| Frontend milestone | Current state | Implementation commit |
|---|---|---|
| 1. Application Shell and Sidebar | Implemented and visually approved | `75d4c57` |
| 2. Dashboard / Overview | Implemented and visually approved | `7113e39` |
| 3. New Assessment Wizard (four steps) | Implemented and visually approved | `29610de` |

Live Scan and Results redesigns are **not yet implemented**. The pre-existing Live Scan functionality remains available; it is not the Design V1 redesign. No Milestone 4 work is included.

Verification for this checkpoint: `npm run build` in desktop passed (TypeScript and Vite; existing CJS deprecation warning). No frontend test script or checked-in frontend test suite is configured. Re-ran the existing temporary isolated Chromium fixture harness: target registration/selection, consent and URL checks, auto/manual calibration success/failure, accelerated timeout, selector reuse/invalidation, step persistence, keyboard budget, exact submission payload, duplicate guard, acknowledgment-driven Live Scan navigation, stale-result rejection, and 20 step/viewport overflow combinations passed with no JavaScript runtime errors. The fixture harness is outside the repository and is not a committed automated test suite.

Live Playwright calibration and full LLM07 end-to-end testing remain pending for the redesigned frontend. Full integration testing is deferred until all frontend screens are complete. No backend acceptance gate is newly passed by these fixture results. Historical backend verification entries do not establish integration acceptance of this redesign.

Scope review: shahzaman was active with a clean working tree and no untracked files at entry. Milestone 3 is already committed; this checkpoint adds documentation only. The reviewed branch diff against local main is limited to desktop frontend files and Project-Context documents. Backend functionality, scanner logic and API contracts are preserved; no changes to the API client, engine, agents or run_aegis.ps1 are included. No main modification, merge or PR creation. Push only to origin/shahzaman; PR creation still requires explicit authorization.


### Milestone 4 — Live Scan implementation — 2026-10-18 (visual approval pending)

The supplied `codex-clipboard-21208e1e-388e-4e44-a6eb-4710e927ffa6.png` is this milestone's primary visual reference. Implemented a white execution card with breadcrumb, target heading, status, Stop and refresh controls, thin attempt-budget progress, horizontal tabs, dark monospaced console and adjacent Current Step panel. Three lower cards contain actual test attempts, target context and available metrics. The approved shell/header/sidebar and previous page layouts remain unchanged. Narrow layouts stack panels and allow local horizontal tab scrolling; the activity console and transcript remain keyboard-focusable scrolling regions. CSS is scoped to Live Scan and uses existing semantic tokens with local dark-console colors.

Four tabs follow the latest explicit request: Live Activity, Agent Reasoning, Requests & Responses, Evidence. This supersedes earlier guidance to omit unsupported reasoning navigation: its panel explicitly states that no reasoning stream exists and links to actual turn evidence. The console displays only backend events, preserves supplied timestamps, deduplicates replay, follows new output until the user scrolls away, and offers Jump to latest. Requests and evidence use saved/live turns merged by attempt; empty responses remain distinct from missing responses. Text is rendered as text, not executable markup.

Current Step reflects actual scan/turn events. Attack Generation, Execution and Analysis remain neutral informational rows because separate phase timing/state is not exposed. No success checkmarks or active phase are inferred. The reference's Pause and ETA are omitted. Findings generated and scan duration show unavailable. Response averages exclude missing/zero latency; potential disclosures show their evaluated-turn denominator. Test cases use reported prompt numbers/strategies, with Recorded or In progress/Incomplete labels rather than invented names or security outcomes. The progress bar represents reported attempts divided by budget, not successful completion.

Existing sources: `GET /api/v1/scans/{scan_id}`, `GET /api/v1/scans/{scan_id}/turns`, `POST /api/v1/scans/{scan_id}/stop`, and `ws://127.0.0.1:8765/api/v1/ws/telemetry/{scan_id}`. Target context comes from the wizard handoff or the existing target list; no API contract changed. Monitoring stays mounted in App across navigation, serializes polls and refreshes, stops automatic polling/reconnect after a confirmed terminal state, and protects scan lifecycle from per-turn status strings. Stop acknowledgment remains Stopping until terminal confirmation. Session storage retains only the selected scan/target metadata so refresh never silently selects a different scan. If browser storage is unavailable, current-session monitoring continues but reload recovery is unavailable.

Build and temporary Chromium fixture verification are recorded in Status.md and logs.md. Captures at a 1440x900 viewport and mobile were visually inspected; spacing was tightened after comparison. The preserved application shell, fewer real events, neutral phase rows, honest unavailable metrics and natural vertical scrolling are intentional differences from the illustrative reference. No fabricated production data or dependencies were added. Live engine integration, real Playwright calibration and full LLM07 scanning are still pending; fixture results are not live acceptance. Await visual approval. Results redesign has not started.


### Milestone 4 finalization and visual approval — 2026-10-18

Milestone 4 is implemented and visually approved by the user, with the two requested final refinements completed. This supersedes the pending-approval entries above while preserving their history. The supported refresh control now displays **Refresh status**, retains the accessible name **Refresh scan status**, and marks its decorative icon hidden from assistive technology. Current Step uses slightly increased spacing above/below the current activity and between phase rows; its structure and neutral phase semantics are unchanged.

Fresh verification: `npm run build` passed (existing Vite CJS deprecation warning). The temporary Chromium Live Scan regression suite passed status/turn separation, deduplication/reconnect, transcript/evidence, keyboard tabs, same-scan navigation/reload, stop acknowledgment/error/retry/duplicate prevention, terminal polling shutdown, stale-response protection, offline/404 retention, empty responses, zero latency, serial refresh, console scrolling, compact navigation and five responsive widths. The existing wizard fixture suite passed, including scan handoff and 20 step/viewport combinations. Desktop/mobile captures were visually inspected after refinements; no runtime exceptions observed. Dashboard and New Assessment component/style files, the shell, API client, backend and run_aegis.ps1 are unchanged in this milestone's diff. No unrelated files or generated artifacts are included.

Live Playwright calibration, actual engine telemetry/reconnection/stopping and full LLM07 end-to-end scanning remain untested. Full integration testing remains deferred until all frontend screens are complete; fixtures do not establish live acceptance. Results/Milestone 5 has not started. The user authorized committing Milestone 4 and pushing only to origin/shahzaman; no main modification, PR or merge is part of this finalization.
