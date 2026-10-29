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
        self.resize(800, 720)
        self.settings = Settings.load(settings_path())
        self.browser = BrowserAutomation(self.settings)
        self.bridge = OTPBridge()
        self.pairing = self.bridge.start()
        self.lock_learning_pending = False
        self.pending_username = ""
        self.pending_password = ""
        self.build_ui()
        self.timer = QTimer(self)
        self.timer.setInterval(800)
        self.timer.timeout.connect(self.poll)
        self.sms_request_pending = False
        self.sms_request_ticks = 0
        self.otp_submitted = False
        self.statusBar().showMessage("就绪：先用 Android 助手扫描配对二维码")

    def build_ui(self):
        root = QWidget()
        layout = QVBoxLayout(root)
        title = QLabel("国寿 e 店自动登录助手")
        title.setStyleSheet("font-size:22px;font-weight:650")
        layout.addWidget(title)
        layout.addWidget(QLabel(
            "首次运行校准一次锁头位置，之后自动点击 · 账号密码登录 · 短信验证码自动填写"
        ))

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

        self.maximize_edge = QCheckBox("启动时默认最大化 Edge 窗口")
        self.maximize_edge.setChecked(self.settings.maximize_edge)
        layout.addWidget(self.maximize_edge)

        lock_row = QHBoxLayout()
        self.lock_hint = QLabel()
        self.lock_hint.setWordWrap(True)
        reset_lock = QPushButton("重新校准锁头位置")
        reset_lock.clicked.connect(self.reset_lock_position)
        lock_row.addWidget(self.lock_hint, 1)
        lock_row.addWidget(reset_lock)
        layout.addLayout(lock_row)
        self.refresh_lock_hint()

        row = QHBoxLayout()
        self.qr = QLabel()
        self.qr.setFixedSize(176, 176)
        self.qr.setAlignment(Qt.AlignCenter)
        image = qrcode.make(json.dumps(self.pairing, separators=(",", ":")))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        pixmap = QPixmap()
        pixmap.loadFromData(buffer.getvalue())
        self.qr.setPixmap(pixmap.scaled(
            168, 168, Qt.KeepAspectRatio, Qt.SmoothTransformation
        ))
        pairing_mode = (
            "配对密钥与端口已保存，可跨 Windows 助手重启使用。"
            if self.pairing.get("persistent")
            else "当前使用临时配对信息；若助手重启，请重新扫描二维码。"
        )
        info = QLabel(
            "Android 配对步骤\n"
            "1. 手机与电脑连接同一 Wi-Fi\n"
            "2. 手机助手扫描左侧二维码并启用短信接收权限\n"
            "3. 手机识别验证码后，按手机端当前流程转发到电脑\n\n"
            "电脑地址: " + str(self.pairing["host"]) + ":" + str(self.pairing["port"]) +
            "\n" + pairing_mode
        )
        info.setWordWrap(True)
        row.addWidget(self.qr)
        row.addWidget(info, 1)
        layout.addLayout(row)

        note = QLabel(
            "首次使用：程序打开 Edge 后，请在网页中手动点击一次右上角锁头。"
            "程序确认密码表单出现后会保存该位置；以后自动点击，不再需要人工操作。"
            "收到手机发送到电脑的短信验证码后，程序会自动填入并点击登录。"
            "若遇到额外安全验证或页面结构不唯一，会停止自动操作。"
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
        open_site.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(self.url.text().strip()))
        )
        for button in (start, stop, save, open_site):
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.start_button = start
        self.setCentralWidget(root)

    def refresh_lock_hint(self):
        if self.settings.has_lock_position:
            self.lock_hint.setText(
                "锁头位置：已保存。后续运行将自动使用上次校准的位置。"
            )
        else:
            self.lock_hint.setText(
                "锁头位置：尚未校准。首次启动时需要手动点击一次锁头，之后自动使用。"
            )

    def reset_lock_position(self):
        self.settings.lock_x_ratio = None
        self.settings.lock_y_ratio = None
        self.settings.lock_maximize = None
        self.settings.save(settings_path())
        self.refresh_lock_hint()
        self.statusBar().showMessage(
            "已清除锁头位置；下次启动自动登录时会重新校准一次。"
        )

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
        self.settings.maximize_edge = self.maximize_edge.isChecked()
        self.settings.save(settings_path())
        if self.remember.isChecked() and self.password.text():
            try:
                save_password(self.settings.username, self.password.text())
            except Exception as exc:
                QMessageBox.warning(self, "密码未保存", str(exc))
        return True

    def _finish_account_login(self, message: str):
        self.browser.fill_account_credentials(
            self.pending_username, self.pending_password
        )
        if not self.browser.submit_login():
            raise RuntimeError("账号密码已填写，但未能唯一识别登录按钮。")
        self.sms_request_pending = True
        self.sms_request_ticks = 0
        self.otp_submitted = False
        self.timer.start()
        self.start_button.setEnabled(False)
        self.statusBar().showMessage(
            message + "；账号密码已提交，正在等待页面显示短信验证码入口"
        )

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

        # A saved position belongs to the selected Edge window mode. If the
        # user switches maximize mode, force a fresh one-time calibration.
        if (
            self.settings.has_lock_position
            and self.settings.lock_maximize is not None
            and self.settings.lock_maximize != self.settings.maximize_edge
        ):
            self.settings.lock_x_ratio = None
            self.settings.lock_y_ratio = None
            self.settings.lock_maximize = None
            self.settings.save(settings_path())
            self.refresh_lock_hint()

        self.pending_username = username
        self.pending_password = password
        try:
            self.browser.open_login()
            if not self.settings.has_lock_position:
                self.browser.begin_lock_position_learning()
                self.lock_learning_pending = True
                self.timer.start()
                self.start_button.setEnabled(False)
                self.statusBar().showMessage(
                    "首次校准：请在 Edge 网页中点击一次右上角锁头。"
                    "密码表单出现后会自动保存位置并继续登录。"
                )
                return

            message = self.browser.open_password_login()
            self._finish_account_login(message)
        except Exception as exc:
            self.timer.stop()
            self.start_button.setEnabled(True)
            QMessageBox.critical(self, "无法启动自动登录", str(exc))

    def poll(self):
        if self.lock_learning_pending:
            # Save only after the real click has opened the account/password form.
            if self.browser.has_password_form():
                click = self.browser.read_lock_position_click()
                if click and click.get("width") and click.get("height"):
                    x_ratio = float(click["x"]) / float(click["width"])
                    y_ratio = float(click["y"]) / float(click["height"])
                    if 0.0 <= x_ratio <= 1.0 and 0.0 <= y_ratio <= 1.0:
                        self.settings.lock_x_ratio = x_ratio
                        self.settings.lock_y_ratio = y_ratio
                        self.settings.lock_maximize = self.settings.maximize_edge
                        self.settings.save(settings_path())
                        self.browser.clear_lock_position_click()
                        self.lock_learning_pending = False
                        self.refresh_lock_hint()
                        try:
                            self._finish_account_login("锁头位置已校准并保存")
                        except Exception as exc:
                            self.timer.stop()
                            self.start_button.setEnabled(True)
                            QMessageBox.critical(self, "账号密码登录失败", str(exc))
                        return
            return

        if self.sms_request_pending:
            result = self.browser.request_sms_code()
            if result == "clicked":
                self.sms_request_pending = False
                self.statusBar().showMessage(
                    "已自动点击“获取验证码”，等待手机自动转发短信"
                )
            elif result == "ambiguous":
                self.sms_request_pending = False
                self.statusBar().showMessage(
                    "页面存在多个“获取验证码”候选项，已停止自动点击，请提供页面截图"
                )
            else:
                self.sms_request_ticks += 1
                if self.sms_request_ticks >= 30:
                    self.sms_request_pending = False
                    self.statusBar().showMessage(
                        "暂未找到“获取验证码”按钮；请确认短信验证页面已出现"
                    )

        code = self.bridge.get_latest_code()
        if code:
            self.otp_submitted = False
            if self.browser.fill_otp(code):
                if self.browser.submit_login():
                    self.otp_submitted = True
                    self.statusBar().showMessage(
                        "验证码已自动填写并提交，正在确认登录"
                    )
                else:
                    self.statusBar().showMessage(
                        "验证码已填写，但无法唯一识别提交按钮"
                    )
            else:
                self.statusBar().showMessage(
                    "已收到验证码，但未能唯一识别验证码输入框"
                )
        try:
            result = self.browser.check_login()
            if result == "authenticated" and self.otp_submitted:
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
        self.lock_learning_pending = False
        self.browser.clear_lock_position_click()
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
