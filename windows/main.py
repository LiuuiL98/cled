"""Manual six-digit clipboard utility. No network receiver is implemented."""
import sys

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QAction, QGuiApplication, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMenu,
    QPushButton, QStyle, QSystemTrayIcon, QVBoxLayout, QWidget,
)

from code_matcher import is_valid_code


class ClipboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("国寿验证码剪贴板")
        self.setMinimumWidth(360)
        self.last_copied = ""

        root = QWidget(self)
        layout = QVBoxLayout(root)
        title = QLabel("国寿验证码剪贴板")
        title.setStyleSheet("font-size: 20px; font-weight: 600;")
        layout.addWidget(title)
        description = QLabel("手动输入或粘贴 6 位验证码。输入完整后会自动复制到系统剪贴板。")
        description.setWordWrap(True)
        layout.addWidget(description)

        self.code = QLineEdit()
        self.code.setMaxLength(6)
        self.code.setPlaceholderText("输入 6 位数字验证码")
        self.code.setValidator(QRegularExpressionValidator(QRegularExpression(r"[0-9]{0,6}")))
        self.code.setClearButtonEnabled(True)
        self.code.textChanged.connect(self.on_text_changed)
        layout.addWidget(self.code)

        self.status = QLabel("等待输入")
        layout.addWidget(self.status)
        row = QHBoxLayout()
        copy_button = QPushButton("复制")
        copy_button.clicked.connect(self.copy_code)
        clear_button = QPushButton("清空输入")
        clear_button.clicked.connect(self.code.clear)
        clipboard_button = QPushButton("清空剪贴板")
        clipboard_button.clicked.connect(self.clear_clipboard)
        row.addWidget(copy_button)
        row.addWidget(clear_button)
        row.addWidget(clipboard_button)
        layout.addLayout(row)

        privacy = QLabel("不联网、不接收短信、不保存验证码。关闭窗口会隐藏到系统托盘。")
        privacy.setWordWrap(True)
        privacy.setStyleSheet("color: #777; font-size: 11px;")
        layout.addWidget(privacy)
        self.setCentralWidget(root)

        self.tray = QSystemTrayIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon), self)
        self.tray.setToolTip("国寿验证码剪贴板")
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

    def on_text_changed(self, value):
        if is_valid_code(value):
            self.copy_code()

    def copy_code(self):
        value = self.code.text()
        if not is_valid_code(value):
            self.status.setText("请输入完整的 6 位数字")
            return
        QGuiApplication.clipboard().setText(value)
        self.last_copied = value
        self.status.setText("已复制到系统剪贴板")
        self.tray.showMessage("验证码已复制", "6 位验证码已写入剪贴板。")

    def clear_clipboard(self):
        clipboard = QGuiApplication.clipboard()
        if self.last_copied and clipboard.text() == self.last_copied:
            clipboard.clear()
            self.status.setText("本程序复制的剪贴板内容已清空")
        else:
            self.status.setText("剪贴板内容已变化，未清除其他内容")

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


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("GuoshouCodeClipboard")
    app.setQuitOnLastWindowClosed(False)
    window = ClipboardWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
