package com.guoshou.clipboard;

import org.junit.Test;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;

public class SmsTemplateParserTest {
    @Test public void extractsExactTemplate() {
        assertEquals("693754", SmsTemplateParser.extractCode(
            "【中国人寿】尊敬的用户，您的验证码：693754，请于5分钟内输入，请勿将验证码泄露给他人，谢谢您的使用！"));
    }
    @Test public void rejectsDifferentBrand() {
        assertNull(SmsTemplateParser.extractCode(
            "【其他】尊敬的用户，您的验证码：693754，请于5分钟内输入，请勿将验证码泄露给他人，谢谢您的使用！"));
    }
    @Test public void rejectsWrongLengthAndChangedExpiry() {
        assertNull(SmsTemplateParser.extractCode(
            "【中国人寿】尊敬的用户，您的验证码：12345，请于5分钟内输入，请勿将验证码泄露给他人，谢谢您的使用！"));
        assertNull(SmsTemplateParser.extractCode(
            "【中国人寿】尊敬的用户，您的验证码：123456，请于10分钟内输入，请勿将验证码泄露给他人，谢谢您的使用！"));
    }
}
