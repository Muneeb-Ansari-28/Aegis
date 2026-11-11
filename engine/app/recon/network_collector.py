"""Playwright Passive Reconnaissance Collector.

Captures network traffic, WebSocket connections, response headers,
DOM globals, script URLs, well-known paths, and pre-detects chat candidates
without requiring user interaction.
"""
import asyncio
import json
import logging
from typing import Any, Dict, List, Literal, Optional, Set, Tuple
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
    status: Literal["completed", "partial", "skipped", "failed", "unknown"] = "completed"
    warnings: List[str] = Field(default_factory=list)
    page_title: str = ""
    page_text_sample: str = ""
    observed_signals: Dict[str, Any] = Field(default_factory=dict)
    chat_candidates: ChatCandidates = Field(default_factory=ChatCandidates)
    well_known_found: List[str] = Field(default_factory=list)
    endpoint_checks: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


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
        self.parsed_target = urlparse(target_url)
        self.target_netloc = self.parsed_target.netloc
        self.base_origin = f"{self.parsed_target.scheme}://{self.parsed_target.netloc}"

    def _is_target_origin(self, url: str) -> bool:
        if not url:
            return False
        parsed = urlparse(url)
        # If relative URL or same netloc, it belongs to target origin
        return not parsed.netloc or parsed.netloc == self.target_netloc

    def _filter_and_record_response(
        self,
        response: Any,
        observed_paths: Set[str],
        observed_headers: Dict[str, str],
        observed_resp_keys: Set[str],
    ) -> None:
        try:
            r_url = getattr(response, "url", "")
            if not self._is_target_origin(r_url):
                return

            parsed = urlparse(r_url)
            if parsed.path:
                observed_paths.add(parsed.path)

            headers = getattr(response, "headers", {})
            if isinstance(headers, dict):
                for k, v in headers.items():
                    observed_headers[str(k).lower()] = str(v).lower()
        except Exception as e:
            logger.debug(f"Error filtering response: {e}")

    async def _record_response_body(
        self,
        response: Any,
        observed_resp_keys: Set[str],
    ) -> None:
        try:
            r_url = getattr(response, "url", "")
            if not self._is_target_origin(r_url):
                return

            headers = getattr(response, "headers", {})
            ctype = headers.get("content-type", "") if isinstance(headers, dict) else ""
            if "application/json" in ctype or not ctype:
                try:
                    body = await response.json()
                    if isinstance(body, dict):
                        for k in body.keys():
                            observed_resp_keys.add(str(k).lower())
                    elif isinstance(body, list) and body and isinstance(body[0], dict):
                        for k in body[0].keys():
                            observed_resp_keys.add(str(k).lower())
                except Exception:
                    pass
        except Exception:
            pass

    async def _probe_well_known_paths(
        self,
        base_origin: str,
    ) -> Tuple[List[str], Dict[str, Dict[str, Any]]]:
        """
        Probe the 7 well-known paths individually with bounded per-request timeouts.
        One failure or timeout does not discard other endpoints.
        """
        well_known_found: List[str] = []
        endpoint_checks: Dict[str, Dict[str, Any]] = {}

        try:
            async with httpx.AsyncClient(verify=False, timeout=2.0) as client:
                for path in WELL_KNOWN_PATHS:
                    probe_url = urljoin(base_origin, path)
                    try:
                        resp = await client.get(probe_url)
                        is_ok = resp.status_code in (200, 301, 302, 307, 308)
                        endpoint_checks[path] = {
                            "status_code": resp.status_code,
                            "ok": is_ok,
                        }
                        if is_ok:
                            well_known_found.append(path)
                    except Exception as ex:
                        endpoint_checks[path] = {
                            "error": type(ex).__name__,
                            "ok": False,
                        }
        except Exception as e:
            logger.debug(f"Well-known path client error: {e}")

        return well_known_found, endpoint_checks

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
        warnings: List[str] = []
        browser_ok = False

        if self.parsed_target.path:
            observed_paths.add(self.parsed_target.path)

        # 1. Playwright browser inspection with guaranteed cleanup
        try:
            async with async_playwright() as p:
                browser: Optional[Browser] = None
                context: Optional[BrowserContext] = None
                try:
                    browser = await p.chromium.launch(
                        headless=self.headless,
                        timeout=self.timeout_ms,
                    )
                    context = await browser.new_context(
                        ignore_https_errors=True,
                        viewport={"width": 1280, "height": 800},
                        user_agent=(
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 AegisRecon/1.0"
                        ),
                    )
                    page: Page = await context.new_page()

                    async def on_response(response):
                        self._filter_and_record_response(
                            response,
                            observed_paths,
                            observed_headers,
                            observed_resp_keys,
                        )
                        await self._record_response_body(
                            response,
                            observed_resp_keys,
                        )

                    async def on_request(request):
                        try:
                            if not self._is_target_origin(request.url):
                                return
                            parsed = urlparse(request.url)
                            if parsed.path:
                                observed_paths.add(parsed.path)
                            post_data = request.post_data
                            if post_data:
                                try:
                                    payload = json.loads(post_data)
                                    if isinstance(payload, dict):
                                        for k in payload.keys():
                                            observed_payload_keys.add(str(k).lower())
                                except Exception:
                                    pass
                        except Exception:
                            pass

                    def on_websocket(ws):
                        try:
                            if self._is_target_origin(ws.url):
                                observed_ws.add(ws.url)
                                ws_parsed = urlparse(ws.url)
                                if ws_parsed.path:
                                    observed_paths.add(ws_parsed.path)
                        except Exception:
                            pass

                    page.on("response", on_response)
                    page.on("request", on_request)
                    page.on("websocket", on_websocket)

                    try:
                        await page.goto(
                            self.target_url,
                            wait_until="domcontentloaded",
                            timeout=self.timeout_ms,
                        )
                        await asyncio.sleep(1.5)
                        browser_ok = True
                    except Exception as nav_e:
                        warnings.append(f"Browser navigation warning on {self.target_url}: {type(nav_e).__name__}")
                        logger.warning(f"Navigation warning on {self.target_url}: {nav_e}")

                    # Extract metadata if page loaded
                    try:
                        page_title = await page.title()
                    except Exception:
                        page_title = ""

                    try:
                        body_text = await page.evaluate("() => document.body ? document.body.innerText : ''")
                        page_text = (body_text or "")[:2000].strip()
                    except Exception:
                        page_text = ""

                    try:
                        script_srcs = await page.evaluate(
                            "() => Array.from(document.querySelectorAll('script[src]')).map(s => s.src)"
                        )
                        # Keep scripts from target origin or AI frameworks
                        for src in (script_srcs or []):
                            if self._is_target_origin(src) or any(ai in src.lower() for ai in ["streamlit", "gradio", "langchain"]):
                                observed_scripts.append(src)
                    except Exception:
                        pass

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
                finally:
                    if context:
                        try:
                            await context.close()
                        except Exception:
                            pass
                    if browser:
                        try:
                            await browser.close()
                        except Exception:
                            pass
        except Exception as play_e:
            warnings.append(f"Playwright passive collector error: {type(play_e).__name__}")
            logger.warning(f"Playwright error during passive collection: {play_e}")

        # 2. Probe well-known paths asynchronously via bounded active checks
        well_known_found, endpoint_checks = await self._probe_well_known_paths(self.base_origin)
        for ep in well_known_found:
            observed_paths.add(ep)

        # 3. Determine stage status
        if browser_ok and not warnings:
            status = "completed"
        elif browser_ok or well_known_found or observed_paths:
            status = "partial"
        else:
            status = "failed"

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
            status=status,
            warnings=warnings,
            page_title=page_title,
            page_text_sample=page_text,
            observed_signals=observed_signals,
            chat_candidates=ChatCandidates(
                inputs=chat_inputs,
                submits=chat_submits,
                responses=chat_responses,
            ),
            well_known_found=well_known_found,
            endpoint_checks=endpoint_checks,
        )
