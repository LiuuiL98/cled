from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Optional

from playwright.sync_api import BrowserContext, Error, Page, Playwright, sync_playwright

from settings import Settings, app_data_dir

DEFAULT_LOGIN_URL = "https://elearningbluefe.e-chinalife.com/els/learner-studentpc-fe/"


class BrowserAutomation:
    """Controls a dedicated Edge profile; never reads cookies or credentials."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._playwright: Optional[Playwright] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    @property
    def profile_dir(self) -> Path:
        return app_data_dir() / "edge-profile"

    def open_login(self) -> None:
        if self._page and not self._page.is_closed():
            self._page.goto(self.settings.login_url, wait_until="domcontentloaded")
            return
        self._playwright = sync_playwright().start()
        profile = self.profile_dir
        profile.mkdir(parents=True, exist_ok=True)
        launch_args = {
            "user_data_dir": str(profile),
            "headless": False,
            "viewport": None,
            "args": ["--start-maximized"],
        }
        try:
            self._context = self._playwright.chromium.launch_persistent_context(
                channel="msedge", **launch_args
            )
        except Error as exc:
            self._playwright.stop()
            self._playwright = None
            raise RuntimeError(
                "Playwright 无法通过 channel=msedge 启动 Microsoft Edge。"
                "请安装最新版 Edge，并关闭正在占用本工具专用 Edge 配置目录的残留进程。"
            ) from exc
        self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
        self._page.goto(self.settings.login_url, wait_until="domcontentloaded", timeout=60000)

    def check_login(self) -> str:
        if not self._page or self._page.is_closed():
            return "closed"
        try:
            current_url = self._page.url
            # Explicit URL marker is the most reliable configurable signal.
            if self.settings.success_url_contains:
                if self.settings.success_url_contains in current_url:
                    return "authenticated"
                return "waiting"
            # Optional site-specific marker set only after verifying the real DOM.
            if self.settings.success_selector:
                locator = self._page.locator(self.settings.success_selector).first
                if locator.count() and locator.is_visible(timeout=500):
                    return "authenticated"
                return "waiting"
            # Safe fallback: page has left the login route. This can require
            # configuring a URL marker if the site uses SPA routing.
            login_path = self.settings.login_url.rstrip("/")
            if current_url.rstrip("/") != login_path and current_url.startswith("https://"):
                return "authenticated"
            return "waiting"
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
