"""Playwright Web Connector for Web Chatbots."""
import asyncio
import logging
import time
import uuid
from typing import Optional, Dict, Any, Union, List

from playwright.async_api import (
    async_playwright,
    Playwright,
    Browser,
    BrowserContext,
    Page,
    Locator,
    TimeoutError as PlaywrightTimeoutError,
    expect,
)

from app.adapters.base import BaseAdapter
from app.schemas.turn_record import TurnRecord
from app.schemas.target import TargetCalibrationConfig
from app.core.config import get_settings
from app.core.errors import ConnectorTimeout, TargetCalibrationError

logger = logging.getLogger(__name__)

CANDIDATE_INPUT_SELECTORS: List[str] = [
    "#assistant-question",
    "textarea[aria-label*='ask' i]",
    "#chat-input",
    "textarea#chat-input",
    "input#chat-input",
    "textarea[placeholder*='message' i]",
    "textarea[placeholder*='chat' i]",
    "textarea[placeholder*='ask' i]",
    "textarea[placeholder*='prompt' i]",
    "textarea[placeholder*='type' i]",
    "textarea[aria-label*='chat' i]",
    "textarea[aria-label*='message' i]",
    "textarea[name='message']",
    "textarea[name='prompt']",
    "textarea",
    "[contenteditable='true'][role='textbox']",
    "[contenteditable='true']",
    "input[type='text'][placeholder*='message' i]",
    "input[type='text'][placeholder*='chat' i]",
    "input[type='text'][placeholder*='ask' i]",
    "input[type='text'][aria-label*='chat' i]",
    "input[type='text'][aria-label*='message' i]",
    "input[type='text']",
]

CANDIDATE_SUBMIT_SELECTORS: List[str] = [
    "button[aria-label='Send question']",
    "button[aria-label*='send question' i]",
    "button#send",
    "#send",
    "button[type='submit']",
    "button[aria-label*='send' i]",
    "button[title*='send' i]",
    "button:has-text('Send')",
    "button:has-text('Submit')",
    "button:has(svg)",
    "input[type='submit']",
]

CANDIDATE_RESPONSE_SELECTORS: List[str] = [
    ".assistant-message.assistant",
    ".assistant-thread .assistant-message.assistant",
    ".assistant-message.assistant:last-child",
    ".assistant-thread .assistant-message.assistant:last-child",
    ".chat-message.assistant:last-child",
    "[data-message-author-role='assistant']:last-child",
    ".assistant-message:last-child",
    ".bot-message:last-child",
    ".chat-message:last-child",
    "#chat-box > .chat-message.assistant:last-child",
    "#chat-box > *:last-child",
    "[role='log'] > *:last-child",
    ".prose:last-child",
    "#chat-box",
]


async def open_chat_surface(
    page: Page, input_selector: Optional[str] = None, timeout_ms: int = 5000,
) -> bool:
    """Wait for a usable composer, clicking a supported launcher at most once.

    Calibration and scanning share this bounded readiness check. A configured
    selector remains authoritative; generic candidates are used only without it.
    Failures include the opening/actionability error instead of being swallowed.
    """
    deadline = time.monotonic() + timeout_ms / 1000

    def remaining() -> int:
        """Keep render, click and composer checks within one readiness budget."""
        return max(1, int((deadline - time.monotonic()) * 1000))

    async def find_input() -> Locator:
        """Prefer chat composers; a launcher takes priority over generic search."""
        if input_selector:
            return page.locator(input_selector).first
        specific = [selector for selector in CANDIDATE_INPUT_SELECTORS
                    if selector not in {"textarea", "input[type='text']"}]
        for selector in specific:
            locator = page.locator(selector).first
            if await locator.is_visible():
                return locator
        for selector in specific:
            locator = page.locator(selector).first
            if await locator.count():
                return locator
        # A lazy-mounted chat has no composer yet. Wait for it after opening,
        # rather than treating the website's search box as a visible chatbot.
        candidates = (specific + ["textarea"] if await launchers.is_visible()
                      else CANDIDATE_INPUT_SELECTORS)
        return page.locator(
            ", ".join(f"{selector}:visible" for selector in candidates)
        ).first

    launchers = page.locator(
        "button.assistant-launch:visible, "
        "button[aria-label*='open assistant' i]:visible, "
        "button[aria-label*='open chat' i]:visible, "
        "button:has-text('Ask Aegis'):visible, "
        "button:has-text('Open chat'):visible"
    ).first
    clicked = False
    try:
        inputs = await find_input()
        if not await inputs.is_visible():
            # Wait for client rendering without a sleep or repeated blind clicks.
            await inputs.and_(page.locator(":visible")).or_(launchers).first.wait_for(
                state="visible", timeout=remaining(),
            )
            inputs = await find_input()
            if not await inputs.is_visible():
                await launchers.click(timeout=remaining())
                clicked = True
                inputs = await find_input()
        await inputs.wait_for(state="visible", timeout=remaining())
        await expect(inputs).to_be_editable(timeout=remaining())
        await inputs.click(trial=True, timeout=remaining())
        return clicked
    except Exception as exc:
        raise TargetCalibrationError(
            f"Chat input is not ready ({input_selector or 'auto-detected input'}); "
            f"launcher {'clicked' if clicked else 'not clicked'}. "
            f"Check the input selector and supported chat launcher. {exc}"
        ) from exc


class PlaywrightWebAdapter(BaseAdapter):
    """
    Playwright Web Connector.
    Navigates to target web chatbots, performs DOM interface auto-detection or consumes
    calibrated selectors, enters prompts, triggers submission (click or Enter), and polls
    until the streaming assistant response stabilizes. Produces a Unified Turn Record.
    """

    def __init__(
        self,
        target_url: str,
        selectors: Optional[Union[dict, TargetCalibrationConfig]] = None,
        headless: Optional[bool] = None,
        browser_timeout_ms: Optional[int] = None,
        settle_timeout_ms: int = 800,
        profile_dir: Optional[str] = None,
    ):
        self.target_url = target_url
        if isinstance(selectors, TargetCalibrationConfig):
            self.selectors: Dict[str, Any] = selectors.model_dump()
        elif isinstance(selectors, dict):
            self.selectors = dict(selectors)
        else:
            self.selectors = {}

        settings = get_settings()
        self.headless: bool = settings.PLAYWRIGHT_HEADLESS if headless is None else headless
        self.browser_timeout_ms: int = (
            settings.BROWSER_TIMEOUT_MS if browser_timeout_ms is None else browser_timeout_ms
        )
        self.settle_timeout_ms: int = settle_timeout_ms
        self.profile_dir: Optional[str] = profile_dir

        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def open(self) -> None:
        """Launch browser, establish context and navigate to the target page."""
        if self.page is not None:
            return

        logger.info(f"Launching Playwright (headless={self.headless}) for target {self.target_url}")
        self._playwright = await async_playwright().start()

        if self.profile_dir:
            logger.info(f"Using persistent profile directory: {self.profile_dir}")
            self._context = await self._playwright.chromium.launch_persistent_context(
                user_data_dir=self.profile_dir,
                headless=self.headless,
                timeout=self.browser_timeout_ms,
                no_viewport=True if not self.headless else None,
            )
            self.page = self._context.pages[0] if self._context.pages else await self._context.new_page()
        else:
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
                timeout=self.browser_timeout_ms,
            )
            self._context = await self._browser.new_context(
                viewport={"width": 1280, "height": 800} if self.headless else None,
                no_viewport=True if not self.headless else None,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Aegis/0.1.0",
            )
            self.page = await self._context.new_page()

        try:
            await self.page.goto(self.target_url, wait_until="domcontentloaded", timeout=self.browser_timeout_ms)
        except Exception as e:
            logger.error(f"Failed to navigate to target {self.target_url}: {e}")
            await self.close()
            raise TargetCalibrationError(f"Could not open target URL {self.target_url}: {e}")
        if not self.headless:
            await self.page.bring_to_front()

        # If required selectors are not provided, run automatic chat detection
        if not self.selectors.get("input_selector") or not self.selectors.get("response_selector"):
            detected = await self.detect_chat_interface()
            self.selectors.update({k: v for k, v in detected.items() if v and not self.selectors.get(k)})

    async def detect_chat_interface(self) -> Dict[str, Optional[str]]:
        """
        Heuristic scanner that identifies chat input, submit button, and response area on the page.
        """
        if not self.page:
            raise TargetCalibrationError("Browser page is not initialized.")

        detected: Dict[str, Optional[str]] = {
            "input_selector": None,
            "submit_selector": None,
            "response_selector": None,
        }

        # 1. Detect Chat Input
        for selector in CANDIDATE_INPUT_SELECTORS:
            try:
                locator = self.page.locator(selector).first
                if await locator.count() > 0 and await locator.is_visible():
                    detected["input_selector"] = selector
                    logger.info(f"Auto-detected chat input: {selector}")
                    break
            except Exception:
                continue

        # 2. Detect Submit Control
        for selector in CANDIDATE_SUBMIT_SELECTORS:
            try:
                locator = self.page.locator(selector).first
                if await locator.count() > 0 and await locator.is_visible():
                    detected["submit_selector"] = selector
                    logger.info(f"Auto-detected submit button: {selector}")
                    break
            except Exception:
                continue

        # 3. Detect Response Element
        for selector in CANDIDATE_RESPONSE_SELECTORS:
            try:
                locator = self.page.locator(selector).first
                if await locator.count() > 0:
                    detected["response_selector"] = selector
                    logger.info(f"Auto-detected response container: {selector}")
                    break
            except Exception:
                continue

        if not detected["response_selector"]:
            # Fallback for dynamic containers
            detected["response_selector"] = "#chat-box > *:last-child"

        return detected

    async def _wait_for_stable_response(
        self,
        response_selector: str,
        initial_text: str,
        max_timeout_ms: int,
        fallback_baselines: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Polls response element until text stops changing (streaming completed).

        The calibrated selector always wins while its text changes, but a
        calibrated selector can match a permanently empty placeholder (for
        example a trailing ``*:last-child`` spacer sitting after every
        assistant message). While the primary selector stays stuck at its
        baseline, this probe checks the known response candidates and switches
        to the first one whose text grew, so replies rendered in sibling
        containers are still captured deterministically.
        """
        assert self.page is not None
        start_time = time.time()
        timeout_sec = max_timeout_ms / 1000.0
        stability_interval = 0.2
        required_stable_checks = max(1, int((self.settle_timeout_ms / 1000.0) / stability_interval))

        fallbacks = dict(fallback_baselines or {})
        fallbacks.pop(response_selector, None)
        active_selector = response_selector
        active_initial = initial_text
        current_stable_checks = 0
        last_seen_text = active_initial
        checks = 0
        probe_every_checks = 5  # probe candidate selectors once per second

        while (time.time() - start_time) < timeout_sec:
            await asyncio.sleep(stability_interval)
            checks += 1
            try:
                locator = self.page.locator(active_selector).last
                if await locator.count() == 0:
                    text = ""
                else:
                    text = (await locator.inner_text()).strip()

                primary_stuck = active_selector == response_selector and (
                    not text or text == active_initial
                )
                if primary_stuck and fallbacks and checks % probe_every_checks == 0:
                    for candidate, baseline in fallbacks.items():
                        try:
                            candidate_locator = self.page.locator(candidate).last
                            if await candidate_locator.count() == 0:
                                continue
                            candidate_text = (await candidate_locator.inner_text()).strip()
                        except Exception:
                            continue
                        if candidate_text and candidate_text != baseline:
                            logger.info(
                                "Response selector %s produced no change; capturing replies via %s",
                                response_selector,
                                candidate,
                            )
                            active_selector = candidate
                            active_initial = baseline
                            last_seen_text = baseline
                            current_stable_checks = 0
                            text = candidate_text
                            break

                # If text is empty or unchanged from pre-prompt state, keep waiting
                if not text or text == active_initial:
                    continue

                if text == last_seen_text:
                    current_stable_checks += 1
                    if current_stable_checks >= required_stable_checks:
                        return text
                else:
                    last_seen_text = text
                    current_stable_checks = 0

            except Exception:
                continue

        if last_seen_text and last_seen_text != active_initial:
            return last_seen_text

        raise ConnectorTimeout(f"Timed out after {max_timeout_ms}ms waiting for response to stabilize at {response_selector}")

    async def send_prompt(
        self,
        prompt: str,
        attempt: int,
        scan_id: str = "scan-default",
        strategy: Optional[str] = None,
    ) -> TurnRecord:
        """
        Inserts prompt into input box, submits via button or Enter key, captures settled response,
        and returns a normalized Unified Turn Record.
        """
        if not self.page:
            await self.open()

        assert self.page is not None
        start_time = time.time()
        turn_id = str(uuid.uuid4())

        input_sel = self.selectors.get("input_selector")
        submit_sel = self.selectors.get("submit_selector")
        resp_sel = self.selectors.get("response_selector") or "#chat-box > *:last-child"

        try:
            await open_chat_surface(
                self.page, input_sel, timeout_ms=min(self.browser_timeout_ms, 5000),
            )
        except TargetCalibrationError as exc:
            logger.error("Could not prepare chat input: %s", exc)
            return TurnRecord(
                turn_id=turn_id, scan_id=scan_id, turn_index=attempt,
                prompt=prompt, response=f"[CONNECTOR_ERROR] {exc}", status="error",
                latency_ms=int((time.time() - start_time) * 1000), strategy=strategy,
                metadata={"error": str(exc), "target_url": self.target_url},
            )

        if not input_sel:
            detected = await self.detect_chat_interface()
            input_sel = detected.get("input_selector")
            if not input_sel:
                return TurnRecord(
                    turn_id=turn_id,
                    scan_id=scan_id,
                    turn_index=attempt,
                    prompt=prompt,
                    response="[CONNECTOR_ERROR] No chat input element found on the target page.",
                    status="error",
                    latency_ms=0,
                    strategy=strategy,
                    metadata={"error": "Missing input_selector", "target_url": self.target_url},
                )
            self.selectors["input_selector"] = input_sel
            if not submit_sel:
                submit_sel = detected.get("submit_selector")
                self.selectors["submit_selector"] = submit_sel

        # Snapshot baseline text before submission
        baseline_text = ""
        try:
            resp_locator = self.page.locator(resp_sel).last
            if await resp_locator.count() > 0:
                baseline_text = (await resp_locator.inner_text()).strip()
        except Exception:
            baseline_text = ""
        # Known response candidates are baselined too, so the wait loop can
        # detect a reply that renders outside a stale calibrated placeholder.
        fallback_baselines: Dict[str, str] = {}
        for candidate in CANDIDATE_RESPONSE_SELECTORS:
            if candidate == resp_sel:
                continue
            try:
                candidate_locator = self.page.locator(candidate).last
                if await candidate_locator.count() > 0:
                    fallback_baselines[candidate] = (await candidate_locator.inner_text()).strip()
                else:
                    fallback_baselines[candidate] = ""
            except Exception:
                fallback_baselines[candidate] = ""

        # Locate input element, clear and enter prompt
        try:
            input_locator = self.page.locator(input_sel).first
            await input_locator.wait_for(state="visible", timeout=self.browser_timeout_ms)
            await input_locator.click(timeout=self.browser_timeout_ms)
            await input_locator.fill(prompt, timeout=self.browser_timeout_ms)
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Failed to enter prompt into {input_sel}: {e}")
            return TurnRecord(
                turn_id=turn_id,
                scan_id=scan_id,
                turn_index=attempt,
                prompt=prompt,
                response=f"[CONNECTOR_ERROR] Failed to type prompt: {e}",
                status="error",
                latency_ms=latency_ms,
                strategy=strategy,
                metadata={"error": str(e), "target_url": self.target_url},
            )

        # Submit via button click or Enter key
        try:
            submitted = False
            if submit_sel:
                submit_locator = self.page.locator(submit_sel).first
                if await submit_locator.count() > 0 and await submit_locator.is_visible():
                    await submit_locator.click()
                    submitted = True

            if not submitted:
                # Default to pressing Enter key
                await input_locator.press("Enter")
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Failed to submit prompt: {e}")
            return TurnRecord(
                turn_id=turn_id,
                scan_id=scan_id,
                turn_index=attempt,
                prompt=prompt,
                response=f"[CONNECTOR_ERROR] Failed to submit prompt: {e}",
                status="error",
                latency_ms=latency_ms,
                strategy=strategy,
                metadata={"error": str(e), "target_url": self.target_url},
            )

        # Wait for and capture streaming/stabilized assistant response
        timeout_ms = self.selectors.get("wait_timeout_ms", 15000)
        try:
            captured_text = await self._wait_for_stable_response(
                response_selector=resp_sel,
                initial_text=baseline_text,
                max_timeout_ms=timeout_ms,
                fallback_baselines=fallback_baselines,
            )
            latency_ms = int((time.time() - start_time) * 1000)
            return TurnRecord(
                turn_id=turn_id,
                scan_id=scan_id,
                turn_index=attempt,
                prompt=prompt,
                response=captured_text,
                status="success",
                latency_ms=latency_ms,
                strategy=strategy,
                metadata={
                    "target_url": self.target_url,
                    "input_selector": input_sel,
                    "submit_selector": submit_sel,
                    "response_selector": resp_sel,
                },
            )
        except ConnectorTimeout as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.warning(f"Response timeout for prompt attempt {attempt}: {e}")
            return TurnRecord(
                turn_id=turn_id,
                scan_id=scan_id,
                turn_index=attempt,
                prompt=prompt,
                response="[CONNECTOR_TIMEOUT] Target did not produce a stable response within timeout limit.",
                status="timeout",
                latency_ms=latency_ms,
                strategy=strategy,
                metadata={"error": str(e), "target_url": self.target_url},
            )
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Unexpected error capturing response: {e}")
            return TurnRecord(
                turn_id=turn_id,
                scan_id=scan_id,
                turn_index=attempt,
                prompt=prompt,
                response=f"[CONNECTOR_ERROR] Failed capturing response: {e}",
                status="error",
                latency_ms=latency_ms,
                strategy=strategy,
                metadata={"error": str(e), "target_url": self.target_url},
            )

    async def reset_session(self) -> None:
        """Reload page or re-initialize chat session."""
        if self.page:
            logger.info("Reloading target page to reset session state.")
            await self.page.reload(wait_until="domcontentloaded")

    async def close(self) -> None:
        """Clean up page, browser context, and Playwright driver."""
        if self.page:
            try:
                await self.page.close()
            except Exception:
                pass
            self.page = None

        if self._context:
            try:
                await self._context.close()
            except Exception:
                pass
            self._context = None

        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None

        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
        logger.info("Playwright session terminated.")
