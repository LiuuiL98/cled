from __future__ import annotations

import io
import json
import sys

import qrcode
from PySide6.QtCore import QTimer, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton, QVBoxLayout, QWidget
)

from automation import BrowserAutomation
from credential_store import load_password, save_password
from otp_bridge import OTPBridge
from settings import Settings, settings_path


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("国寿 e 店自动登录助手")
        self.resize(800, 690)
        self.settings = Settings.load(settings_path())
        self.browser = BrowserAutomation(self.settings)
        self.bridge = OTPBridge()
        self.pairing = self.bridge.start()
        self.build_ui()
        self.timer = QTimer(self)
        self.timer.setInterval(800)
        self.timer.timeout.connect(self.poll)
        self.sms_request_pending = False
        self.sms_request_ticks = 0
        self.statusBar().showMessage("就绪：先用 Android 助手扫描配对二维码")

    def build_ui(self):
        root = QWidget()
        layout = QVBoxLayout(root)
        title = QLabel("国寿 e 店自动登录助手")
        title.setStyleSheet("font-size:22px;font-weight:650")
        layout.addWidget(title)
        layout.addWidget(QLabel("自动进入右上角锁头入口 · 账号密码登录 · 短信验证码自动填写"))

        form = QFormLayout()
        self.url = QLineEdit(self.settings.login_url)
        self.username = QLineEdit(self.settings.username)
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        try:
            self.password.setText(load_password(self.settings.username) or "")
        except Exception:
            pass
        self.target = QLineEdit(self.settings.target_url)
        self.success_url = QLineEdit(self.settings.success_url_contains)
        self.success_selector = QLineEdit(self.settings.success_selector)
        form.addRow("国寿 e 店网址", self.url)
        form.addRow("登录账号", self.username)
        form.addRow("登录密码（保存在 Windows 凭据管理器）", self.password)
        form.addRow("登录后目标网址（可选）", self.target)
        form.addRow("登录成功 URL 标志（可选）", self.success_url)
        form.addRow("登录成功页面元素 CSS（可选）", self.success_selector)
        layout.addLayout(form)

        self.remember = QCheckBox("保存密码到本机 Windows 凭据管理器")
        self.remember.setChecked(True)
        layout.addWidget(self.remember)

        row = QHBoxLayout()
        self.qr = QLabel()
        self.qr.setFixedSize(176, 176)
        self.qr.setAlignment(Qt.AlignCenter)
        image = qrcode.make(json.dumps(self.pairing, separators=(",", ":")))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        pixmap = QPixmap()
        pixmap.loadFromData(buffer.getvalue())
        self.qr.setPixmap(pixmap.scaled(168, 168, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        info = QLabel(
            "Android 配对步骤\n"
            "1. 手机与电脑连接同一 Wi-Fi\n"
            "2. 手机助手扫描左侧二维码\n"
            "3. 手机收到验证码后自动加密发送\n\n"
            "电脑地址: " + str(self.pairing["host"]) + ":" + str(self.pairing["port"])
        )
        info.setWordWrap(True)
        row.addWidget(self.qr)
        row.addWidget(info, 1)
        layout.addLayout(row)

        self.otp = QLineEdit()
        self.otp.setReadOnly(True)
        self.otp.setEchoMode(QLineEdit.Password)
        self.otp.setPlaceholderText("收到的验证码短暂显示在这里")
        layout.addWidget(self.otp)

        note = QLabel(
            "程序会点击登录面板右上角锁头，尝试填写唯一账号和密码输入框。"
            "收到短信后自动填入验证码并点击唯一登录按钮。若遇到额外安全验证或页面结构不唯一，会停止自动操作。"
        )
        note.setWordWrap(True)
        note.setStyleSheet("background:#f2f4f7;padding:10px;border-radius:8px")
        layout.addWidget(note)

        buttons = QHBoxLayout()
        start = QPushButton("启动自动登录")
        start.clicked.connect(self.start_login)
        stop = QPushButton("停止检测")
        stop.clicked.connect(self.stop_monitor)
        save = QPushButton("保存设置")
        save.clicked.connect(self.save_settings)
        open_site = QPushButton("打开网站")
        open_site.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(self.url.text().strip())))
        for button in (start, stop, save, open_site):
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.start_button = start
        self.setCentralWidget(root)

    def save_settings(self):
        if not self.url.text().strip().startswith("https://"):
            QMessageBox.warning(self, "设置无效", "网址必须使用 HTTPS。")
            return False
        if self.target.text().strip() and not self.target.text().strip().startswith("https://"):
            QMessageBox.warning(self, "设置无效", "目标网址必须使用 HTTPS。")
            return False
        self.settings.login_url = self.url.text().strip()
        self.settings.target_url = self.target.text().strip()
        self.settings.username = self.username.text().strip()
        self.settings.success_url_contains = self.success_url.text().strip()
        self.settings.success_selector = self.success_selector.text().strip()
        self.settings.save(settings_path())
        if self.remember.isChecked() and self.password.text():
            try:
                save_password(self.settings.username, self.password.text())
            except Exception as exc:
                QMessageBox.warning(self, "密码未保存", str(exc))
        return True

    def start_login(self):
        if not self.save_settings():
            return
        username = self.username.text().strip()
        password = self.password.text()
        if not password:
            try:
                password = load_password(username) or ""
            except Exception:
                password = ""
        if not username or not password:
            QMessageBox.warning(self, "缺少登录信息", "请填写账号和密码。")
            return
        try:
            message = self.browser.open_password_login()
            self.browser.fill_account_credentials(username, password)
            if not self.browser.submit_login():
                raise RuntimeError("账号密码已填写，但未能唯一识别登录按钮。")
            self.sms_request_pending = True
            self.sms_request_ticks = 0
            self.timer.start()
            self.start_button.setEnabled(False)
            self.statusBar().showMessage(message + "；账号密码已提交，正在寻找“获取验证码”按钮")
        except Exception as exc:
            QMessageBox.critical(self, "无法启动自动登录", str(exc))

    def poll(self):
        if self.sms_request_pending:
            result = self.browser.request_sms_code()
            if result == "clicked":
                self.sms_request_pending = False
                self.statusBar().showMessage("已自动点击“获取验证码”，等待手机收到并转发短信")
            elif result == "ambiguous":
                self.sms_request_pending = False
                self.statusBar().showMessage("页面存在多个“获取验证码”候选项，已停止自动点击，请提供页面截图")
            else:
                self.sms_request_ticks += 1
                if self.sms_request_ticks >= 30:
                    self.sms_request_pending = False
                    self.statusBar().showMessage("暂未找到“获取验证码”按钮；请确认短信验证页面已出现")
        code = self.bridge.get_latest_code()
        if code:
            self.otp.setText(code)
            if self.browser.fill_otp(code):
                if self.browser.submit_login():
                    self.statusBar().showMessage("验证码已填写并提交，正在确认登录")
                else:
                    self.statusBar().showMessage("验证码已填写，但无法唯一识别提交按钮")
            else:
                self.statusBar().showMessage("已收到验证码，但未能唯一识别验证码输入框")
        try:
            result = self.browser.check_login()
            if result == "authenticated":
                self.timer.stop()
                if self.settings.target_url:
                    self.browser.navigate(self.settings.target_url)
                    self.statusBar().showMessage("登录成功，已进入目标页面")
                else:
                    self.statusBar().showMessage("检测到登录成功")
                self.start_button.setEnabled(True)
            elif result == "closed":
                self.stop_monitor()
        except Exception as exc:
            self.statusBar().showMessage("状态检测失败: " + str(exc))

    def stop_monitor(self):
        self.timer.stop()
        self.start_button.setEnabled(True)
        self.statusBar().showMessage("自动检测已停止")

    def closeEvent(self, event):
        self.timer.stop()
        self.browser.close()
        self.bridge.stop()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ChinaLifeEShopAssistant")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
