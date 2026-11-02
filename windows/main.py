"""Windows tray utility with a test-only LAN receiver."""
import sys

from PySide6.QtCore import QObject, Signal, QRegularExpression
from PySide6.QtGui import QAction, QGuiApplication, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMenu,
    QPushButton, QStyle, QSystemTrayIcon, QVBoxLayout, QWidget,
)

from code_matcher import is_valid_code
from lan_test_receiver import LanTestReceiver, find_lan_ipv4


class ReceiverSignals(QObject):
    code_received = Signal(str)


class ClipboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("国寿验证码助手 · Windows 测试端")
        self.setMinimumWidth(470)
        self.last_copied = ""
        self.signals = ReceiverSignals()
        self.signals.code_received.connect(self.on_test_code_received)
        self.receiver = LanTestReceiver(self.signals.code_received.emit)

        root = QWidget(self)
        layout = QVBoxLayout(root)
        title = QLabel("国寿验证码助手")
        title.setStyleSheet("font-size: 20px; font-weight: 600;")
        layout.addWidget(title)

        intro = QLabel("Windows 测试接收器已启动。它只接受带正确随机令牌、且 source=GUOSHOU_TEST_SIMULATOR 的模拟数据。")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        layout.addWidget(QLabel("本机局域网地址（填入 Android 测试端）"))
        self.address = QLineEdit(f"{find_lan_ipv4()}:{self.receiver.port}")
        self.address.setReadOnly(True)
        layout.addWidget(self.address)

        layout.addWidget(QLabel("一次性测试配对令牌（复制到 Android）"))
        self.token = QLineEdit(self.receiver.token)
        self.token.setReadOnly(True)
        layout.addWidget(self.token)
        copy_token = QPushButton("复制测试令牌")
        copy_token.clicked.connect(lambda: QGuiApplication.clipboard().setText(self.receiver.token))
        layout.addWidget(copy_token)

        self.server_status = QLabel(f"监听中：0.0.0.0:{self.receiver.port}")
        layout.addWidget(self.server_status)

        layout.addWidget(QLabel("最近一次接收的模拟验证码"))
        self.code = QLineEdit()
        self.code.setReadOnly(True)
        self.code.setPlaceholderText("等待 Android 测试端发送")
        layout.addWidget(self.code)

        description = QLabel("也可以在下面手动输入 6 位数字，输入完整后自动复制。")
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
