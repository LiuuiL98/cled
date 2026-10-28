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
        try:
            visible_passwords = self._page.locator('input[type="password"]:visible').count()
        except Error:
            visible_passwords = 0
        if visible_passwords == 1:
            return "已检测到账号密码表单，无需再次点击锁头入口"
        ok, message = click_lock_corner_entry(self._page)
        if not ok:
            raise RuntimeError(message)
        return message

    def _visible_inputs(self):
        """Return usable visible inputs from the page and all of its frames."""
        if not self._page or self._page.is_closed():
            return []
        results = []
        for frame in self._page.frames:
            try:
                items = frame.locator("input").evaluate_all(
                    """els => els.map((el, index) => {
                        const style = getComputedStyle(el);
                        const visible = !!el.getClientRects().length &&
                            style.display !== 'none' && style.visibility !== 'hidden' &&
                            style.opacity !== '0';
                        return {
                            index,
                            visible,
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
                for item in items:
                    item["frame"] = frame
                    results.append(item)
            except Error:
                continue
        return results

    def fill_account_credentials(self, username: str, password: str) -> None:
        if not self._page or self._page.is_closed():
            raise RuntimeError("登录页面尚未打开。")

        usable = [
            item for item in self._visible_inputs()
            if item["visible"] and not item["disabled"] and not item["readOnly"]
        ]

        def metadata(item: dict) -> str:
            return " ".join(
                item[key] for key in
                ("name", "id", "placeholder", "aria", "autocomplete")
            ).lower()

        password_fields = [
            item for item in usable
            if item["type"] == "password"
            or item["autocomplete"].lower() == "current-password"
            or any(token in metadata(item) for token in ("密码", "password", "passwd"))
        ]
        # Avoid mistaking a field labelled "密码提示" or a hidden helper for
        # the real password control; the visibility filter is applied above.
        password_fields = [
            item for item in password_fields
            if not any(token in metadata(item) for token in ("confirm", "确认密码", "新密码"))
        ]
        if len(password_fields) != 1:
            raise RuntimeError(
                f"未能定位唯一密码输入框（可见候选数：{len(password_fields)}），已停止自动填写。"
            )

        username_fields = []
        for item in usable:
            combined = metadata(item)
            if item["type"] in ("text", "email", "tel", "number") and any(
                token in combined for token in (
                    "user", "account", "mobile", "phone", "login",
                    "用户名", "账号", "帐号", "账户", "手机号", "工号"
                )
            ) and not any(
                token in combined for token in
                ("otp", "sms", "verify", "验证码", "校验码", "密码", "password")
            ):
                username_fields.append(item)

        if not username_fields:
            candidates = [
                item for item in usable
                if item["type"] in ("text", "email", "tel", "number")
                and item is not password_fields[0]
                and not any(
                    token in metadata(item)
                    for token in ("otp", "sms", "verify", "验证码", "校验码")
                )
            ]
            if len(candidates) == 1:
                username_fields = candidates

        if len(username_fields) != 1:
            raise RuntimeError(
                f"未能定位唯一账号输入框（可见候选数：{len(username_fields)}），已停止自动填写。"
            )

        username_field = username_fields[0]
        password_field = password_fields[0]
        username_field["frame"].locator("input").nth(username_field["index"]).fill(username.strip())
        password_field["frame"].locator("input").nth(password_field["index"]).fill(password)

    def submit_login(self) -> bool:
        if not self._page or self._page.is_closed():
            return False
        candidates = []
        selector = "button,[role='button'],input[type='submit'],input[type='button']"
        for frame in self._page.frames:
            try:
                locator = frame.locator(selector)
                found = locator.evaluate_all(
                    """els => els.map((el, index) => {
                        const text = (el.innerText || el.value || el.getAttribute('aria-label') || '').replace(/\\s+/g, '').trim();
                        const visible = !!el.getClientRects().length &&
                            getComputedStyle(el).display !== 'none' &&
                            getComputedStyle(el).visibility !== 'hidden' && !el.disabled;
                        return {index, text, visible};
                    }).filter(item => item.visible && ['登录', '立即登录', '确认登录'].includes(item.text))"""
                )
                candidates.extend((frame, item["index"]) for item in found)
            except Error:
                continue
        if len(candidates) != 1:
            return False
        frame, index = candidates[0]
        frame.locator(selector).nth(index).click(timeout=5000)
        return True


    def request_sms_code(self) -> str:
        """Click the visible '获取验证码' action once when it is unambiguous."""
        if not self._page or self._page.is_closed():
            return "not_found"
        labels = ("获取验证码", "获取短信验证码", "发送验证码", "发送短信验证码")
        action_selector = "button,[role='button'],a,input[type='button'],input[type='submit']"
        matches = []
        for frame in self._page.frames:
            for label in labels:
                try:
                    locator = frame.locator(action_selector)
                    found = locator.evaluate_all(
                        """(els, expected) => els.map((el, index) => {
                            const text = (el.innerText || el.value || el.getAttribute('aria-label') || '')
                                .replace(/\\s+/g, '').trim();
                            const visible = !!el.getClientRects().length &&
                                getComputedStyle(el).display !== 'none' &&
                                getComputedStyle(el).visibility !== 'hidden' && !el.disabled;
                            return {index, text, visible};
                        }).filter(item => item.visible && item.text === expected)""",
                        label,
                    )
                    matches.extend((frame, action_selector, item["index"], label) for item in found)
                except Error:
                    continue

        # If the control is a styled div/span instead of a semantic button, require
        # a single exact, visible text match across all frames.
        if not matches:
            for frame in self._page.frames:
                for label in labels:
                    try:
                        locator = frame.get_by_text(label, exact=True)
                        visible = []
                        for index in range(min(locator.count(), 10)):
                            try:
                                if locator.nth(index).is_visible():
                                    visible.append(index)
                            except Error:
                                continue
                        matches.extend((frame, None, index, label) for index in visible)
                    except Error:
                        continue

        if not matches:
            return "not_found"
        if len(matches) != 1:
            return "ambiguous"

        frame, selector, index, label = matches[0]
        try:
            if selector:
                frame.locator(selector).nth(index).click(timeout=5000)
            else:
                frame.get_by_text(label, exact=True).nth(index).click(timeout=5000)
            return "clicked"
        except Error:
            return "not_found"

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
