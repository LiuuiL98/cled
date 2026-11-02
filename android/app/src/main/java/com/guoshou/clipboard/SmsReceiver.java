package com.guoshou.clipboard;

import android.Manifest;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.drawable.Icon;
import android.os.Build;
import android.provider.Telephony;
import android.telephony.SmsMessage;

public final class SmsReceiver extends BroadcastReceiver {
    private static final String CHANNEL_ID = "china_life_codes";

    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent == null || !Telephony.Sms.Intents.SMS_RECEIVED_ACTION.equals(intent.getAction())) return;
        if (context.checkSelfPermission(Manifest.permission.RECEIVE_SMS) != PackageManager.PERMISSION_GRANTED) return;

        SmsMessage[] messages = Telephony.Sms.Intents.getMessagesFromIntent(intent);
        if (messages == null || messages.length == 0) return;
        StringBuilder body = new StringBuilder();
        for (SmsMessage message : messages) {
            if (message != null && message.getMessageBody() != null) body.append(message.getMessageBody());
        }

        String code = SmsTemplateParser.extractCode(body.toString());
        if (code == null) return;
        if (Build.VERSION.SDK_INT >= 33
                && context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) return;
        showCodeNotification(context, code);
    }

    private void showCodeNotification(Context context, String code) {
        NotificationManager manager = context.getSystemService(NotificationManager.class);
        if (manager == null) return;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID, "中国人寿验证码", NotificationManager.IMPORTANCE_HIGH);
            channel.setDescription("仅在本机显示匹配到的验证码，不上传或保存短信正文");
            manager.createNotificationChannel(channel);
        }

        Intent copyIntent = new Intent(context, CopyCodeReceiver.class);
        copyIntent.setAction(CopyCodeReceiver.ACTION_COPY_CODE);
        copyIntent.putExtra(CopyCodeReceiver.EXTRA_CODE, code);
        int id = (int) (System.currentTimeMillis() & 0x7fffffff);
        PendingIntent pending = PendingIntent.getBroadcast(context, id, copyIntent,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);

        Notification.Builder builder = Build.VERSION.SDK_INT >= 26
            ? new Notification.Builder(context, CHANNEL_ID) : new Notification.Builder(context);
        Notification notification = builder
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle("收到中国人寿验证码")
            .setContentText("验证码：" + code)
            .setStyle(new Notification.BigTextStyle().bigText("验证码：" + code))
            .setCategory(Notification.CATEGORY_MESSAGE)
            .setVisibility(Notification.VISIBILITY_PRIVATE)
            .setPriority(Notification.PRIORITY_HIGH)
            .setAutoCancel(true)
            .addAction(new Notification.Action.Builder(
                Icon.createWithResource(context, android.R.drawable.ic_menu_save),
                "复制验证码", pending).build())
            .build();
        manager.notify(id, notification);
    }
}
