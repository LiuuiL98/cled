# 国寿 e 店自动登录助手

Windows + Android 双端工具。Windows 端启动 Microsoft Edge，打开国寿 e 店入口，识别登录面板右上角的折角锁头图标并切换至账号密码登录，填写本机保存的账号密码；Android 端通过已配对的局域网通道把验证码发送给 Windows，Windows 再尝试填写验证码并提交。

## 默认网站入口

https://elearningbluefe.e-chinalife.com/els/learner-studentpc-fe/

截图中的账号密码入口是登录面板右上角折角区域内的锁头图标，不是文字按钮。代码通过“易学堂登录”和“云助理登录”两个标签定位登录面板，再点击其右上角对应位置。无法唯一定位面板时会停止，不会猜测点击。

## Windows 端

- 使用 Playwright 启动 Microsoft Edge 独立用户配置目录。
- 自动切换到账号密码登录模式。
- 账号保存在本地设置文件；密码仅通过 Windows Credential Manager（keyring Windows backend）保存，不写入仓库或普通配置文件。
- 自动识别唯一账号、密码输入框并填写。
- 仅当页面存在唯一的“登录 / 立即登录 / 确认登录”按钮时才提交。
- 收到验证码后，尝试填写唯一明确的验证码输入框并提交。
- 登录成功后可跳转到自定义业务页面。

网站 DOM 尚未在本机真实登录账号环境验证。若该入口坐标布局或字段结构因浏览器缩放、窗口尺寸或网站更新而变化，程序可能提示无法唯一识别；此时应根据实际页面更新定位器，不应强行点击。

## Android 配对与验证码

手机与电脑需要连接同一可信 Wi-Fi。Android 助手扫描 Windows 窗口的配对二维码，随后把验证码加密发送到电脑。电脑端每次启动生成新的 AES-GCM 密钥，配对信息通过二维码提供给手机。

**当前仓库 Android APK 仍提供短信分享/剪贴板粘贴后发送的入口，尚未实现免逐条确认的后台短信自动读取。** 这点需要在 OPPO PEAM00（Android 12 / ColorOS 12.1）上进一步验证平台权限和可行实现后才能交付，当前不能把它当成已完成。

## 本地开发

Windows：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Android 使用 JDK 17、Android SDK 35 和 Gradle 8.9：

```bash
gradle :app:assembleDebug
```

APK 输出：`app/build/outputs/apk/debug/app-debug.apk`

## GitHub Actions

推送到 main 会同时：
- 安装 Python 依赖、运行语法检查和单元测试、打包 Windows EXE。
- 配置 Android SDK、构建 Android Debug APK。
- 上传 Windows 和 Android 两个构建 Artifacts。

从仓库 Actions 的对应运行记录下载构建产物。
