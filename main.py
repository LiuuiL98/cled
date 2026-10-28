from __future__ import annotations

import io
import sys

import qrcode
from PySide6.QtCore import QTimer, QUrl, Qt
from PySide6.QtGui import QDesktopServices, QGuiApplication, QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton, QVBoxLayout, QWidget
)

from automation import BrowserAutomation
from otp_bridge import OTPBridge
from settings import Settings, settings_path


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("国寿 e 店自动启动助手")
        self.resize(760, 610)
        self.settings = Settings.load(settings_path())
        self.automation = BrowserAutomation(self.settings)
        self.bridge = OTPBridge()
        self.pairing_info = self.bridge.start()
        self._build_ui()
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._poll)
        self.statusBar().showMessage("就绪：先在手机端扫码配对，再打开登录页面")

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        title = QLabel("国寿 e 店自动启动助手")
        title.setStyleSheet("font-size: 22px; font-weight: 650;")
        subtitle = QLabel("Microsoft Edge · 手机短信验证码协同 · 登录后进入业务页面")
        subtitle.setStyleSheet("color: #667085;")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        form = QFormLayout()
        self.login_url = QLineEdit(self.settings.login_url)
        self.target_url = QLineEdit(self.settings.target_url)
        self.success_url = QLineEdit(self.settings.success_url_contains)
        self.success_selector = QLineEdit(self.settings.success_selector)
        form.addRow("扫码/密码登录入口", self.login_url)
        form.addRow("登录后业务页面（可留空）", self.target_url)
        form.addRow("成功 URL 标志（可选）", self.success_url)
        form.addRow("成功页面元素 CSS（可选）", self.success_selector)
        layout.addLayout(form)

        pair_row = QHBoxLayout()
        self.qr_label = QLabel()
        self.qr_label.setFixedSize(176, 176)
        self.qr_label.setAlignment(Qt.AlignCenter)
        qr_data = qrcode.make(__import__("json").dumps(self.pairing_info, separators=(",", ":")))
        buffer = io.BytesIO()
        qr_data.save(buffer, format="PNG")
        pixmap = QPixmap()
        pixmap.loadFromData(buffer.getvalue())
        self.qr_label.setPixmap(pixmap.scaled(168, 168, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        pair_text = QLabel(
            f"手机端配对\n\n"
            f"1. 手机与电脑连接同一 Wi-Fi\n"
            f"2. 打开 Android 助手，点击“扫描电脑二维码”\n"
            f"3. 扫描左侧二维码完成本次配对\n\n"
            f"电脑地址：{self.pairing_info['host']}:{self.pairing_info['port']}\n"
            f"验证码只在本机和局域网内传输，并使用本次运行生成的密钥加密。"
        )
        pair_text.setWordWrap(True)
        pair_text.setStyleSheet("color: #475467;")
        pair_row.addWidget(self.qr_label)
        pair_row.addWidget(pair_text, 1)
        layout.addLayout(pair_row)

        code_row = QHBoxLayout()
        self.code_preview = QLineEdit()
        self.code_preview.setReadOnly(True)
        self.code_preview.setEchoMode(QLineEdit.Password)
        self.code_preview.setPlaceholderText("手机确认发送后，验证码会在这里暂存")
        copy_button = QPushButton("复制验证码")
        copy_button.clicked.connect(self.copy_code)
        code_row.addWidget(self.code_preview, 1)
        code_row.addWidget(copy_button)
        layout.addLayout(code_row)

        note = QLabel(
            "手机端请从短信应用主动分享短信给助手，核对识别出的验证码后再发送。"
            "电脑只会尝试填入唯一且明确的验证码输入框，不会自动点击登录。"
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
        self.open_site_button.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(self.login_url.text().strip()))
        )
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
        self.settings.save(settings_path())
        self.statusBar().showMessage("设置已保存")
        return True

    def open_login(self) -> None:
        if not self.save_settings():
            return
        try:
            self.automation.open_login()
            self.timer.start()
            self.statusBar().showMessage("已打开 Edge：请在网页中输入账号密码并完成手机验证")
            self.open_button.setEnabled(False)
        except Exception as exc:
            QMessageBox.critical(self, "无法启动 Edge", f"{exc}\n\n请确认已安装 Microsoft Edge。")

    def _poll(self) -> None:
        code = self.bridge.get_latest_code()
        if code:
            self.code_preview.setText(code)
            if self.automation.fill_otp(code):
                self.statusBar().showMessage("验证码已填入唯一匹配的输入框，请检查网页并自行提交")
            else:
                self.statusBar().showMessage("已收到验证码，但未找到唯一验证码输入框；可点击复制后手动粘贴")
        try:
            result = self.automation.check_login()
            if result == "authenticated":
                self.timer.stop()
                if self.settings.target_url:
                    self.automation.navigate(self.settings.target_url)
                    self.statusBar().showMessage("检测到登录状态，已打开设置的业务页面")
                else:
                    self.statusBar().showMessage("检测到登录状态：当前停留在登录后的页面")
                self.open_button.setEnabled(True)
            elif result == "closed":
                self.stop_monitor()
                self.statusBar().showMessage("Edge 已关闭")
        except Exception as exc:
            self.statusBar().showMessage(f"状态检测暂时不可用：{exc}")

    def copy_code(self) -> None:
        code = self.code_preview.text().strip()
        if code:
            QGuiApplication.clipboard().setText(code)
            self.statusBar().showMessage("验证码已复制到剪贴板")

    def stop_monitor(self) -> None:
        self.timer.stop()
        self.open_button.setEnabled(True)
        self.statusBar().showMessage("自动检测已停止；Edge 不会因此关闭")

    def closeEvent(self, event) -> None:
        self.timer.stop()
        self.automation.close()
        self.bridge.stop()
        event.accept()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("ChinaLifeEShopAssistant")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
