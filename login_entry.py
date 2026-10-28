from __future__ import annotations

from playwright.sync_api import Error


# The lock-corner position is grounded in the user's current Edge screenshot:
# x ~= 88.5% and y ~= 20.5% of the webpage viewport (browser chrome excluded).
LOCK_X_RATIO = 0.885
LOCK_Y_RATIO = 0.205
EXPECTED_HOST = "elearningbluefe.e-chinalife.com"


def _password_fields(page) -> int:
    count = 0
    for frame in page.frames:
        try:
            count += frame.locator(
                'input[type="password"]:visible, '
                'input[autocomplete="current-password"]:visible, '
                'input[placeholder*="密码"]:visible, '
                'input[aria-label*="密码"]:visible'
            ).count()
        except Error:
            continue
    return count


def click_lock_corner_entry(page) -> tuple[bool, str]:
    """
    Switch the e-learning login card from QR mode to account/password mode.

    The site currently renders the two visible tab captions inconsistently
    through its frontend DOM, so captions are diagnostic only. The screenshot-
    calibrated folded-lock point is used on the verified site host, followed
    by a positive check that a password field appeared.
    """
    try:
        host = (page.url.split("/", 3)[2].split(":", 1)[0].lower()
                if "://" in page.url else "")
        if host != EXPECTED_HOST:
            return False, "当前网页不是已确认的国寿 e 学登录页面，已停止点击"

        if _password_fields(page) == 1:
            return True, "已检测到账号密码表单"

        # The lock control is at the top-right folded corner in the supplied
        # screenshot. Reset scroll so the viewport-relative point stays valid.
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(350)
        viewport = page.evaluate(
            "() => ({width: window.innerWidth, height: window.innerHeight})"
        )
        width = int(viewport.get("width") or 0)
        height = int(viewport.get("height") or 0)
        if width < 500 or height < 350:
            return False, f"网页可视区域异常（{width}×{height}），已停止点击"

        x = width * LOCK_X_RATIO
        y = height * LOCK_Y_RATIO

        hit = page.evaluate(
            """({x, y}) => {
                const el = document.elementFromPoint(x, y);
                if (!el) return null;
                const style = getComputedStyle(el);
                const r = el.getBoundingClientRect();
                return {
                    tag: el.tagName,
                    role: el.getAttribute('role') || '',
                    aria: el.getAttribute('aria-label') || '',
                    title: el.getAttribute('title') || '',
                    cursor: style.cursor,
                    x: Math.round(r.x),
                    y: Math.round(r.y),
                    width: Math.round(r.width),
                    height: Math.round(r.height)
                };
            }""",
            {"x": x, "y": y},
        )
        if not hit:
            return False, "锁头图标位置没有可点击元素，已停止操作"

        page.mouse.click(x, y)
        # The page's tab switch is client-rendered; wait for the password form.
        for _ in range(10):
            page.wait_for_timeout(250)
            if _password_fields(page) == 1:
                return True, "已自动点击右上角锁头并检测到账号密码表单"

        return False, (
            "已尝试点击截图对应的右上角锁头位置，但没有检测到密码输入框；"
            f"点击位置命中 {hit['tag']}，页面尺寸 {width}×{height}。"
            "为避免误填，已停止自动登录。"
        )
    except Error as exc:
        return False, f"锁头入口定位失败：{exc}"
