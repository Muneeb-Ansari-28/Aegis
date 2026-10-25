"""Real Chromium regressions for collapsed chat, calibration, and viewport sizing."""
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from playwright.async_api import Browser

from app.adapters.playwright_web import PlaywrightWebAdapter
from app.adapters.web_calibration import WebCalibration
from app.schemas.target import TargetCalibrationConfig


@pytest.fixture(scope="module")
def chat_site():
    """Serve isolated chat variants without modifying either application."""
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            mode = self.path.strip("/")
            opened = "open" if mode in {"visible", "readonly"} else ""
            launcher = "" if mode == "missing" else (
                '<button aria-label="Open chat" onclick="'
                + ("" if mode == "broken" else "document.querySelector('dialog').showModal()")
                + '">Open chat</button>'
            )
            overlay = '<div style="position:fixed;inset:0;z-index:99"></div>' if mode == "blocked" else ""
            html = f"""<!doctype html><html><style>
            button[aria-label] {{position:fixed;right:24px;bottom:24px}}
            </style><body><input type="text" placeholder="Search catalog">{launcher}{overlay}
            <dialog {opened}><form onsubmit="event.preventDefault();
            document.querySelector('[role=log]').insertAdjacentHTML('beforeend',
            '<p class=assistant-message>Reply: '+document.querySelector('textarea').value+'</p>')">
            <textarea id="chat-input" {'readonly' if mode == 'readonly' else ''}></textarea>
            <button id="send" type="submit">Send</button></form>
            <div role="log"><p>Welcome</p></div></dialog></body></html>"""
            if mode == "silent":
                html = html.replace("document.querySelector('[role=log]').insertAdjacentHTML", "void")
            if mode == "delayed":
                html = html.replace("<body>", "<body><script>setTimeout(() => document.querySelector('main').hidden=false, 150)</script><main hidden>")
                html = html.replace("</body>", "</main></body>")
            if mode == "lazy":
                html += """<script>
                const template = document.querySelector('dialog').outerHTML;
                document.querySelector('dialog').remove();
                document.querySelector('button[aria-label="Open chat"]').onclick = () => {
                  document.body.insertAdjacentHTML('beforeend', template);
                  document.querySelector('dialog').showModal();
                };</script>"""
            if mode == "editable":
                html = """<textarea hidden></textarea>
                <div role="textbox" contenteditable="true"></div>
                <button id="send">Send</button><div role="log"><p>Welcome</p></div>"""
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode())

        def log_message(self, format: str, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()
    thread.join()


def selectors():
    """Saved selectors are unchanged by readiness handling."""
    return TargetCalibrationConfig(
        input_selector="#chat-input", submit_selector="#send",
        response_selector="[role='log'] > *:last-child", wait_timeout_ms=1000,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["closed", "visible", "delayed"])
async def test_scan_opens_if_needed_and_collects_reply(chat_site, mode):
    adapter = PlaywrightWebAdapter(f"{chat_site}/{mode}", selectors(), headless=True,
                                   browser_timeout_ms=3000, settle_timeout_ms=200)
    try:
        await adapter.open()
        assert adapter.page is not None
        assert adapter.page.viewport_size == {"width": 1280, "height": 800}
        turn = await adapter.send_prompt("Hello", 1)
        assert turn.status == "success", turn.response
        assert turn.response == "Reply: Hello"
        assert adapter.selectors == selectors().model_dump()
    finally:
        await adapter.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["missing", "broken", "blocked", "readonly"])
async def test_unusable_chat_returns_clear_error_without_submitting(chat_site, mode):
    adapter = PlaywrightWebAdapter(f"{chat_site}/{mode}", selectors(), headless=True,
                                   browser_timeout_ms=500)
    try:
        await adapter.open()
        turn = await adapter.send_prompt("Must not submit", 1)
        assert turn.status == "error"
        assert "Chat input is not ready" in turn.response
        assert turn.metadata["error"]
        assert adapter.page is not None
        assert await adapter.page.locator("textarea").input_value() == ""
        assert await adapter.page.locator("[role=log]").text_content() == "Welcome"
    finally:
        await adapter.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["closed", "visible", "lazy"])
async def test_auto_calibration_selectors_reused_in_fresh_scan(chat_site, mode):
    config = await WebCalibration().auto_calibrate(f"{chat_site}/{mode}")
    adapter = PlaywrightWebAdapter(f"{chat_site}/{mode}", config, headless=True,
                                   settle_timeout_ms=200)
    try:
        turn = await adapter.send_prompt("Calibrated", 1)
        assert turn.status == "success", turn.response
        assert "Reply: Calibrated" in turn.response
    finally:
        await adapter.close()


@pytest.mark.asyncio
async def test_calibration_ignores_hidden_unrelated_textarea(chat_site):
    config = await WebCalibration().auto_calibrate(f"{chat_site}/editable")
    assert "contenteditable" in config.input_selector


@pytest.mark.asyncio
async def test_headed_scan_uses_native_viewport(chat_site):
    adapter = PlaywrightWebAdapter(f"{chat_site}/closed", selectors(), headless=False)
    try:
        await adapter.open()
        assert adapter.page is not None
        assert adapter.page.viewport_size is None
        cdp = await adapter.page.context.new_cdp_session(adapter.page)
        window = await cdp.send("Browser.getWindowForTarget")
        for width, height in [(900, 650), (1100, 750)]:
            before = await adapter.page.evaluate("[innerWidth, innerHeight]")
            await cdp.send("Browser.setWindowBounds", {
                "windowId": window["windowId"],
                "bounds": {"width": width, "height": height},
            })
            await adapter.page.wait_for_function(
                "before => innerWidth !== before[0] || innerHeight !== before[1]", arg=before,
            )
            assert await adapter.page.evaluate("""() => {
                const r = document.querySelector('button[aria-label]').getBoundingClientRect();
                return r.bottom <= innerHeight && r.right <= innerWidth;
            }""")
        await cdp.send("Browser.setWindowBounds", {
            "windowId": window["windowId"], "bounds": {"windowState": "maximized"},
        })
        turn = await adapter.send_prompt("Native", 1)
        assert turn.status == "success", turn.response
    finally:
        await adapter.close()


@pytest.mark.asyncio
async def test_calibration_storage_roundtrip_without_schema_change(chat_site, monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.core.database import Base
    from app.schemas.target import TargetCreate
    from app.services.target_service import TargetService

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    monkeypatch.setattr("app.services.target_service.SessionLocal", sessionmaker(bind=engine))
    monkeypatch.setattr(TargetService, "_targets", {})
    target = await TargetService.create_target(TargetCreate(name="Fixture", url=f"{chat_site}/closed"))
    assert target.url is not None
    config = await WebCalibration().auto_calibrate(target.url)
    await TargetService.calibrate_target(target.id, config)
    TargetService._targets.clear()
    loaded = await TargetService.get_target(target.id)
    assert loaded is not None
    assert loaded.calibration_config == config
    assert set(config.model_dump()) == {"input_selector", "submit_selector", "response_selector", "wait_timeout_ms"}
    engine.dispose()


@pytest.mark.asyncio
async def test_response_timeout_remains_a_connector_timeout(chat_site):
    adapter = PlaywrightWebAdapter(f"{chat_site}/silent", selectors(), headless=True)
    try:
        turn = await adapter.send_prompt("No answer", 1)
        assert turn.status == "timeout"
        assert turn.response.startswith("[CONNECTOR_TIMEOUT]")
        assert adapter.page is not None
        assert await adapter.page.locator("textarea").input_value() == "No answer"
    finally:
        await adapter.close()


@pytest.mark.asyncio
async def test_interactive_calibration_captures_and_reuses_controls(chat_site, monkeypatch):
    contexts = []
    original = Browser.new_context

    async def capture_context(browser, **kwargs):
        context = await original(browser, **kwargs)
        contexts.append(context)
        return context

    monkeypatch.setattr(Browser, "new_context", capture_context)
    steps = []

    async def progress(step):
        steps.append(step)
        page = contexts[0].pages[0]
        assert page.viewport_size is None
        if step == 0:
            await page.get_by_role("button", name="Open chat").click()
            await page.locator("#chat-input").click()
        elif step == 1:
            await page.locator("#send").click()

    config = await WebCalibration().calibrate_interactive(
        f"{chat_site}/closed", timeout_sec=10, progress_callback=progress,
    )
    assert steps == [0, 1, 2]
    assert config.input_selector == "#chat-input"
    assert config.submit_selector == "#send"
    adapter = PlaywrightWebAdapter(f"{chat_site}/closed", config, headless=True,
                                   settle_timeout_ms=200)
    try:
        turn = await adapter.send_prompt("Interactive", 1)
        assert turn.status == "success", turn.response
    finally:
        await adapter.close()
