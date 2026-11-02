package com.guoshou.clipboard;

import android.Manifest;
import android.app.Activity;
import android.os.Build;
import android.os.Bundle;
import android.content.pm.PackageManager;
import android.graphics.Typeface;
import android.view.Gravity;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.util.ArrayList;

public final class MainActivity extends Activity {
    private static final int REQUEST_PERMISSIONS = 100;
    private TextView status;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setGravity(Gravity.TOP);
        int pad = Math.round(24 * getResources().getDisplayMetrics().density);
        root.setPadding(pad, pad, pad, pad);

        TextView title = new TextView(this);
        title.setText("国寿验证码助手");
        title.setTextSize(24);
        title.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        root.addView(title);

        TextView intro = new TextView(this);
        intro.setText("系统收到新短信时会唤醒本应用。应用仅识别指定的中国人寿短信模板，匹配后显示本机通知。点击通知中的“复制验证码”即可复制。\n\n不会联网、不会转发、不会读取历史短信或保存短信正文。");
        intro.setTextSize(15);
        root.addView(intro);

        status = new TextView(this);
        status.setTextSize(14);
        root.addView(status, new LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        Button request = new Button(this);
        request.setText("检查并申请权限");
        request.setOnClickListener(v -> requestPermissionsIfNeeded());
        root.addView(request);
        setContentView(root);
        requestPermissionsIfNeeded();
    }

    @Override
    protected void onResume() {
        super.onResume();
        updateStatus();
    }

    private void requestPermissionsIfNeeded() {
        ArrayList<String> required = new ArrayList<>();
        if (checkSelfPermission(Manifest.permission.RECEIVE_SMS) != PackageManager.PERMISSION_GRANTED)
            required.add(Manifest.permission.RECEIVE_SMS);
        if (Build.VERSION.SDK_INT >= 33
                && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED)
            required.add(Manifest.permission.POST_NOTIFICATIONS);
        if (!required.isEmpty()) requestPermissions(required.toArray(new String[0]), REQUEST_PERMISSIONS);
        else updateStatus();
    }

    private void updateStatus() {
        if (status == null) return;
        boolean sms = checkSelfPermission(Manifest.permission.RECEIVE_SMS) == PackageManager.PERMISSION_GRANTED;
        boolean notification = Build.VERSION.SDK_INT < 33
                || checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED;
        status.setText("短信接收：" + (sms ? "已授权" : "未授权")
            + "\n通知：" + (notification ? "已授权" : "未授权")
            + (!sms ? "\n短信权限未获准时无法自动识别新短信。" : ""));
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] results) {
        super.onRequestPermissionsResult(requestCode, permissions, results);
        if (requestCode == REQUEST_PERMISSIONS) updateStatus();
    }
}
