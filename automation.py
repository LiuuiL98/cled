from __future__ import annotations

from typing import Optional

from playwright.sync_api import BrowserContext, Error, Page, Playwright, sync_playwright

from settings import Settings, app_data_dir

DEFAULT_LOGIN_URL = "https://elearningbluefe.e-chinalife.com/els/learner-studentpc-fe/"


class BrowserAutomation:
    """Controls a dedicated Edge profile; never reads cookies or credentials."""

    OTP_SELECTORS = [
        'input[autocomplete="one-time-code"]',
        'input[name*="otp" i]',
        'input[id*="otp" i]',
        'input[name*="smsCode" i]',
        'input[id*="smsCode" i]',
        'input[name*="verifyCode" i]',
        'input[id*="verifyCode" i]',
        'input[placeholder*="验证码"]',
        'input[aria-label*="验证码"]',
        'input[placeholder*="校验码"]',
    ]

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._playwright: Optional[Playwright] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    @property
    def profile_dir(self):
        return app_data_dir() / "edge-profile"

    def open_login(self) -> None:
        if self._page and not self._page.is_closed():
            self._page.goto(self.settings.login_url, wait_until="domcontentloaded")
            return
        self._playwright = sync_playwright().start()
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        try:
            self._context = self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_dir),
                channel="msedge",
                headless=False,
                viewport=None,
                args=["--start-maximized"],
            )
        except Error as exc:
            self._playwright.stop()
            self._playwright = None
            raise RuntimeError(
                "无法通过 Playwright 启动 Microsoft Edge。请确认已安装最新版 Edge，"
                "并关闭占用本工具专用浏览器配置目录的残留进程。"
            ) from exc
        self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
        self._page.goto(self.settings.login_url, wait_until="domcontentloaded", timeout=60000)

    def check_login(self) -> str:
        if not self._page or self._page.is_closed():
            return "closed"
        try:
            current_url = self._page.url
            if self.settings.success_url_contains:
                return "authenticated" if self.settings.success_url_contains in current_url else "waiting"
            if self.settings.success_selector:
                locator = self._page.locator(self.settings.success_selector).first
                if locator.count() and locator.is_visible(timeout=500):
                    return "authenticated"
                return "waiting"
            login_path = self.settings.login_url.rstrip("/")
            if current_url.rstrip("/") != login_path and current_url.startswith("https://"):
                return "authenticated"
            return "waiting"
        except Error:
            return "waiting"

    def fill_otp(self, code: str) -> bool:
        """Fill only one uniquely identified OTP field; never submit the form."""
        if not self._page or self._page.is_closed():
            return False
        if not code.isdigit() or not 4 <= len(code) <= 8:
            return False
        try:
            return bool(self._page.evaluate(
                """({selectors, value}) => {
                    const fields = new Set();
                    for (const selector of selectors) {
                        document.querySelectorAll(selector).forEach((el) => {
                            if (!(el instanceof HTMLInputElement)) return;
                            const type = (el.getAttribute('type') || 'text').toLowerCase();
                            const visible = !!(el.getClientRects().length);
                            if (visible && !el.disabled && !el.readOnly &&
                                type !== 'password' && type !== 'hidden') fields.add(el);
                        });
                    }
                    if (fields.size !== 1) return false;
                    const el = [...fields][0];
                    const setter = Object.getOwnPropertyDescriptor(
                        HTMLInputElement.prototype, 'value'
                    ).set;
                    setter.call(el, value);
                    el.dispatchEvent(new Event('input', {bubbles: true}));
                    el.dispatchEvent(new Event('change', {bubbles: true}));
                    el.focus();
                    return true;
                }""",
                {"selectors": self.OTP_SELECTORS, "value": code},
            ))
        except Error:
            return False

    def navigate(self, url: str) -> None:
        if not self._page or self._page.is_closed():
            raise RuntimeError("Edge 页面已关闭")
        self._page.goto(url, wait_until="domcontentloaded", timeout=60000)

    def close(self) -> None:
        try:
            if self._context:
                self._context.close()
        finally:
            self._context = None
            self._page = None
            if self._playwright:
                self._playwright.stop()
                self._playwright = None
