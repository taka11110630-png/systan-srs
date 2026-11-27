"""Opaque-box Playwright E2E test harness for systan-srs.

Serves the repository root over an ephemeral 127.0.0.1 HTTP server and provides
isolated per-test BrowserContexts plus strictly DOM-based UI helpers matching
PROJECT.md § Interface Contracts.
"""

from __future__ import annotations

import functools
import json
import mimetypes
import os
import re
import tempfile
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterator

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
CHROME_EXECUTABLE = "/usr/bin/google-chrome"

EXTERNAL_BUNDLE_PATH = Path("/tmp/drive_notes/systan_data.json")
EXTERNAL_AI_PACK_PATH = Path("/home/antigravity/private/systan_ai_pack.json")

STORAGE_KEY = "systan_srs_state_v2"

CORE_9_FAMILIES = [
    "transitive_trap",
    "intrans_prep",
    "svoo_vs_to",
    "svoc",
    "from_family",
    "with_family",
    "of_family",
    "as_family",
    "vocab_confusable",
]

IMPERIAL_4_FAMILIES = [
    "inanimate_subject",
    "stage5_polysemy",
    "stage3_usage",
    "composition_trap",
]

CANONICAL_FAMILIES = CORE_9_FAMILIES + IMPERIAL_4_FAMILIES

LEGACY_FAMILY_ALIASES = {
    "vt_trap": "transitive_trap",
    "vi_prep": "intrans_prep",
    "svoo_to": "svoo_vs_to",
    "svoc_that": "svoc",
    "from_prevent": "from_family",
    "with_provide": "with_family",
    "of_rob": "of_family",
    "as_regard": "as_family",
    "writing_trap": "composition_trap",
}

CANONICAL_LEVELS = ["all", "common", "march", "national"]

CANONICAL_TARGETS = [
    "today_weak",
    "ext_cloze",
    "err_reason",
    "verb_family",
    "stage_batch",
]

CANONICAL_ERROR_TAGS = [
    "knowledge_gap",
    "misunderstanding",
    "misreading",
    "careless",
    "confusion",
    "order_error",
]

LEGACY_ERROR_TAGS = ["prep_pattern", "confusable", "slow", "unlearned"]

CLOSING_TAB1 = (
    "まずは自分で解いてください。あなたの回答後に、同じミスが残っているかを確認します。"
)
CLOSING_TAB3 = (
    "まずは正解を気にせず、10秒だけ考えて答えてください。あなたの回答後に、正解とズレを整理します。"
)
CLOSING_TAB5 = (
    "まずは自分の力で答えてください。あなたの回答後に、どの知識を使えばよかったかを整理します。"
)


class SkipTest(Exception):
    """Raised by optional external-data tests when external private files are absent."""


class _QuietHandler(SimpleHTTPRequestHandler):
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".js": "application/javascript; charset=utf-8",
        ".mjs": "application/javascript; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".svg": "image/svg+xml",
        ".html": "text/html; charset=utf-8",
        ".css": "text/css; charset=utf-8",
    }

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        if self.path.endswith("sw.js"):
            self.send_header("Service-Worker-Allowed", "/")
        super().end_headers()

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return


class LocalStaticServer:
    """Ephemeral 127.0.0.1:0 static HTTP server for the PWA repo root."""

    def __init__(self, directory: Path = REPO_ROOT) -> None:
        self.directory = directory
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self.url: str = ""

    def start(self) -> str:
        mimetypes.add_type("application/javascript", ".js")
        handler = functools.partial(_QuietHandler, directory=str(self.directory))
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self._server.daemon_threads = True
        port = self._server.server_address[1]
        self.url = f"http://127.0.0.1:{port}"
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self.url

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=3)
            self._thread = None


@dataclass
class BrowserSession:
    context: BrowserContext
    page: Page
    base_url: str
    page_errors: list[str] = field(default_factory=list)
    console_errors: list[str] = field(default_factory=list)
    dialogs: list[str] = field(default_factory=list)

    def assert_no_errors(self, allow_console_substr: tuple[str, ...] = ()) -> None:
        unexpected_console = [
            msg
            for msg in self.console_errors
            if not any(s in msg for s in allow_console_substr)
        ]
        if self.page_errors or unexpected_console:
            parts = []
            if self.page_errors:
                parts.append(f"pageerrors={self.page_errors}")
            if unexpected_console:
                parts.append(f"console.error={unexpected_console}")
            raise AssertionError("Unexpected runtime errors: " + "; ".join(parts))


class TestEnv:
    """Shared local HTTP server + single headless Chrome instance across a run."""

    def __init__(self) -> None:
        self.server = LocalStaticServer(REPO_ROOT)
        self._pw_cm: Any = None
        self._pw: Any = None
        self.browser: Browser | None = None
        self.base_url: str = ""

    def __enter__(self) -> "TestEnv":
        self.base_url = self.server.start()
        self._pw_cm = sync_playwright()
        self._pw = self._pw_cm.__enter__()
        launch_kwargs: dict[str, Any] = {"headless": True}
        if os.path.exists(CHROME_EXECUTABLE):
            launch_kwargs["executable_path"] = CHROME_EXECUTABLE
        self.browser = self._pw.chromium.launch(**launch_kwargs)
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self.browser is not None:
            self.browser.close()
            self.browser = None
        if self._pw_cm is not None:
            self._pw_cm.__exit__(exc_type, exc, tb)
            self._pw_cm = None
            self._pw = None
        self.server.stop()

    @contextmanager
    def new_session(
        self,
        viewport: dict[str, int] | None = None,
        init_script: str | None = None,
        auto_accept_dialogs: bool = True,
        timeout_ms: int = 4500,
    ) -> Iterator[BrowserSession]:
        assert self.browser is not None
        vp = viewport or {"width": 1280, "height": 860}
        context = self.browser.new_context(viewport=vp, service_workers="allow")
        if init_script:
            context.add_init_script(init_script)
        page = context.new_page()
        page.set_default_timeout(timeout_ms)
        session = BrowserSession(context=context, page=page, base_url=self.base_url)

        page.on("pageerror", lambda err: session.page_errors.append(str(err)))
        page.on(
            "console",
            lambda msg: session.console_errors.append(msg.text)
            if msg.type == "error"
            else None,
        )
        if auto_accept_dialogs:

            def _on_dialog(dialog: Any) -> None:
                session.dialogs.append(dialog.message)
                dialog.accept()

            page.on("dialog", _on_dialog)

        try:
            yield session
        finally:
            context.close()


# ---------------------------------------------------------------------------
# Fixture loading utilities
# ---------------------------------------------------------------------------


def fixture_path(name: str) -> Path:
    path = FIXTURES_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Missing fixture: {path}")
    return path


def load_fixture_json(name: str) -> Any:
    return json.loads(fixture_path(name).read_text(encoding="utf-8"))


@contextmanager
def temp_json_file(data: Any, filename: str = "temp_pack.json") -> Iterator[Path]:
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir) / filename
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        yield p


# ---------------------------------------------------------------------------
# Opaque-Box DOM interaction helpers
# ---------------------------------------------------------------------------


def open_app(page: Page, base_url: str) -> None:
    page.goto(base_url + "/", wait_until="domcontentloaded")
    page.wait_for_function(
        """() => {
            const ob = document.getElementById('onboardingScreen');
            const main = document.getElementById('appMain');
            const obVis = ob && getComputedStyle(ob).display !== 'none';
            const mainVis = main && getComputedStyle(main).display !== 'none';
            return Boolean(obVis || mainVis);
        }"""
    )


def upload_bundle(page: Page, path: Path) -> None:
    inp = page.locator("#bundleFileInput, #onboardFileInput").first
    assert inp.count() > 0, "Expected onboarding bundle file input (#bundleFileInput or #onboardFileInput)"
    inp.set_input_files(str(path))
    page.wait_for_function(
        """() => {
            const main = document.getElementById('appMain');
            const ob = document.getElementById('onboardingScreen');
            return main && getComputedStyle(main).display !== 'none'
                && (!ob || getComputedStyle(ob).display === 'none');
        }"""
    )


def boot_with_synthetic(page: Page, base_url: str, bundle_name: str = "synthetic_bundle.json") -> None:
    open_app(page, base_url)
    upload_bundle(page, fixture_path(bundle_name))


def switch_tab(page: Page, tab_name: str) -> None:
    btn = page.locator(f"#mainNav button[data-tab='{tab_name}']")
    assert btn.count() == 1, f"Missing nav tab button for data-tab='{tab_name}'"
    btn.click()
    page.wait_for_selector(f"#tab-{tab_name}.active")


def open_ai_panel(page: Page) -> None:
    panel = page.locator("#loopAiPanel")
    if not panel.is_visible():
        page.locator("#loopToggleAiBtn").click()
        panel.wait_for(state="visible")


def get_ext_badge_text(page: Page) -> str:
    badge = page.locator("#loopExtBadge, #loopExtStatusBadge").first
    assert badge.count() > 0, "Missing AI pack status badge (#loopExtBadge / #loopExtStatusBadge)"
    return badge.inner_text().strip()


def parse_ext_badge_counts(text: str) -> tuple[int, int]:
    """Extract (hook_count, cloze_count) from badge text like '🧩 拡張フック 6語 / 📝 4択 18問'."""
    m_hk = re.search(r"(\d+)\s*語", text)
    m_cl = re.search(r"(\d+)\s*問", text)
    if not m_hk or not m_cl:
        raise AssertionError(f"Could not parse hook/cloze counts from badge text: {text!r}")
    return int(m_hk.group(1)), int(m_cl.group(1))


def upload_ai_pack(page: Page, path: Path) -> str:
    open_ai_panel(page)
    inp = page.locator("#loopExtFileInput, #aiExtFileInput").first
    assert inp.count() > 0, "Missing AI pack file input (#loopExtFileInput / #aiExtFileInput)"
    inp.set_input_files(str(path))
    page.wait_for_timeout(250)
    return get_ext_badge_text(page)


def paste_ai_pack(page: Page, text: str) -> str:
    open_ai_panel(page)
    ta = page.locator("#loopExtJsonInput, #aiPasteJsonInput").first
    btn = page.locator("#loopExtImportBtn, #aiImportPasteBtn").first
    assert ta.count() > 0 and btn.count() > 0, "Missing AI JSON paste textarea/import button"
    ta.fill(text)
    btn.click()
    page.wait_for_timeout(250)
    return get_ext_badge_text(page)


def select_loop_mode(page: Page, style: str) -> None:
    sel = page.locator("#loopModeSel")
    if sel.count() > 0 and sel.is_visible():
        sel.select_option(style)
        return
    btn = page.locator(f"#loopStyleSwitch button[data-lstyle='{style}']")
    assert btn.count() > 0, f"Loop style '{style}' not found in #loopModeSel or #loopStyleSwitch"
    btn.click()


def select_loop_focus(page: Page, fmt: str) -> None:
    sel = page.locator("#loopFocusSel")
    if sel.count() > 0 and sel.is_visible():
        sel.select_option(fmt)
        return
    btn = page.locator(f"#loopSingleFmtBar button[data-lfmt='{fmt}']")
    assert btn.count() > 0, f"Loop focus '{fmt}' not found in #loopFocusSel or #loopSingleFmtBar"
    btn.click()


def select_loop_size(page: Page, size: int) -> None:
    s = str(size)
    sel = page.locator("#loopSizeSel")
    if sel.count() > 0 and sel.is_visible():
        sel.select_option(s)
        return
    btn = page.locator(f"#loopSizeBar button[data-lsize='{s}']")
    assert btn.count() > 0, f"Loop size '{s}' not found in #loopSizeSel or #loopSizeBar"
    btn.click()


def get_available_loop_targets(page: Page) -> list[str]:
    sel = page.locator("#loopTargetSel")
    if sel.count() > 0:
        return sel.locator("option").evaluate_all("opts => opts.map(o => o.value)")
    return page.locator("#loopTargetBar button[data-ltarget]").evaluate_all(
        "btns => btns.map(b => b.getAttribute('data-ltarget'))"
    )


def select_loop_target(page: Page, target: str) -> None:
    sel = page.locator("#loopTargetSel")
    if sel.count() > 0:
        opts = sel.locator("option").evaluate_all("opts => opts.map(o => o.value)")
        assert target in opts, f"Target '{target}' missing from #loopTargetSel options: {opts}"
        sel.select_option(target)
        return
    btn = page.locator(f"#loopTargetBar button[data-ltarget='{target}']")
    if btn.count() == 0:
        avail = get_available_loop_targets(page)
        raise AssertionError(
            f"Contract violation: target '{target}' missing from #loopTargetSel / #loopTargetBar (available: {avail})"
        )
    btn.click()


def get_available_levels(page: Page) -> list[str]:
    sel = page.locator("#loopLevelSel")
    assert sel.count() > 0, "Contract violation: missing required selector #loopLevelSel"
    return sel.locator("option").evaluate_all("opts => opts.map(o => o.value)")


def select_loop_level(page: Page, level: str) -> None:
    avail = get_available_levels(page)
    assert level in avail, f"Contract violation: level '{level}' missing from #loopLevelSel (available: {avail})"
    page.locator("#loopLevelSel").select_option(level)


def get_available_verb_families(page: Page) -> list[str]:
    sel = page.locator("#loopVerbFamilySel")
    if sel.count() > 0:
        return sel.locator("option").evaluate_all("opts => opts.map(o => o.value)")
    # Ensure verb_family subfilter is rendered if using #loopVfBar
    if page.locator("#loopVfBar").count() == 0:
        select_loop_target(page, "verb_family")
    return page.locator("#loopVfBar button[data-vf]").evaluate_all(
        "btns => btns.map(b => b.getAttribute('data-vf'))"
    )


def select_verb_family(page: Page, family: str) -> None:
    sel = page.locator("#loopVerbFamilySel")
    if sel.count() > 0:
        opts = sel.locator("option").evaluate_all("opts => opts.map(o => o.value)")
        assert family in opts, (
            f"Contract violation: family '{family}' missing from #loopVerbFamilySel (available: {opts})"
        )
        sel.select_option(family)
        return
    if page.locator("#loopVfBar").count() == 0:
        select_loop_target(page, "verb_family")
    btn = page.locator(f"#loopVfBar button[data-vf='{family}']")
    if btn.count() == 0:
        avail = get_available_verb_families(page)
        raise AssertionError(
            f"Contract violation: family '{family}' missing from #loopVerbFamilySel / #loopVfBar (available: {avail})"
        )
    btn.click()


def get_available_ai_prompt_types(page: Page) -> list[str]:
    open_ai_panel(page)
    sel = page.locator("#loopAiPromptType")
    if sel.count() > 0:
        return sel.locator("option").evaluate_all("opts => opts.map(o => o.value)")
    return page.locator("#aiModeBar button[data-aimode]").evaluate_all(
        "btns => btns.map(b => b.getAttribute('data-aimode'))"
    )


def select_ai_prompt_type(page: Page, ptype: str) -> None:
    open_ai_panel(page)
    sel = page.locator("#loopAiPromptType")
    if sel.count() > 0:
        opts = sel.locator("option").evaluate_all("opts => opts.map(o => o.value)")
        assert ptype in opts, (
            f"Contract violation: AI prompt type '{ptype}' missing from #loopAiPromptType (available: {opts})"
        )
        sel.select_option(ptype)
        return
    btn = page.locator(f"#aiModeBar button[data-aimode='{ptype}']")
    if btn.count() == 0:
        avail = get_available_ai_prompt_types(page)
        raise AssertionError(
            f"Contract violation: AI prompt type '{ptype}' missing from #loopAiPromptType / #aiModeBar (available: {avail})"
        )
    btn.click()


def get_ai_prompt_text(page: Page) -> str:
    open_ai_panel(page)
    ta = page.locator("#loopAiPromptOut, #aiPromptTextarea").first
    assert ta.count() > 0, "Missing AI prompt output textarea (#loopAiPromptOut / #aiPromptTextarea)"
    return ta.input_value()


def start_loop_session(page: Page) -> None:
    btn = page.locator("#loopStartBtn")
    assert btn.count() > 0, "Expected #loopStartBtn to start Loop session"
    btn.click()


def read_local_state(page: Page) -> dict[str, Any]:
    raw = page.evaluate("(k) => localStorage.getItem(k)", STORAGE_KEY)
    assert raw is not None, f"localStorage['{STORAGE_KEY}'] is unexpectedly null"
    return json.loads(raw)


def write_local_state(page: Page, state_obj: dict[str, Any]) -> None:
    page.evaluate(
        "([k, v]) => localStorage.setItem(k, v)",
        [STORAGE_KEY, json.dumps(state_obj, ensure_ascii=False)],
    )


def get_toast_text(page: Page) -> str:
    return page.locator("#toast").inner_text().strip()
