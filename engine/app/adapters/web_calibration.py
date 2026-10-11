"""Visible-Browser Selector Capture and Interactive Calibration."""
import asyncio
import logging
from typing import Dict, Any, Optional
from playwright.async_api import async_playwright
from app.schemas.target import TargetCalibrationConfig
from app.adapters.playwright_web import PlaywrightWebAdapter
from app.core.errors import TargetCalibrationError

logger = logging.getLogger(__name__)

CALIBRATION_OVERLAY_SCRIPT = """
(() => {
  if (window.__aegis_calibrating) return;
  window.__aegis_calibrating = true;
  window.__aegis_result = {
    input_selector: null,
    submit_selector: null,
    response_selector: null,
    step: 0
  };

  const banner = document.createElement('div');
  banner.id = '__aegis_calibration_banner';
  banner.style.position = 'fixed';
  banner.style.top = '12px';
  banner.style.right = '12px';
  banner.style.zIndex = '9999999';
  banner.style.padding = '14px 20px';
  banner.style.background = '#1e293b';
  banner.style.color = '#38bdf8';
  banner.style.fontFamily = 'monospace';
  banner.style.fontSize = '14px';
  banner.style.fontWeight = 'bold';
  banner.style.borderRadius = '8px';
  banner.style.boxShadow = '0 4px 15px rgba(0,0,0,0.4)';
  banner.style.border = '2px solid #0284c7';
  banner.style.maxWidth = '380px';
  banner.style.cursor = 'default';
  banner.innerText = 'Step 1/3: Click on the Chat Input box';
  document.body.appendChild(banner);

  function getUniqueSelector(el) {
    if (!el || el === document.body) return '';
    if (el.id) return '#' + CSS.escape(el.id);
    if (el.getAttribute('name')) return `${el.tagName.toLowerCase()}[name="${CSS.escape(el.getAttribute('name'))}"]`;
    if (el.getAttribute('placeholder')) return `${el.tagName.toLowerCase()}[placeholder*="${CSS.escape(el.getAttribute('placeholder').slice(0, 15))}"]`;
    if (el.getAttribute('aria-label')) return `[aria-label*="${CSS.escape(el.getAttribute('aria-label'))}"]`;
    if (el.className && typeof el.className === 'string') {
      const classes = el.className.trim().split(/\\s+/).filter(c => !c.startsWith('__aegis')).slice(0, 2);
      if (classes.length) return el.tagName.toLowerCase() + '.' + classes.join('.');
    }
    return el.tagName.toLowerCase();
  }

  document.addEventListener('mouseover', (e) => {
    if (e.target.id && e.target.id.startsWith('__aegis')) return;
    e.target.style.outline = '2px dashed #0284c7';
  }, true);

  document.addEventListener('mouseout', (e) => {
    if (e.target.id && e.target.id.startsWith('__aegis')) return;
    e.target.style.outline = '';
  }, true);

  document.addEventListener('click', (e) => {
    if (e.target.id && e.target.id.startsWith('__aegis')) return;
    e.preventDefault();
    e.stopPropagation();
    e.target.style.outline = '';

    const selector = getUniqueSelector(e.target);

    if (window.__aegis_result.step === 0) {
      window.__aegis_result.input_selector = selector;
      window.__aegis_result.step = 1;
      banner.style.borderColor = '#10b981';
      banner.style.color = '#34d399';
      banner.innerText = 'Step 2/3: Click the Send Button (or wait 5s to skip)';
    } else if (window.__aegis_result.step === 1) {
      window.__aegis_result.submit_selector = selector;
      window.__aegis_result.step = 2;
      banner.style.borderColor = '#f59e0b';
      banner.style.color = '#fbbf24';
      banner.innerText = 'Step 3/3: Click on an Assistant Response bubble';
    } else if (window.__aegis_result.step === 2) {
      window.__aegis_result.response_selector = selector;
      window.__aegis_result.step = 3;
      banner.style.borderColor = '#22c55e';
      banner.style.color = '#4ade80';
      banner.innerText = '✓ Calibration complete! Closing browser...';
    }
  }, true);
})();
"""


class WebCalibration:
    """
    Calibrates website chatbot targets.
    Supports both automated heuristics and visible interactive user click-to-calibrate flows.
    """

    async def auto_calibrate(self, target_url: str, headless: bool = True) -> TargetCalibrationConfig:
        """
        Runs headless automated interface detection on the target URL.
        """
        adapter = PlaywrightWebAdapter(target_url=target_url, headless=headless)
        try:
            await adapter.open()
            detected = await adapter.detect_chat_interface()
            return TargetCalibrationConfig(
                input_selector=detected.get("input_selector") or "textarea",
                submit_selector=detected.get("submit_selector") or "button#send",
                response_selector=detected.get("response_selector") or "#chat-box > *:last-child",
                wait_timeout_ms=15000,
            )
        finally:
            await adapter.close()

    async def calibrate_interactive(self, target_url: str, timeout_sec: int = 60) -> TargetCalibrationConfig:
        """
        Launches a visible browser window, displays step-by-step guidance overlay,
        and captures user clicks on the input box, send button, and response message.
        """
        logger.info(f"Starting interactive calibration for {target_url}")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(viewport={"width": 1280, "height": 800})
            page = await context.new_page()

            try:
                await page.goto(target_url, wait_until="domcontentloaded")
                await page.evaluate(CALIBRATION_OVERLAY_SCRIPT)

                start_time = asyncio.get_event_loop().time()
                while (asyncio.get_event_loop().time() - start_time) < timeout_sec:
                    await asyncio.sleep(0.5)
                    state = await page.evaluate("() => window.__aegis_result || {}")
                    if state.get("step") == 3:
                        break

                state = await page.evaluate("() => window.__aegis_result || {}")
                return TargetCalibrationConfig(
                    input_selector=state.get("input_selector") or "textarea#chat-input",
                    submit_selector=state.get("submit_selector") or "button#send",
                    response_selector=state.get("response_selector") or ".chat-message.assistant:last-child",
                    wait_timeout_ms=15000,
                )
            except Exception as e:
                logger.error(f"Interactive calibration error: {e}")
                # Fallback to auto-detect
                return await self.auto_calibrate(target_url, headless=True)
            finally:
                await browser.close()
