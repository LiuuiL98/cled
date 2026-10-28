from __future__ import annotations

import re
from typing import Optional

from playwright.sync_api import BrowserContext, Error, Page, Playwright, sync_playwright

from login_entry import click_lock_corner_entry
from settings import Settings, app_data_dir


class BrowserAutomation:
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

    def open_password_login(self) -> str:
        if not self._page or self._page.is_closed():
            self.open_login()
        assert self._page is not None
        ok, message = click_lock_corner_entry(self._page)
        if not ok:
            raise RuntimeError(message)
        return message

    def _visible_inputs(self):
        if not self._page or self._page.is_closed():
            return []
        return self._page.locator("input").evaluate_all(
            """els => els.map((el, index) => {
                const style = getComputedStyle(el);
                return {
                    index,
                    visible: !!el.getClientRects().length && style.display !== 'none' && style.visibility !== 'hidden',
                    disabled: !!el.disabled,
                    readOnly: !!el.readOnly,
                    type: (el.getAttribute('type') || 'text').toLowerCase(),
                    name: el.getAttribute('name') || '',
                    id: el.id || '',
                    placeholder: el.getAttribute('placeholder') || '',
                    aria: el.getAttribute('aria-label') || '',
                    autocomplete: el.getAttribute('autocomplete') || ''
                };
            })"""
        )

    def fill_account_credentials(self, username: str, password: str) -> None:
        if not self._page or self._page.is_closed():
            raise RuntimeError("登录页面尚未打开。")
        items = self._visible_inputs()
        usable = [item for item in items if item["visible"] and not item["disabled"] and not item["readOnly"]]
        password_fields = [item for item in usable if item["type"] == "password"]
        if len(password_fields) != 1:
            raise RuntimeError("没有找到唯一的密码输入框，已停止自动填写。")
        username_fields = []
        for item in usable:
            combined = " ".join(item[k] for k in ("name", "id", "placeholder", "aria", "autocomplete")).lower()
            if item["type"] in ("text", "email", "tel", "number") and any(
                token in combined for token in ("user", "account", "mobile", "phone", "login", "账号", "帐号", "账户", "手机号", "工号")
            ) and not any(token in combined for token in ("otp", "sms", "verify", "验证码", "校验码")):
                username_fields.append(item)
        if not username_fields:
            candidates = [item for item in usable if item["type"] in ("text", "email", "tel", "number")]
            if len(candidates) == 1:
                username_fields = candidates
        if len(username_fields) != 1:
            raise RuntimeError("没有找到唯一的账号输入框，已停止自动填写。")

        self._page.locator("input").nth(username_fields[0]["index"]).fill(username.strip())
        self._page.locator("input").nth(password_fields[0]["index"]).fill(password)

    def submit_login(self) -> bool:
        if not self._page or self._page.is_closed():
            return False
        for frame in self._page.frames:
            candidates = []
            for selector in ("button", "[role='button']", "input[type='submit']", "input[type='button']"):
                locator = frame.locator(selector)
                try:
                    found = locator.evaluate_all(
                        """els => els.map((el, index) => {
                            const text = (el.innerText || el.value || el.getAttribute('aria-label') || '').replace(/\\s+/g, '').trim();
                            const visible = !!el.getClientRects().length &&
                                getComputedStyle(el).display !== 'none' &&
                                getComputedStyle(el).visibility !== 'hidden' && !el.disabled;
                            return {index, text, visible};
                        })"""
                    )
                    for item in found:
                        if item["visible"] and item["text"] in ("登录", "立即登录", "确认登录"):
                            candidates.append((selector, item["index"]))
                except Error:
                    continue
            if len(candidates) == 1:
                selector, index = candidates[0]
                frame.locator(selector).nth(index).click(timeout=5000)
                return True
            if len(candidates) > 1:
                return False
        return False

    def fill_otp(self, code: str) -> bool:
        if not self._page or self._page.is_closed() or not code.isdigit() or not 4 <= len(code) <= 8:
            return False
        try:
            return bool(self._page.evaluate(
                """({selectors, value}) => {
                    const fields = new Set();
                    for (const selector of selectors) {
                        document.querySelectorAll(selector).forEach((el) => {
                            if (!(el instanceof HTMLInputElement)) return;
                            const type = (el.getAttribute('type') || 'text').toLowerCase();
                            if (el.getClientRects().length && !el.disabled && !el.readOnly &&
                                type !== 'password' && type !== 'hidden') fields.add(el);
                        });
                    }
                    if (fields.size !== 1) return false;
                    const el = [...fields][0];
                    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
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

    def check_login(self) -> str:
        if not self._page or self._page.is_closed():
            return "closed"
        try:
            url = self._page.url.lower()
            blocked = ("login", "signin", "sso", "oauth", "auth", "verify", "sms")
            if self.settings.success_url_contains:
                return "authenticated" if self.settings.success_url_contains in url else "waiting"
            if self.settings.success_selector:
                node = self._page.locator(self.settings.success_selector).first
                return "authenticated" if node.count() and node.is_visible(timeout=500) else "waiting"
            return "authenticated" if self._page.url.startswith("https://") and not any(x in url for x in blocked) and self._page.url.rstrip("/") != self.settings.login_url.rstrip("/") else "waiting"
        except Error:
            return "waiting"

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
