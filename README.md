# 国寿 e 店自动启动助手

Windows + Android 双端工具：Windows 端启动 Microsoft Edge 并打开国寿 e 店；Android 端接收用户主动分享/粘贴的短信文本，在用户确认后通过加密局域网把一次性验证码发送到 Windows。Windows 只尝试填入唯一、明确匹配的验证码输入框，不自动点击登录。

## 默认入口

https://elearningbluefe.e-chinalife.com/els/learner-studentpc-fe/

## Android 端重要说明

Android 16 对通知中的一次性验证码有敏感内容保护。普通通知监听程序可能拿不到验证码原文；短信读取权限也属于受限制权限。因此 Android 首版不申请 READ_SMS、RECEIVE_SMS 或通知访问权限。

使用方法：
1. 手机上安装 Android APK。
2. Windows 助手运行后，手机和电脑连接同一个可信 Wi-Fi。
3. 在 Android 助手中扫描 Windows 窗口的配对二维码。
4. 在短信应用中选择验证码短信，使用“分享”发送给“国寿验证码助手”；也可复制短信后在助手中粘贴。
5. 核对识别出的数字验证码，点击“确认并发送到电脑”。
6. Windows 收到后，只在页面存在唯一明确的验证码输入框时填入；用户检查网页并自行点击登录。

本工具不会读取短信数据库、保存完整短信、上传短信原文或自动提交身份验证。

## Windows 本地开发

\`\`\`powershell
py -3.11 -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
python main.py
\`\`\`

需要安装 Microsoft Edge。Edge 使用应用专用的本地用户数据目录：
\`%LOCALAPPDATA%\\ChinaLifeEShopAssistant\\edge-profile\`

## Android 本地构建

使用 JDK 17、Android SDK 35 和 Gradle 8.9：

\`\`\`bash
gradle :app:assembleDebug
\`\`\`

APK 输出：\`app/build/outputs/apk/debug/app-debug.apk\`

## GitHub Actions

每次推送到 main 后会构建：
- Windows 桌面程序（PyInstaller onedir EXE 文件夹）
- Android Debug APK
- Windows 语法检查及单元测试

在仓库 Actions 的构建记录中下载两个 Artifacts。

## 安全边界

- Android 只接收由用户主动分享或粘贴的短信文本，不监听所有通知。
- 不保存短信原文；只在内存中提取验证码。
- 每次 Windows 启动生成新的 256-bit AES-GCM 配对密钥，并通过二维码提供给 Android。
- 验证码只通过同一局域网传输，载荷使用 AES-GCM 加密并带时间戳/随机 nonce。
- 配对密钥只保存在手机本地；Windows 程序退出后旧配对失效。
- 请仅在你有权使用的账户、设备和可信网络中操作。
