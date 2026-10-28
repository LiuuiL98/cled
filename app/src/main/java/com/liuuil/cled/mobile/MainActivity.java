package com.liuuil.cled.mobile;

import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.view.ViewGroup;
import android.view.inputmethod.InputType;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;

import com.google.zxing.integration.android.IntentIntegrator;
import com.google.zxing.integration.android.IntentResult;
import com.journeyapps.barcodescanner.CaptureActivity;

import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.util.Base64;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;

public class MainActivity extends Activity {
    private static final String PREFS = "paired_pc";
    private EditText codeInput;
    private TextView status;
    private String host = "";
    private int port = 0;
    private String keyText = "";

    @Override
    public void onCreate(Bundle state) {
        super.onCreate(state);
        loadPairing();
        buildUi();
        handleIncomingIntent(getIntent());
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        handleIncomingIntent(intent);
    }

    private void buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        int pad = dp(20);
        root.setPadding(pad, pad, pad, pad);

        TextView title = new TextView(this);
        title.setText("国寿验证码助手");
        title.setTextSize(23);
        title.setPadding(0, 0, 0, dp(8));
        root.addView(title);

        TextView desc = new TextView(this);
        desc.setText("从短信应用分享验证码短信到本应用，核对验证码后发送到已配对的电脑。短信内容只在本机临时处理。");
        desc.setTextSize(14);
        root.addView(desc);

        Button pair = new Button(this);
        pair.setText("扫描电脑配对二维码");
        pair.setOnClickListener(v -> scanPairingQr());
        root.addView(pair);

        Button paste = new Button(this);
        paste.setText("从剪贴板粘贴短信");
        paste.setOnClickListener(v -> pasteFromClipboard());
        root.addView(paste);

        TextView label = new TextView(this);
        label.setText("验证码（请核对后发送）");
        label.setPadding(0, dp(14), 0, dp(4));
        root.addView(label);

        codeInput = new EditText(this);
        codeInput.setInputType(InputType.TYPE_CLASS_NUMBER);
        codeInput.setSingleLine(true);
        codeInput.setHint("4–8 位验证码");
        root.addView(codeInput, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        Button send = new Button(this);
        send.setText("确认并发送到电脑");
        send.setOnClickListener(v -> sendCode());
        root.addView(send);

        status = new TextView(this);
        status.setTextSize(13);
        status.setPadding(0, dp(12), 0, 0);
        root.addView(status);

        TextView privacy = new TextView(this);
        privacy.setTextSize(12);
        privacy.setPadding(0, dp(20), 0, 0);
        privacy.setText("隐私说明：本应用不申请读取短信数据库或全部通知的权限，不上传短信原文。验证码通过本次配对密钥加密后，经同一局域网发送到电脑。");
        root.addView(privacy);

        setContentView(root);
        refreshPairStatus();
    }

    private int dp(int value) {
        return (int) (value * getResources().getDisplayMetrics().density + 0.5f);
    }

    private void handleIncomingIntent(Intent intent) {
        if (intent == null || !Intent.ACTION_SEND.equals(intent.getAction())) return;
        if (!"text/plain".equals(intent.getType())) return;
        CharSequence text = intent.getCharSequenceExtra(Intent.EXTRA_TEXT);
        if (text == null) text = intent.getCharSequenceExtra(Intent.EXTRA_SUBJECT);
        if (text != null) {
            String code = extractCode(text.toString());
            if (!code.isEmpty()) {
                codeInput.setText(code);
                status.setText("已从分享内容识别验证码，请核对后点击发送。短信原文不会保存。");
            } else {
                status.setText("未能自动识别验证码，请手动输入短信中的数字验证码。");
            }
        }
    }

    private String extractCode(String message) {
        Pattern contextual = Pattern.compile(
                "(?:验证码|校验码|动态码|verification[\\\\s-]*code|OTP)[^0-9]{0,18}([0-9]{4,8})",
                Pattern.CASE_INSENSITIVE);
        Matcher first = contextual.matcher(message);
        if (first.find()) return first.group(1);

        Pattern digits = Pattern.compile("(?<![0-9])([0-9]{4,8})(?![0-9])");
        Matcher matcher = digits.matcher(message);
        String candidate = "";
        int count = 0;
        while (matcher.find()) {
            candidate = matcher.group(1);
            count++;
            if (count > 1) return "";
        }
        return count == 1 ? candidate : "";
    }

    private void pasteFromClipboard() {
        ClipboardManager manager = (ClipboardManager) getSystemService(CLIPBOARD_SERVICE);
        if (manager == null || !manager.hasPrimaryClip()) {
            status.setText("剪贴板为空。");
            return;
        }
        ClipData clip = manager.getPrimaryClip();
        if (clip == null || clip.getItemCount() == 0) return;
        CharSequence text = clip.getItemAt(0).coerceToText(this);
        String code = extractCode(text == null ? "" : text.toString());
        if (!code.isEmpty()) {
            codeInput.setText(code);
            status.setText("已从剪贴板识别验证码，请核对后发送。");
        } else {
            status.setText("剪贴板中未找到唯一验证码，请手动输入。");
        }
    }

    private void scanPairingQr() {
        IntentIntegrator integrator = new IntentIntegrator(this);
        integrator.setDesiredBarcodeFormats(IntentIntegrator.QR_CODE);
        integrator.setPrompt("扫描电脑端显示的配对二维码");
        integrator.setBeepEnabled(false);
        integrator.setOrientationLocked(false);
        integrator.setCaptureActivity(CaptureActivity.class);
        integrator.initiateScan();
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        IntentResult result = IntentIntegrator.parseActivityResult(requestCode, resultCode, data);
        if (result != null) {
            if (result.getContents() != null) savePairing(result.getContents());
            return;
        }
        super.onActivityResult(requestCode, resultCode, data);
    }

    private void savePairing(String raw) {
        try {
            JSONObject object = new JSONObject(raw);
            if (object.getInt("v") != 1) throw new IllegalArgumentException("版本不支持");
            String newHost = object.getString("host");
            int newPort = object.getInt("port");
            String newKey = object.getString("key");
            if (!newHost.matches("[0-9.]+") || newPort < 1 || newPort > 65535) {
                throw new IllegalArgumentException("电脑地址无效");
            }
            byte[] decoded = Base64.getUrlDecoder().decode(newKey);
            if (decoded.length != 32) throw new IllegalArgumentException("配对密钥无效");
            host = newHost;
            port = newPort;
            keyText = newKey;
            getSharedPreferences(PREFS, MODE_PRIVATE).edit()
                    .putString("host", host).putInt("port", port).putString("key", keyText).apply();
            refreshPairStatus();
        } catch (Exception e) {
            status.setText("配对失败：请扫描电脑端当前显示的二维码。");
        }
    }

    private void loadPairing() {
        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        host = prefs.getString("host", "");
        port = prefs.getInt("port", 0);
        keyText = prefs.getString("key", "");
    }

    private void refreshPairStatus() {
        boolean paired = !host.isEmpty() && port > 0 && !keyText.isEmpty();
        status.setText(paired
                ? "已配对电脑：" + host + ":" + port + "。请分享短信或粘贴验证码。"
                : "尚未配对。请先在电脑助手窗口扫描配对二维码。");
    }

    private void sendCode() {
        String code = codeInput.getText().toString().trim();
        if (!code.matches("[0-9]{4,8}")) {
            status.setText("请输入 4–8 位数字验证码。");
            return;
        }
        if (host.isEmpty() || port <= 0 || keyText.isEmpty()) {
            status.setText("尚未配对电脑，请先扫描电脑端二维码。");
            return;
        }
        status.setText("正在通过加密局域网发送…");
        new Thread(() -> {
            String result = "发送失败，请检查同一 Wi-Fi 和电脑端程序是否运行。";
            try {
                byte[] key = Base64.getUrlDecoder().decode(keyText);
                byte[] nonce = new byte[12];
                new SecureRandom().nextBytes(nonce);
                JSONObject payload = new JSONObject();
                payload.put("code", code);
                payload.put("timestamp", System.currentTimeMillis() / 1000L);

                Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
                cipher.init(Cipher.ENCRYPT_MODE, new SecretKeySpec(key, "AES"),
                        new GCMParameterSpec(128, nonce));
                byte[] encrypted = cipher.doFinal(payload.toString().getBytes(StandardCharsets.UTF_8));

                JSONObject envelope = new JSONObject();
                envelope.put("nonce", Base64.getUrlEncoder().withoutPadding().encodeToString(nonce));
                envelope.put("ciphertext", Base64.getUrlEncoder().withoutPadding().encodeToString(encrypted));

                URL url = new URL("http://" + host + ":" + port + "/otp");
                HttpURLConnection connection = (HttpURLConnection) url.openConnection();
                connection.setRequestMethod("POST");
                connection.setConnectTimeout(5000);
                connection.setReadTimeout(5000);
                connection.setDoOutput(true);
                connection.setRequestProperty("Content-Type", "application/json");
                byte[] body = envelope.toString().getBytes(StandardCharsets.UTF_8);
                connection.setFixedLengthStreamingMode(body.length);
                try (OutputStream output = connection.getOutputStream()) {
                    output.write(body);
                }
                int statusCode = connection.getResponseCode();
                InputStream input = statusCode >= 200 && statusCode < 300
                        ? connection.getInputStream() : connection.getErrorStream();
                if (input != null) {
                    ByteArrayOutputStream response = new ByteArrayOutputStream();
                    byte[] buffer = new byte[512];
                    int count;
                    while ((count = input.read(buffer)) != -1) response.write(buffer, 0, count);
                    input.close();
                }
                connection.disconnect();
                if (statusCode == 200) result = "验证码已加密发送到电脑。请检查网页并自行完成登录。";
                else result = "电脑拒绝了本次验证码，请重新配对后再试。";
            } catch (Exception ignored) {
                // Do not log the code, SMS contents, pairing key, or exception payload.
            }
            final String message = result;
            runOnUiThread(() -> {
                status.setText(message);
                if (message.startsWith("验证码已加密")) codeInput.setText("");
            });
        }, "otp-send").start();
    }
}
