# 国寿 e 店自动启动助手

Windows 桌面工具：启动 Microsoft Edge 并打开国寿 e 店扫码入口，用户本人完成扫码后，程序通过页面 URL / 可配置标志判断是否进入登录态，并可跳转到自定义业务页面。

> 本工具不采集账号密码、不读取/导出 Cookie、不绕过二维码、短信或其他身份验证。Edge 使用独立的本地用户数据目录保存会话。请仅在你有权访问的账户和设备上使用。

## 默认入口

https://elearningbluefe.e-chinalife.com/els/learner-studentpc-fe/

## 开发运行

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
python main.py
```

首次启动会提示安装 Playwright 浏览器运行时。应用优先使用本机 Microsoft Edge（Playwright channel=edge）；找不到时提示用户安装 Edge。

## 使用

1. 启动程序并点击“打开登录页面”。
2. 在弹出的 Edge 窗口中按网站官方流程扫码并完成所有验证。
3. 本工具监测页面是否离开登录入口；可在“高级设置”中填写明确的登录成功 URL 片段或 DOM 标志。
4. 登录成功后，如设置了业务页面 URL，程序会导航到该地址。

## 会话目录

默认放在用户目录下 `%LOCALAPPDATA%\ChinaLifeEShopAssistant\edge-profile`。不要手动分享此目录，其中可能包含登录会话数据。可在设置中清理个人配置目录（关闭 Edge 后操作）。

## 构建

GitHub Actions 的 Windows 构建会运行静态语法检查、单元测试，并使用 PyInstaller 产出 EXE。构建产物保存在 Actions 的 Artifacts 中。
