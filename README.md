# 国寿验证码助手（安全本地版）

版本 0.1.0。此分支是一次全新实现，不复用旧 CLED 项目的代码或架构。

## 功能边界

Android 端仅接收系统新短信广播，严格匹配指定的中国人寿模板，匹配后显示本机通知。用户点击通知中的“复制验证码”后，验证码写入 Android 剪贴板。

Windows 端为独立托盘程序。用户手动输入或粘贴 6 位数字后，程序自动复制到 Windows 剪贴板。

两个程序之间没有配对、网络连接、验证码转发或远程控制能力。Android 不读取历史短信、不保存短信正文、不写入验证码日志。Android manifest 不申请 INTERNET 权限。

## Android

最低 Android 8.0（API 26），目标 API 35，Java 17。需要 RECEIVE_SMS；Android 13 及以上还需要 POST_NOTIFICATIONS。RECEIVE_SMS 属于受限权限，实际能否授予取决于 Android 版本、ROM 和安装来源；应用内请求权限不保证系统最终放行。

## Windows

Python 3.11、PySide6。输入或粘贴完整 6 位 ASCII 数字后自动复制。窗口关闭时隐藏到系统托盘，可在托盘菜单退出。

## 构建

GitHub Actions 分别构建 Android Debug APK 和 Windows 单文件 EXE，并运行解析器及输入校验测试。工作流产物会上传为 Actions Artifacts。

Windows 本地运行：进入 windows 目录，创建 Python 虚拟环境，安装 requirements.txt，然后执行 python main.py。
