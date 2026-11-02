package com.guoshou.clipboard;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

public final class TestRelayClient {
    private TestRelayClient() { }

    public static String send(String hostAndPort, String token, String code) {
        if (hostAndPort == null || !hostAndPort.matches("[A-Za-z0-9.\\-]+(:[0-9]{1,5})?")) {
            return "Windows 地址格式无效";
        }
        if (token == null || !token.matches("[A-Fa-f0-9]{64}")) {
            return "测试令牌格式无效";
        }
        if (code == null || !code.matches("[0-9]{6}")) {
            return "模拟验证码格式无效";
        }

        HttpURLConnection connection = null;
        try {
            URL url = new URL("http://" + hostAndPort + "/test-code");
            connection = (HttpURLConnection) url.openConnection();
            connection.setRequestMethod("POST");
            connection.setConnectTimeout(3000);
            connection.setReadTimeout(3000);
            connection.setDoOutput(true);
            connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            connection.setRequestProperty("X-Test-Token", token);

            JSONObject payload = new JSONObject();
            payload.put("source", "GUOSHOU_TEST_SIMULATOR");
            payload.put("code", code);
            byte[] body = payload.toString().getBytes(StandardCharsets.UTF_8);
            connection.setFixedLengthStreamingMode(body.length);
            try (OutputStream output = connection.getOutputStream()) {
                output.write(body);
            }

            int status = connection.getResponseCode();
            if (status == 200) return "模拟验证码已发送，Windows 应已自动复制";
            InputStream error = connection.getErrorStream();
            if (error != null) {
                try (BufferedReader reader = new BufferedReader(
                        new InputStreamReader(error, StandardCharsets.UTF_8))) {
                    while (reader.readLine() != null) { /* drain error body */ }
                }
            }
            return "Windows 拒绝了测试数据（HTTP " + status + "）";
        } catch (Exception e) {
            return "发送失败：" + e.getClass().getSimpleName() + "；检查同一 Wi-Fi 和防火墙";
        } finally {
            if (connection != null) connection.disconnect();
        }
    }
}
