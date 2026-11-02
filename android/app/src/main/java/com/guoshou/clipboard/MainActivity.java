package com.guoshou.clipboard;

import android.Manifest;
import android.app.Activity;
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

import java.util.ArrayList;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class MainActivity extends Activity {
    private static final int REQUEST_PERMISSIONS = 100;
    private static final String PREFS = "test_link_preferences";
    private TextView status;
    private EditText hostInput;
    private EditText tokenInput;
    private EditText sampleInput;
    private final ExecutorService networkExecutor = Executors.newSingleThreadExecutor();

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);

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
        intro.setText("真实短信只在本机匹配并显示通知。下面的联调区只发送你手动填写的模拟短信样本，不会把系统收到的真实短信转发出去。");
        intro.setTextSize(14);
        root.addView(intro);

        addLabel(root, "Windows 电脑地址（IP:端口）");
        hostInput = new EditText(this);
        hostInput.setSingleLine(true);
        hostInput.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        hostInput.setHint("例如 192.168.1.20:8765");
        hostInput.setText(prefs.getString("host", ""));
        root.addView(hostInput);

        addLabel(root, "测试配对令牌");
        tokenInput = new EditText(this);
        tokenInput.setSingleLine(true);
        tokenInput.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD);
        tokenInput.setHint("从 Windows 测试接收器复制");
        tokenInput.setText(prefs.getString("token", ""));
        root.addView(tokenInput);

        Button save = new Button(this);
        save.setText("保存测试配对信息");
        save.setOnClickListener(v -> {
            prefs.edit()
                .putString("host", hostInput.getText().toString().trim())
                .putString("token", tokenInput.getText().toString().trim())
                .apply();
            updateStatus("测试配对信息已保存在本机");
        });
        root.addView(save);

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
        privacy.setText("测试通道：HTTP 局域网直连 + 随机令牌。仅用于模拟数据，不是生产级安全传输。不要输入真实验证码或其他敏感信息。");
        privacy.setTextSize(12);
        root.addView(privacy);

        Button request = new Button(this);
        request.setText("检查并申请短信通知权限");
        request.setOnClickListener(v -> requestPermissionsIfNeeded());
        root.addView(request);

        setContentView(root);
        requestPermissionsIfNeeded();
    }

    private void addLabel(LinearLayout root, String text) {
        TextView label = new TextView(this);
        label.setText(text);
        label.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        label.setPadding(0, Math.round(12 * getResources().getDisplayMetrics().density), 0, 0);
        root.addView(label);
    }

    private void sendTestCode() {
        String host = hostInput.getText().toString().trim();
        String token = tokenInput.getText().toString().trim();
        String sample = sampleInput.getText().toString();
        String code = SmsTemplateParser.extractCode(sample);

        if (host.isEmpty() || token.isEmpty()) {
            updateStatus("请先填写 Windows 地址和测试配对令牌");
            return;
        }
        if (code == null) {
            updateStatus("模拟短信格式不匹配，未发送任何内容");
            return;
        }

        getSharedPreferences(PREFS, MODE_PRIVATE).edit()
            .putString("host", host)
            .putString("token", token)
            .apply();

        updateStatus("正在发送模拟测试数据…");
        networkExecutor.execute(() -> {
            String result = TestRelayClient.send(host, token, code);
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
