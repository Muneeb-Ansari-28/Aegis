"""Automatic and user guided calibration for local web chat targets."""
import asyncio
import logging
import time
from typing import Awaitable, Callable, Dict, Optional

from playwright.async_api import async_playwright

from app.adapters.playwright_web import (
    CANDIDATE_RESPONSE_SELECTORS,
    PlaywrightWebAdapter,
    open_chat_surface,
)
from app.core.errors import TargetCalibrationError
from app.schemas.target import TargetCalibrationConfig

logger = logging.getLogger(__name__)
ProgressCallback = Callable[[int], Awaitable[None]]

CALIBRATION_OVERLAY_SCRIPT = r"""
(() => {
  if (window.__aegis_calibrating) return;
  window.__aegis_calibrating = true;
  window.__aegis_result = { input_selector: null, submit_selector: null, step: 0 };

  const banner = document.createElement('div');
  banner.id = '__aegis_calibration_banner';
  Object.assign(banner.style, {
    position: 'fixed', top: '12px', right: '12px', zIndex: '2147483647',
    padding: '14px 18px', background: '#fff', color: '#234c81',
    fontFamily: 'system-ui, sans-serif', fontSize: '14px', fontWeight: '600',
    borderRadius: '6px', border: '2px solid #557fb8',
    boxShadow: '0 3px 14px rgba(20, 44, 76, .2)', maxWidth: '360px'
  });
  banner.textContent = 'Step 1 of 2 — Open the chat if needed, then click its input area';
  document.body.appendChild(banner);

  function targetFor(event) {
    const node = event.target instanceof Element ? event.target : null;
    if (!node || node.closest('[id^="__aegis_"]')) return null;
    return node.closest('textarea, input:not([type="hidden"]), [contenteditable="true"], [role="textbox"], button, [role="button"], input[type="submit"]');
  }

  // Disabled chat send controls cannot receive a calibration click until text is
  // entered. Enable only disabled submit buttons paired with a text composer;
  // capture runs in the browser's capture phase and prevents any real submission.
  document.querySelectorAll('button:disabled, [role="button"][aria-disabled="true"]').forEach(button => {
    const form = button.closest('form');
    if (!form) return;
    const composer = form.querySelector('textarea, [contenteditable="true"], [role="textbox"]')
      || Array.from(form.querySelectorAll('input[type="text"]')).find(input =>
        /chat|message|prompt|ask|question/i.test(
          [input.id, input.name, input.placeholder, input.getAttribute('aria-label')].join(' ')
        )
      );
    if (!composer) return;
    button.__aegis_was_disabled = true;
    button.disabled = false;
    button.removeAttribute('aria-disabled');
  });

  function uniqueSelector(element) {
    const tag = element.tagName.toLowerCase();
    if (element.id) {
      const idSelector = '#' + CSS.escape(element.id);
      if (document.querySelectorAll(idSelector).length === 1) return idSelector;
    }
    for (const attribute of ['name', 'placeholder', 'aria-label', 'data-testid']) {
      const value = element.getAttribute(attribute);
      if (!value) continue;
      const selector = `${tag}[${attribute}="${CSS.escape(value)}"]`;
      if (document.querySelectorAll(selector).length === 1) return selector;
    }
    const path = [];
    let current = element;
    while (current && current !== document.body) {
      let part = current.tagName.toLowerCase();
      const siblings = current.parentElement
        ? Array.from(current.parentElement.children).filter(child => child.tagName === current.tagName)
        : [];
      if (siblings.length > 1) part += `:nth-of-type(${siblings.indexOf(current) + 1})`;
      path.unshift(part);
      const candidate = path.join(' > ');
      if (document.querySelectorAll(candidate).length === 1) return candidate;
      current = current.parentElement;
    }
    return path.join(' > ');
  }

  document.addEventListener('mouseover', event => {
    const element = targetFor(event);
    if (element) element.style.outline = '2px solid #4b78b8';
  }, true);
  document.addEventListener('mouseout', event => {
    const element = targetFor(event);
    if (element) element.style.outline = '';
  }, true);
  document.addEventListener('click', event => {
    const element = targetFor(event);
    if (!element) return;
    const isExpected = window.__aegis_result.step === 0
      ? element.matches('textarea, input:not([type="hidden"]):not([type="submit"]):not([type="button"]), [contenteditable="true"], [role="textbox"]')
      : element.matches('button, [role="button"], input[type="submit"], input[type="button"]');
    if (!isExpected) {
      banner.textContent = window.__aegis_result.step === 0
        ? 'Open the chatbot if it is closed, then click its input area'
        : 'Click the chat Enter / Send button to finish';
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    element.style.outline = '';

    if (window.__aegis_result.step === 0) {
      if (!element.matches('textarea, input:not([type="hidden"]), [contenteditable="true"], [role="textbox"]')) {
        banner.textContent = 'Select the chatbot text input to continue';
        return;
      }
      window.__aegis_result.input_selector = uniqueSelector(element);
      window.__aegis_result.step = 1;
      banner.textContent = 'Step 2 of 2 — Click the Enter / Send button';
      return;
    }

    if (window.__aegis_result.step === 1) {
      if (!element.matches('button, [role="button"], input[type="submit"], input[type="button"]')) {
        banner.textContent = 'Select the chat Enter / Send button to finish';
        return;
      }
      window.__aegis_result.submit_selector = uniqueSelector(element);
      window.__aegis_result.step = 2;
      banner.textContent = 'Calibration complete — returning to Aegis';
      banner.style.borderColor = '#41835b';
      banner.style.color = '#326b49';
    }
  }, true);
})();
"""


class WebCalibration:
    """Detect or capture selectors for a local web chatbot."""

    async def auto_calibrate(
        self, target_url: str, headless: bool = True
    ) -> TargetCalibrationConfig:
        """Use Playwright heuristics to find visible chat controls on the target."""
        adapter = PlaywrightWebAdapter(target_url=target_url, headless=headless)
        try:
            await adapter.open()
            if adapter.page:
                await self._wait_for_client_render(adapter.page)
                await self._open_chat_surface(adapter.page)
                detected = await adapter.detect_chat_interface()
                adapter.selectors.update({key: value for key, value in detected.items() if value})
            detected = adapter.selectors
            if not detected.get("input_selector"):
                raise TargetCalibrationError("No visible chatbot input was detected.")
            if not detected.get("submit_selector"):
                raise TargetCalibrationError(
                    "No visible Enter or Send button was detected. Use click calibration."
                )
            response_selector = await self._find_response_selector(adapter.page)
            if not response_selector:
                raise TargetCalibrationError(
                    "No assistant response area was detected on this page."
                )
            return TargetCalibrationConfig(
                input_selector=detected["input_selector"],
                submit_selector=detected["submit_selector"],
                response_selector=response_selector,
                wait_timeout_ms=15000,
            )
        finally:
            if not headless:
                await asyncio.sleep(2)
            await adapter.close()

    async def calibrate_interactive(
        self,
        target_url: str,
        timeout_sec: int = 90,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> TargetCalibrationConfig:
        """Open the target, capture its input and send controls, and detect replies."""
        logger.info("Starting interactive calibration for local target %s", target_url)
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=False)
            context = await browser.new_context(no_viewport=True)
            page = await context.new_page()
            try:
                await page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
                await page.bring_to_front()
                await self._wait_for_client_render(page)
                await page.evaluate(CALIBRATION_OVERLAY_SCRIPT)
                if progress_callback:
                    await progress_callback(0)
                started = time.monotonic()
                last_reported_step = 0
                state: Dict[str, object] = {}
                while time.monotonic() - started < timeout_sec:
                    await asyncio.sleep(0.2)
                    state = await page.evaluate("() => window.__aegis_result || ({})")
                    step = int(state.get("step", 0))
                    if progress_callback and step != last_reported_step:
                        await progress_callback(step)
                        last_reported_step = step
                    if step == 2:
                        break
                if state.get("step") != 2:
                    raise TargetCalibrationError(
                        "Calibration timed out. Select the input area and Enter/Send button in the target browser."
                    )

                input_selector = str(state.get("input_selector") or "")
                submit_selector = str(state.get("submit_selector") or "")
                response_selector = await self._find_response_selector(page)
                if not response_selector:
                    raise TargetCalibrationError(
                        "Input and send controls were selected, but Playwright could not detect the response area."
                    )
                return TargetCalibrationConfig(
                    input_selector=input_selector,
                    submit_selector=submit_selector,
                    response_selector=response_selector,
                    wait_timeout_ms=15000,
                )
            except TargetCalibrationError:
                raise
            except Exception as exc:
                logger.exception("Interactive calibration failed")
                raise TargetCalibrationError(f"Could not calibrate local target: {exc}") from exc
            finally:
                await browser.close()

    @staticmethod
    async def _wait_for_client_render(page) -> None:
        """Allow client-rendered chat controls to appear before selector detection."""
        try:
            await page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            pass
        await page.wait_for_timeout(350)

    @staticmethod
    async def _open_chat_surface(page) -> bool:
        """Use the same bounded chat readiness check as the scan connector."""
        return await open_chat_surface(page)

    @staticmethod
    async def _find_response_selector(page) -> Optional[str]:
        """Return the first visible response selector recognized by the connector."""
        for selector in CANDIDATE_RESPONSE_SELECTORS:
            try:
                locator = page.locator(selector).last
                if await locator.count() and await locator.is_visible():
                    return selector
            except Exception:
                continue
        # Chat UIs often render an empty placeholder as the final log child before
        # the first message. The selector is still valid once the first reply arrives.
        log = page.locator("[role='log']").first
        try:
            if await log.count() and await log.is_visible():
                return "[role='log'] > *:last-child"
        except Exception:
            pass
        return None
