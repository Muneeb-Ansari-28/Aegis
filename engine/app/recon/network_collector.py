"""Playwright Passive Reconnaissance Collector.

Captures network traffic, WebSocket connections, response headers,
DOM globals, script URLs, well-known paths, and pre-detects chat candidates
without requiring user interaction.
"""
import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

import httpx
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from pydantic import BaseModel, Field

from app.adapters.playwright_web import (
    CANDIDATE_INPUT_SELECTORS,
    CANDIDATE_SUBMIT_SELECTORS,
    CANDIDATE_RESPONSE_SELECTORS,
)
from app.core.config import get_settings

logger = logging.getLogger(__name__)

WELL_KNOWN_PATHS = [
    "/openapi.json",
    "/docs",
    "/health",
    "/api/version",
    "/api/tags",
    "/_stcore/health",
    "/info",
]


class ChatCandidates(BaseModel):
    inputs: List[str] = Field(default_factory=list)
    submits: List[str] = Field(default_factory=list)
    responses: List[str] = Field(default_factory=list)


class PassiveReconData(BaseModel):
    """Complete collection of passive signals gathered from target."""
    target_url: str
    page_title: str = ""
    page_text_sample: str = ""
    observed_signals: Dict[str, Any] = Field(default_factory=dict)
    chat_candidates: ChatCandidates = Field(default_factory=ChatCandidates)
    well_known_found: List[str] = Field(default_factory=list)


class PassiveNetworkCollector:
    """
    Executes passive reconnaissance on target web URL using Playwright.
    Collects network traffic, headers, scripts, DOM globals, and well-known paths.
    """

    def __init__(self, target_url: str, headless: Optional[bool] = None, timeout_ms: int = 15000):
        self.target_url = target_url
        settings = get_settings()
        self.headless = settings.PLAYWRIGHT_HEADLESS if headless is None else headless
        self.timeout_ms = timeout_ms

    async def collect(self) -> PassiveReconData:
        """
        Execute passive inspection and return structured signal data.
        """
        observed_paths: Set[str] = set()
        observed_headers: Dict[str, str] = {}
        observed_ws: Set[str] = set()
        observed_scripts: List[str] = []
        observed_globals: Set[str] = set()
        observed_dom: Set[str] = set()
        observed_resp_keys: Set[str] = set()
        observed_payload_keys: Set[str] = set()

        chat_inputs: List[str] = []
        chat_submits: List[str] = []
        chat_responses: List[str] = []
        page_title = ""
        page_text = ""

        # Parse baseline path
        parsed_target = urlparse(self.target_url)
        base_origin = f"{parsed_target.scheme}://{parsed_target.netloc}"
        if parsed_target.path:
            observed_paths.add(parsed_target.path)

        async with async_playwright() as p:
            browser: Browser = await p.chromium.launch(
                headless=self.headless,
                timeout=self.timeout_ms,
            )
            # ignore_https_errors=True is critical for localhost dev certs
            context: BrowserContext = await browser.new_context(
                ignore_https_errors=True,
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 AegisRecon/1.0"
                ),
            )
            page: Page = await context.new_page()

            # 1. Network response listener
            async def on_response(response):
                try:
                    r_url = response.url
                    parsed = urlparse(r_url)
                    if parsed.netloc == parsed_target.netloc:
                        observed_paths.add(parsed.path)

                    headers = response.headers
                    for k, v in headers.items():
                        observed_headers[k.lower()] = v.lower()

                    ctype = headers.get("content-type", "")
                    if "application/json" in ctype:
                        try:
                            body = await response.json()
                            if isinstance(body, dict):
                                for k in body.keys():
                                    observed_resp_keys.add(k.lower())
                            elif isinstance(body, list) and body and isinstance(body[0], dict):
                                for k in body[0].keys():
                                    observed_resp_keys.add(k.lower())
                        except Exception:
                            pass
                except Exception:
                    pass

            # 2. Network request listener
            async def on_request(request):
                try:
                    parsed = urlparse(request.url)
                    if parsed.netloc == parsed_target.netloc:
                        observed_paths.add(parsed.path)
                    post_data = request.post_data
                    if post_data:
                        try:
                            payload = json.loads(post_data)
                            if isinstance(payload, dict):
                                for k in payload.keys():
                                    observed_payload_keys.add(k.lower())
                        except Exception:
                            pass
                except Exception:
                    pass

            # 3. WebSocket listener
            def on_websocket(ws):
                try:
                    observed_ws.add(ws.url)
                    ws_parsed = urlparse(ws.url)
                    if ws_parsed.netloc == parsed_target.netloc:
                        observed_paths.add(ws_parsed.path)
                except Exception:
                    pass

            page.on("response", on_response)
            page.on("request", on_request)
            page.on("websocket", on_websocket)

            # Navigate to target
            try:
                await page.goto(
                    self.target_url,
                    wait_until="domcontentloaded",
                    timeout=self.timeout_ms,
                )
                # Allow async client hydration / requests to settle
                await asyncio.sleep(1.5)
            except Exception as e:
                logger.warning(f"Navigation warning during passive recon on {self.target_url}: {e}")

            # Capture page metadata
            try:
                page_title = await page.title()
            except Exception:
                page_title = ""

            try:
                body_text = await page.evaluate("() => document.body ? document.body.innerText : ''")
                page_text = (body_text or "")[:2000].strip()
            except Exception:
                page_text = ""

            # Capture script tags
            try:
                script_srcs = await page.evaluate(
                    "() => Array.from(document.querySelectorAll('script[src]')).map(s => s.src)"
                )
                observed_scripts.extend(script_srcs or [])
            except Exception:
                pass

            # Probe known window globals
            check_globals = [
                "__NEXT_DATA__",
                "gradio_config",
                "gradio_api_info",
                "Streamlit",
                "streamlit",
                "chainlit",
                "webpackChunk",
            ]
            for glob in check_globals:
                try:
                    has_global = await page.evaluate(f"() => typeof window['{glob}'] !== 'undefined'")
                    if has_global:
                        observed_globals.add(glob)
                except Exception:
                    pass

            # Probe known framework DOM elements
            check_dom = [
                "div.stApp",
                "div[data-testid='stChatMessage']",
                "gradio-app",
                "div#chainlit-copilot",
                "div#__next",
            ]
            for selector in check_dom:
                try:
                    count = await page.locator(selector).count()
                    if count > 0:
                        observed_dom.add(selector)
                except Exception:
                    pass

            # 4. Pre-detect chat candidates for calibration
            for selector in CANDIDATE_INPUT_SELECTORS:
                try:
                    loc = page.locator(selector).first
                    if await loc.count() > 0 and await loc.is_visible():
                        chat_inputs.append(selector)
                except Exception:
                    continue

            for selector in CANDIDATE_SUBMIT_SELECTORS:
                try:
                    loc = page.locator(selector).first
                    if await loc.count() > 0 and await loc.is_visible():
                        chat_submits.append(selector)
                except Exception:
                    continue

            for selector in CANDIDATE_RESPONSE_SELECTORS:
                try:
                    loc = page.locator(selector).first
                    if await loc.count() > 0:
                        chat_responses.append(selector)
                except Exception:
                    continue

            await context.close()
            await browser.close()

        # 5. Probe well-known paths asynchronously via httpx
        well_known_found: List[str] = []
        try:
            async with httpx.AsyncClient(verify=False, timeout=3.0) as client:
                for path in WELL_KNOWN_PATHS:
                    probe_url = urljoin(base_origin, path)
                    try:
                        resp = await client.get(probe_url)
                        if resp.status_code in (200, 301, 302, 307, 308):
                            well_known_found.append(path)
                            observed_paths.add(path)
                            if "openapi.json" in path and resp.status_code == 200:
                                observed_headers["server"] = resp.headers.get("server", "")
                    except Exception:
                        continue
        except Exception as e:
            logger.debug(f"Well-known path probe error: {e}")

        observed_signals = {
            "paths": list(observed_paths),
            "headers": observed_headers,
            "websocket_paths": list(observed_ws),
            "dom": list(observed_dom),
            "globals": list(observed_globals),
            "scripts": observed_scripts,
            "response_keys": list(observed_resp_keys),
            "payload_keys": list(observed_payload_keys),
        }

        return PassiveReconData(
            target_url=self.target_url,
            page_title=page_title,
            page_text_sample=page_text,
            observed_signals=observed_signals,
            chat_candidates=ChatCandidates(
                inputs=chat_inputs,
                submits=chat_submits,
                responses=chat_responses,
            ),
            well_known_found=well_known_found,
        )

