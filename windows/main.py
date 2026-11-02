"""Windows tray utility with a QR-pairable test-only LAN receiver."""
import sys
from io import BytesIO

import qrcode
from PySide6.QtCore import QObject, Qt, Signal, QRegularExpression
from PySide6.QtGui import QAction, QGuiApplication, QPixmap, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMenu,
    QPushButton, QStyle, QSystemTrayIcon, QVBoxLayout, QWidget,
)

from code_matcher import is_valid_code
from lan_test_receiver import LanTestReceiver, find_lan_ipv4
from pairing_qr import build_pairing_uri


class ReceiverSignals(QObject):
    code_received = Signal(str)


class ClipboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("国寿验证码助手 · Windows 测试端")
        self.setMinimumWidth(480)
        self.last_copied = ""
        self.signals = ReceiverSignals()
        self.signals.code_received.connect(self.on_test_code_received)
        self.receiver = LanTestReceiver(self.signals.code_received.emit)
        self.lan_host = find_lan_ipv4()

        root = QWidget(self)
        layout = QVBoxLayout(root)
        title = QLabel("国寿验证码助手")
        title.setStyleSheet("font-size: 20px; font-weight: 600;")
        layout.addWidget(title)

        intro = QLabel("Android 打开应用后点击“扫描 Windows 配对二维码”。扫码成功后，测试地址和令牌会自动保存到手机。")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        qr = self.create_pairing_qr()
        qr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(qr)

        layout.addWidget(QLabel("本机局域网地址"))
        self.address = QLineEdit(f"{self.lan_host}:{self.receiver.port}")
        self.address.setReadOnly(True)
        layout.addWidget(self.address)

        refresh = QPushButton("刷新配对二维码")
        refresh.clicked.connect(self.refresh_pairing_qr)
        layout.addWidget(refresh)

        self.server_status = QLabel(f"测试接收器监听中：0.0.0.0:{self.receiver.port}")
        layout.addWidget(self.server_status)

        layout.addWidget(QLabel("最近一次接收的模拟验证码"))
        self.code = QLineEdit()
        self.code.setReadOnly(True)
        self.code.setPlaceholderText("等待 Android 测试端发送")
        layout.addWidget(self.code)

        description = QLabel("也可以在电脑上手动输入 6 位数字，输入完整后自动复制。")
        description.setWordWrap(True)
        layout.addWidget(description)

        self.manual_code = QLineEdit()
        self.manual_code.setMaxLength(6)
        self.manual_code.setPlaceholderText("手动输入 6 位数字")
        self.manual_code.setValidator(QRegularExpressionValidator(QRegularExpression(r"[0-9]{0,6}")))
        self.manual_code.textChanged.connect(self.on_manual_text_changed)
        layout.addWidget(self.manual_code)

        row = QHBoxLayout()
        clear_button = QPushButton("清空输入")
        clear_button.clicked.connect(self.manual_code.clear)
        clipboard_button = QPushButton("清空本程序剪贴板")
        clipboard_button.clicked.connect(self.clear_clipboard)
        row.addWidget(clear_button)
        row.addWidget(clipboard_button)
        layout.addLayout(row)

        privacy = QLabel("测试模式：HTTP 明文局域网传输，仅用于模拟数据。不要在此测试通道传输真实验证码、密码或其他敏感信息。")
        privacy.setWordWrap(True)
        privacy.setStyleSheet("color: #777; font-size: 11px;")
        layout.addWidget(privacy)
        self.setCentralWidget(root)

        self.tray = QSystemTrayIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon), self)
        self.tray.setToolTip("国寿验证码助手 · 测试端")
        menu = QMenu()
        show = QAction("打开窗口", self)
        show.triggered.connect(self.showNormal)
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(show)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self.on_tray_activated)
        self.tray.show()

    def create_pairing_qr(self):
        self.qr_label = QLabel()
        self.qr_label.setMinimumSize(250, 250)
        self.qr_label.setMaximumSize(250, 250)
        self.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.refresh_pairing_qr()
        return self.qr_label

    def refresh_pairing_qr(self):
        self.lan_host = find_lan_ipv4()
        payload = build_pairing_uri(
            self.lan_host, self.receiver.port, self.receiver.token)
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=4,
        )
        qr.add_data(payload)
        qr.make(fit=True)
        image = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        pixmap = QPixmap()
        if not pixmap.loadFromData(buffer.getvalue(), "PNG"):
            raise RuntimeError("Could not render pairing QR code")
        self.qr_label.setPixmap(pixmap.scaled(
            232, 232,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ))
        if hasattr(self, "address"):
            self.address.setText(f"{self.lan_host}:{self.receiver.port}")
        if hasattr(self, "server_status"):
            self.server_status.setText("测试接收器监听中；二维码已刷新")

    def on_test_code_received(self, value: str):
        if not is_valid_code(value):
            return
        QGuiApplication.clipboard().setText(value)
        self.last_copied = value
        self.code.setText(value)
        self.server_status.setText("已接收模拟测试数据，并自动复制到剪贴板")
        self.tray.showMessage("测试验证码已复制", "模拟验证码已写入系统剪贴板。")

    def on_manual_text_changed(self, value):
        if is_valid_code(value):
            QGuiApplication.clipboard().setText(value)
            self.last_copied = value

    def clear_clipboard(self):
        clipboard = QGuiApplication.clipboard()
        if self.last_copied and clipboard.text() == self.last_copied:
            clipboard.clear()
            self.server_status.setText("本程序复制的剪贴板内容已清空")
        else:
            self.server_status.setText("剪贴板内容已变化，未清除其他内容")

    def on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                      QSystemTrayIcon.ActivationReason.DoubleClick):
            self.showNormal()
            self.raise_()
            self.activateWindow()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray.showMessage("程序仍在运行", "可从系统托盘菜单选择退出。")

    def shutdown(self):
        self.receiver.stop()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("GuoshouCodeClipboard")
    app.setQuitOnLastWindowClosed(False)
    window = ClipboardWindow()
    app.aboutToQuit.connect(window.shutdown)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
