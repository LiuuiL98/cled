package com.guoshou.clipboard;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class SmsTemplateParser {
    private static final Pattern TEMPLATE = Pattern.compile(
        "^【中国人寿】尊敬的用户，您的验证码：(\\d{6})，请于5分钟内输入，请勿将验证码泄露给他人，谢谢您的使用！$"
    );

    private SmsTemplateParser() { }

    public static String extractCode(String body) {
        if (body == null) return null;
        String normalized = body.replace("\r", "").replace("\n", "").trim();
        Matcher matcher = TEMPLATE.matcher(normalized);
        return matcher.matches() ? matcher.group(1) : null;
    }
}
