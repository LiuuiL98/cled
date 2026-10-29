from __future__ import annotations

from playwright.sync_api import Error


EXPECTED_HOST = "elearningbluefe.e-chinalife.com"


def password_field_count(page) -> int:
    """Count visible password fields across the page and its child frames."""
    selector = (
        'input[type="password"]:visible, '
        'input[autocomplete="current-password"]:visible, '
        'input[placeholder*="密码"]:visible, '
        'input[aria-label*="密码"]:visible'
    )
    count = 0
    for frame in page.frames:
        try:
            count += frame.locator(selector).count()
        except Error:
            continue
    return count


def begin_lock_position_learning(page) -> None:
    """
    Capture the next real user click inside the web page. The click is not
    intercepted, so clicking the lock continues to switch the site's login
    panel normally. Coordinates are reported in CSS viewport pixels.
    """
    host = (
        page.url.split("/", 3)[2].split(":", 1)[0].lower()
        if "://" in page.url else ""
    )
    if host != EXPECTED_HOST:
        raise RuntimeError("当前网页不是已确认的国寿 e 学登录页面。")

    page.evaluate(
        """() => {
            window.__cledLockClick = null;
            if (window.__cledLockClickHandler) {
                document.removeEventListener('click', window.__cledLockClickHandler, true);
            }
            window.__cledLockClickHandler = (event) => {
                if (!event.isTrusted) return;
                window.__cledLockClick = {
                    x: event.clientX,
                    y: event.clientY,
                    width: window.innerWidth,
                    height: window.innerHeight,
                    href: location.href,
                    at: Date.now()
                };
            };
            document.addEventListener('click', window.__cledLockClickHandler, true);
        }"""
    )


def read_manual_lock_click(page) -> dict | None:
    if not page or page.is_closed():
        return None
    try:
        return page.evaluate("() => window.__cledLockClick || null")
    except Error:
        return None


def clear_manual_lock_click(page) -> None:
    if not page or page.is_closed():
        return
    try:
        page.evaluate(
            """() => {
                if (window.__cledLockClickHandler) {
                    document.removeEventListener('click', window.__cledLockClickHandler, true);
                }
                window.__cledLockClick = null;
                window.__cledLockClickHandler = null;
            }"""
        )
    except Error:
        pass


def click_saved_lock_position(
    page, x_ratio: float, y_ratio: float
) -> tuple[bool, str]:
    """Click the one-time calibrated viewport position and verify the form."""
    try:
        host = (
            page.url.split("/", 3)[2].split(":", 1)[0].lower()
            if "://" in page.url else ""
        )
        if host != EXPECTED_HOST:
            return False, "当前网页不是已确认的国寿 e 学登录页面，已停止点击"

        if password_field_count(page) == 1:
            return True, "已检测到账号密码表单，无需再次点击"

        if not (0 <= x_ratio <= 1 and 0 <= y_ratio <= 1):
            return False, "已保存的锁头位置无效，请重新校准"

        page.bring_to_front()
        page.evaluate("window.scrollTo(0, 0)")
        metrics = page.evaluate(
            "() => ({width: window.innerWidth, height: window.innerHeight})"
        )
        width = float(metrics.get("width") or 0)
        height = float(metrics.get("height") or 0)
        if width < 500 or height < 350:
            return False, f"网页可视区域异常（{width:.0f}×{height:.0f}），已停止点击"

        x = width * x_ratio
        y = height * y_ratio
        page.mouse.click(x, y)
        for _ in range(20):
            page.wait_for_timeout(150)
            count = password_field_count(page)
            if count == 1:
                return True, "已自动点击已保存的锁头位置并检测到账号密码表单"
            if count > 1:
                return False, f"点击后出现 {count} 个密码框，为避免误填已停止"
        return False, (
            f"已点击保存的位置（视口比例 {x_ratio:.4f}, {y_ratio:.4f}），"
            "但没有检测到密码输入框。请使用“重新校准锁头位置”。"
        )
    except Error as exc:
        return False, f"使用已保存锁头位置失败：{exc}"
