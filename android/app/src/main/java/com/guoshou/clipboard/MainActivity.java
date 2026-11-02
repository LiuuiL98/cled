package com.guoshou.clipboard;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Build;
import android.os.Bundle;
import android.content.pm.PackageManager;
import android.graphics.Typeface;
import android.text.InputType;
import android.view.Gravity;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import com.google.zxing.integration.android.IntentIntegrator;
import com.google.zxing.integration.android.IntentResult;

import java.util.ArrayList;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class MainActivity extends Activity {
    private static final int REQUEST_PERMISSIONS = 100;
    private static final String PREFS = "test_link_preferences";
    private TextView status;
    private TextView pairingStatus;
    private EditText sampleInput;
    private final ExecutorService networkExecutor = Executors.newSingleThreadExecutor();

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setGravity(Gravity.TOP);
        int pad = Math.round(20 * getResources().getDisplayMetrics().density);
        root.setPadding(pad, pad, pad, pad);

        TextView title = new TextView(this);
        title.setText("国寿验证码助手 · 测试联调");
        title.setTextSize(22);
        title.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        root.addView(title);

        TextView intro = new TextView(this);
        intro.setText("真实短信只在本机匹配并显示通知。扫码仅用于配置 Windows 测试接收器；联调发送区只发送手动编辑的模拟短信样本。");
        intro.setTextSize(14);
        root.addView(intro);

        addLabel(root, "Windows 测试端配对");
        pairingStatus = new TextView(this);
        pairingStatus.setTextSize(14);
        root.addView(pairingStatus);
        Button scan = new Button(this);
        scan.setText("扫描 Windows 配对二维码");
        scan.setOnClickListener(v -> startQrScan());
        root.addView(scan);
        Button clearPairing = new Button(this);
        clearPairing.setText("解除配对");
        clearPairing.setOnClickListener(v -> {
            getSharedPreferences(PREFS, MODE_PRIVATE).edit().clear().apply();
            updatePairingStatus();
            updateStatus("已清除本机保存的测试配对信息");
        });
        root.addView(clearPairing);

        addLabel(root, "模拟短信正文（仅用于联调）");
        sampleInput = new EditText(this);
        sampleInput.setMinLines(3);
        sampleInput.setGravity(Gravity.TOP | Gravity.START);
        sampleInput.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_MULTI_LINE);
        sampleInput.setText("【中国人寿】尊敬的用户，您的验证码：693754，请于5分钟内输入，请勿将验证码泄露给他人，谢谢您的使用！");
        root.addView(sampleInput, new LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        Button send = new Button(this);
        send.setText("发送模拟短信中的验证码");
        send.setOnClickListener(v -> sendTestCode());
        root.addView(send);

        status = new TextView(this);
        status.setTextSize(14);
        status.setPadding(0, pad / 2, 0, 0);
        root.addView(status, new LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        TextView privacy = new TextView(this);
        privacy.setText("联调通道仅用于模拟数据：HTTP 局域网直连 + 随机测试令牌。不要在此通道发送真实验证码、密码或其他敏感信息。");
        privacy.setTextSize(12);
        root.addView(privacy);

        Button request = new Button(this);
        request.setText("检查并申请短信通知权限");
        request.setOnClickListener(v -> requestPermissionsIfNeeded());
        root.addView(request);

        setContentView(root);
        updatePairingStatus();
        requestPermissionsIfNeeded();
    }

    private void addLabel(LinearLayout root, String text) {
        TextView label = new TextView(this);
        label.setText(text);
        label.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        label.setPadding(0, Math.round(12 * getResources().getDisplayMetrics().density), 0, 0);
        root.addView(label);
    }

    private void startQrScan() {
        IntentIntegrator integrator = new IntentIntegrator(this);
        integrator.setDesiredBarcodeFormats(IntentIntegrator.QR_CODE);
        integrator.setPrompt("扫描 Windows 测试端窗口中的二维码");
        integrator.setBeepEnabled(false);
        integrator.setOrientationLocked(true);
        integrator.initiateScan();
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        IntentResult result = IntentIntegrator.parseActivityResult(requestCode, resultCode, data);
        if (result != null) {
            if (result.getContents() == null) {
                updateStatus("已取消扫码");
            } else {
                savePairing(result.getContents());
            }
            return;
        }
        super.onActivityResult(requestCode, resultCode, data);
    }

    private void savePairing(String raw) {
        PairingPayload.PairingInfo info = PairingPayload.parse(raw);
        if (info == null) {
            Toast.makeText(this, "二维码无效或不是本测试程序的配对码", Toast.LENGTH_LONG).show();
            updateStatus("扫码失败：二维码格式或地址校验未通过");
            return;
        }
        getSharedPreferences(PREFS, MODE_PRIVATE).edit()
            .putString("host", info.host)
            .putInt("port", info.port)
            .putString("token", info.token)
            .apply();
        updatePairingStatus();
        updateStatus("配对成功，可以发送模拟测试数据");
        Toast.makeText(this, "Windows 测试端配对成功", Toast.LENGTH_SHORT).show();
    }

    private void updatePairingStatus() {
        if (pairingStatus == null) return;
        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        String host = prefs.getString("host", "");
        int port = prefs.getInt("port", 0);
        String token = prefs.getString("token", "");
        boolean paired = !host.isEmpty() && port > 0 && token.matches("[a-fA-F0-9]{64}");
        pairingStatus.setText(paired
            ? "已配对：" + host + ":" + port + "（配置保存在本机）"
            : "尚未配对，请扫描 Windows 窗口中的二维码");
    }

    private void sendTestCode() {
        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        String host = prefs.getString("host", "");
        int port = prefs.getInt("port", 0);
        String token = prefs.getString("token", "");
        String sample = sampleInput.getText().toString();
        String code = SmsTemplateParser.extractCode(sample);

        if (host.isEmpty() || port <= 0 || token.isEmpty()) {
            updateStatus("请先扫描 Windows 配对二维码");
            return;
        }
        if (code == null) {
            updateStatus("模拟短信格式不匹配，未发送任何内容");
            return;
        }

        updateStatus("正在发送模拟测试数据…");
        networkExecutor.execute(() -> {
            String result = TestRelayClient.send(host + ":" + port, token, code);
            runOnUiThread(() -> updateStatus(result));
        });
    }

    private void requestPermissionsIfNeeded() {
        ArrayList<String> required = new ArrayList<>();
        if (checkSelfPermission(Manifest.permission.RECEIVE_SMS) != PackageManager.PERMISSION_GRANTED)
            required.add(Manifest.permission.RECEIVE_SMS);
        if (Build.VERSION.SDK_INT >= 33
                && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED)
            required.add(Manifest.permission.POST_NOTIFICATIONS);
        if (!required.isEmpty()) requestPermissions(required.toArray(new String[0]), REQUEST_PERMISSIONS);
        else updatePermissionStatus();
    }

    private void updatePermissionStatus() {
        if (status == null) return;
        boolean sms = checkSelfPermission(Manifest.permission.RECEIVE_SMS) == PackageManager.PERMISSION_GRANTED;
        boolean notification = Build.VERSION.SDK_INT < 33
                || checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED;
        updateStatus("短信接收：" + (sms ? "已授权" : "未授权")
            + "；通知：" + (notification ? "已授权" : "未授权"));
    }

    private void updateStatus(String message) {
        if (status != null) status.setText(message);
    }

    @Override
    protected void onResume() {
        super.onResume();
        updatePermissionStatus();
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] results) {
        super.onRequestPermissionsResult(requestCode, permissions, results);
        if (requestCode == REQUEST_PERMISSIONS) updatePermissionStatus();
    }

    @Override
    protected void onDestroy() {
        networkExecutor.shutdownNow();
        super.onDestroy();
    }
}
