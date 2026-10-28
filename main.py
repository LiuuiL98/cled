from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QTimer, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton, QVBoxLayout, QWidget
)

from automation import BrowserAutomation, DEFAULT_LOGIN_URL
from settings import Settings, settings_path


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("国寿 e 店自动启动助手")
        self.resize(680, 430)
        self.settings = Settings.load(settings_path())
        self.automation = BrowserAutomation(self.settings)
        self._build_ui()
        self.timer = QTimer(self)
        self.timer.setInterval(1500)
        self.timer.timeout.connect(self._poll)
        self.statusBar().showMessage("就绪：点击“打开登录页面”启动 Edge")

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        title = QLabel("国寿 e 店自动启动助手")
        title.setStyleSheet("font-size: 22px; font-weight: 650;")
        subtitle = QLabel("启动 Microsoft Edge · 官方扫码登录 · 登录后进入业务页面")
        subtitle.setStyleSheet("color: #667085;")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        form = QFormLayout()
        self.login_url = QLineEdit(self.settings.login_url)
        self.target_url = QLineEdit(self.settings.target_url)
        self.success_url = QLineEdit(self.settings.success_url_contains)
        self.success_selector = QLineEdit(self.settings.success_selector)
        self.keep_profile = QCheckBox("保留 Edge 会话（建议开启）")
        self.keep_profile.setChecked(self.settings.keep_profile)
        form.addRow("扫码登录入口", self.login_url)
        form.addRow("登录后业务页面（可留空）", self.target_url)
        form.addRow("成功 URL 标志（可选）", self.success_url)
        form.addRow("成功页面元素 CSS（可选）", self.success_selector)
        form.addRow("", self.keep_profile)
        layout.addLayout(form)

        note = QLabel(
            "扫码和二次验证由本人在 Edge 中完成。程序只检查页面状态，不读取密码或导出登录凭证。"
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #475467; background: #f2f4f7; padding: 10px; border-radius: 8px;")
        layout.addWidget(note)

        buttons = QHBoxLayout()
        self.open_button = QPushButton("打开登录页面")
        self.open_button.clicked.connect(self.open_login)
        self.stop_button = QPushButton("关闭自动检测")
        self.stop_button.clicked.connect(self.stop_monitor)
        self.save_button = QPushButton("保存设置")
        self.save_button.clicked.connect(self.save_settings)
        self.open_site_button = QPushButton("打开网站")
        self.open_site_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(self.login_url.text().strip())))
        buttons.addWidget(self.open_button)
        buttons.addWidget(self.stop_button)
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.open_site_button)
        layout.addLayout(buttons)
        self.setCentralWidget(root)

    def save_settings(self) -> bool:
        login_url = self.login_url.text().strip()
        target_url = self.target_url.text().strip()
        if not login_url.startswith("https://"):
            QMessageBox.warning(self, "设置无效", "登录入口必须是 HTTPS 地址。")
            return False
        if target_url and not target_url.startswith("https://"):
            QMessageBox.warning(self, "设置无效", "业务页面必须是 HTTPS 地址。")
            return False
        self.settings.login_url = login_url
        self.settings.target_url = target_url
        self.settings.success_url_contains = self.success_url.text().strip()
        self.settings.success_selector = self.success_selector.text().strip()
        self.settings.keep_profile = self.keep_profile.isChecked()
        self.settings.save(settings_path())
        self.statusBar().showMessage("设置已保存")
        return True

    def open_login(self) -> None:
        if not self.save_settings():
            return
        try:
            self.automation.open_login()
            self.timer.start()
            self.statusBar().showMessage("已打开 Edge：请使用官方 APP 扫码并完成验证")
            self.open_button.setEnabled(False)
        except Exception as exc:
            QMessageBox.critical(
                self, "无法启动 Edge",
                f"{exc}\n\n请确认已安装 Microsoft Edge，并允许应用启动浏览器。"
            )

    def _poll(self) -> None:
        try:
            result = self.automation.check_login()
            if result == "authenticated":
                self.timer.stop()
                self.statusBar().showMessage("已检测到登录状态")
                if self.settings.target_url:
                    self.automation.navigate(self.settings.target_url)
                    self.statusBar().showMessage("登录成功，已打开设置的业务页面")
                else:
                    self.statusBar().showMessage("登录成功：当前保留在网站登录后的页面")
                self.open_button.setEnabled(True)
            elif result == "closed":
                self.stop_monitor()
                self.statusBar().showMessage("Edge 已关闭")
        except Exception as exc:
            self.statusBar().showMessage(f"状态检测暂时不可用：{exc}")

    def stop_monitor(self) -> None:
        self.timer.stop()
        self.open_button.setEnabled(True)
        self.statusBar().showMessage("自动检测已停止；Edge 不会因此关闭")

    def closeEvent(self, event) -> None:
        self.timer.stop()
        self.automation.close()
        event.accept()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("ChinaLifeEShopAssistant")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
