# 国寿验证码助手（测试联调版）

版本 0.2.0。Android 与 Windows 工程均为新建实现，不复用旧 CLED 项目架构。

## 当前实现边界

Android 的系统短信广播仍只在手机本机匹配指定中国人寿短信，并显示本机通知；该接收器没有网络调用，也不会把真实收到的短信或验证码发送给 Windows。

为了开发和验证双端配合，0.2.0 增加隔离的**模拟短信联调通道**：
1. Windows 启动局域网测试接收器，生成随机 256-bit 测试令牌。
2. 用户将 Windows 显示的地址和令牌一次性填入 Android 测试页。
3. Android 测试页提供手动编辑的模拟短信正文，只有匹配完整测试模板时才提取 6 位数字。
4. Android 将显式标记为 `GUOSHOU_TEST_SIMULATOR` 的测试数据发送到 Windows。
5. Windows 校验令牌、消息来源标记和 6 位数字格式，然后自动复制到系统剪贴板。

**系统 SMS_RECEIVED 广播处理器与网络发送器相互独立，没有把真实短信接收结果接入发送通道。** 本版本传输为 HTTP 明文局域网测试通道，只能承载模拟数据，不应用于真实验证码、密码或其他敏感信息。

## Android

最低 Android 8.0（API 26），目标 API 35，Java 17。需要 RECEIVE_SMS；Android 13 及以上还需要 POST_NOTIFICATIONS。网络权限仅供手动触发的模拟数据联调。

## Windows

Python 3.11、PySide6。运行后自动启动局域网测试接收器，窗口显示本机地址和随机测试令牌。关闭窗口会隐藏到托盘；托盘菜单可退出。

## 构建

GitHub Actions 分别运行 Android JUnit 测试并构建 Debug APK，以及运行 Windows 单元测试并打包单文件 EXE。产物上传为 Actions Artifacts。

Windows 本地运行：进入 windows 目录，创建 Python 虚拟环境，安装 requirements.txt，然后执行 `python main.py`。
