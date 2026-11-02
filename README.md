# 国寿验证码助手（扫码测试联调版）

版本 0.3.0。Android 与 Windows 工程均为独立新建实现。

## 扫码配对

1. 启动 Windows 程序，显示二维码和本机局域网地址。
2. Android 打开程序，点击“扫描 Windows 配对二维码”。
3. 首次扫描时允许相机权限。
4. 扫码成功后，Android 自动解析并保存 Windows IPv4 地址、端口和随机测试令牌。
5. Windows 重启后使用保存在当前用户配置目录的相同令牌。电脑 IP 改变时，在 Windows 点击“刷新配对二维码”，再用 Android 重新扫描。

二维码使用应用专属 URI：`guoshou-test://pair`。Android 仅接受带正确 scheme、私有 IPv4 地址、有效端口和 256-bit 十六进制令牌的二维码。没有必要再手动复制 IP 或令牌。

## 测试通道边界

Android 的系统短信广播仍只在手机本机匹配指定中国人寿短信并显示本机通知；它没有网络调用，不会将真实收到的短信或验证码发送给 Windows。

双端网络通道只发送 Android 测试页中手动填写的模拟短信样本，消息标记为 `GUOSHOU_TEST_SIMULATOR`。Windows 校验随机测试令牌、来源标记和 6 位 ASCII 数字后自动复制到剪贴板。

本版本仅为局域网联调工具，传输为 HTTP 明文，不得用于真实验证码、密码或其他敏感信息。

## Android

最低 Android 8.0（API 26），目标 API 35，Java 17。使用 JourneyApps ZXing Embedded 4.3.0 扫描二维码。首次扫码需要相机权限；短信接收仍需要 RECEIVE_SMS，Android 13 及以上需要 POST_NOTIFICATIONS。

## Windows

Python 3.11、PySide6、qrcode。启动后运行局域网测试接收器并显示配对二维码。测试令牌保存在 `%APPDATA%/GuoshouCodeClipboard/test-token.txt`。关闭主窗口会隐藏到系统托盘。

## 构建

GitHub Actions 运行 Android JUnit 测试并构建 Debug APK，同时运行 Windows 单元测试并打包单文件 EXE。
