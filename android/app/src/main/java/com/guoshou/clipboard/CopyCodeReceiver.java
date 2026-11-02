package com.guoshou.clipboard;

import android.content.BroadcastReceiver;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.widget.Toast;

public final class CopyCodeReceiver extends BroadcastReceiver {
    public static final String ACTION_COPY_CODE = "com.guoshou.clipboard.COPY_CODE";
    public static final String EXTRA_CODE = "code";

    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent == null || !ACTION_COPY_CODE.equals(intent.getAction())) return;
        String code = intent.getStringExtra(EXTRA_CODE);
        if (code == null || !code.matches("[0-9]{6}")) return;
        ClipboardManager clipboard = (ClipboardManager) context.getSystemService(Context.CLIPBOARD_SERVICE);
        if (clipboard == null) return;
        clipboard.setPrimaryClip(ClipData.newPlainText("中国人寿验证码", code));
        Toast.makeText(context, "验证码已复制", Toast.LENGTH_SHORT).show();
    }
}
