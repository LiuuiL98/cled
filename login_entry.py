from __future__ import annotations

from playwright.sync_api import Error


# Calibrated against the user's Edge screenshot. Coordinates are relative to
# the webpage viewport (not the outer Windows screenshot/browser chrome).
LOCK_X_RATIO = 0.885
LOCK_Y_RATIO = 0.260
LOCK_CANDIDATES = (
    (0.885, 0.260),  # center of the lock badge
    (0.875, 0.260),
    (0.895, 0.260),
    (0.885, 0.245),
    (0.885, 0.275),
    (0.895, 0.245),
    (0.895, 0.275),
)
EXPECTED_HOST = "elearningbluefe.e-chinalife.com"


def _password_fields(page) -> int:
    count = 0
    selectors = (
        'input[type="password"]:visible, '
        'input[autocomplete="current-password"]:visible, '
        'input[placeholder*="密码"]:visible, '
        'input[aria-label*="密码"]:visible'
    )
    for frame in page.frames:
        try:
            count += frame.locator(selectors).count()
        except Error:
            continue
    return count


def click_lock_corner_entry(page) -> tuple[bool, str]:
    """
    Automatically switch the verified e-learning login card from QR mode
    to account/password mode. No user click or per-run coordinate selection
    is required. A click only counts as successful after a password field
    is positively detected.
    """
    try:
        host = (
            page.url.split("/", 3)[2].split(":", 1)[0].lower()
            if "://" in page.url else ""
        )
        if host != EXPECTED_HOST:
            return False, "当前网页不是已确认的国寿 e 学登录页面，已停止点击"

        if _password_fields(page) == 1:
            return True, "已检测到账号密码表单"

        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(350)
        viewport = page.evaluate(
            "() => ({width: window.innerWidth, height: window.innerHeight})"
        )
        width = int(viewport.get("width") or 0)
        height = int(viewport.get("height") or 0)
        if width < 500 or height < 350:
            return False, f"网页可视区域异常（{width}×{height}），已停止点击"

        last_hit = None
        tried = []
        for x_ratio, y_ratio in LOCK_CANDIDATES:
            x = width * x_ratio
            y = height * y_ratio
            hit = page.evaluate(
                """({x, y}) => {
                    const el = document.elementFromPoint(x, y);
                    if (!el) return null;
                    const r = el.getBoundingClientRect();
                    const chain = [];
                    let node = el;
                    for (let i = 0; node && i < 4; i++, node = node.parentElement) {
                        const s = getComputedStyle(node);
                        chain.push({
                            tag: node.tagName,
                            role: node.getAttribute('role') || '',
                            aria: node.getAttribute('aria-label') || '',
                            title: node.getAttribute('title') || '',
                            cursor: s.cursor,
                            className: typeof node.className === 'string' ?
                                node.className.slice(0, 100) : '',
                            width: Math.round(node.getBoundingClientRect().width),
                            height: Math.round(node.getBoundingClientRect().height)
                        });
                    }
                    return {
                        tag: el.tagName,
                        cursor: getComputedStyle(el).cursor,
                        rect: {
                            x: Math.round(r.x), y: Math.round(r.y),
                            width: Math.round(r.width), height: Math.round(r.height)
                        },
                        chain
                    };
                }""",
                {"x": x, "y": y},
            )
            last_hit = hit
            tried.append(f"{x_ratio:.3f},{y_ratio:.3f}")
            if hit is None:
                continue

            page.mouse.click(x, y)
            # React/Vue may update the panel after the click event has bubbled.
            for _ in range(8):
                page.wait_for_timeout(200)
                if _password_fields(page) == 1:
                    return True, (
                        "已自动点击右上角锁头并检测到账号密码表单"
                        f"（网页坐标比例 {x_ratio:.3f},{y_ratio:.3f}）"
                    )

        hit_tag = last_hit.get("tag", "无") if last_hit else "无"
        hit_cursor = last_hit.get("cursor", "无") if last_hit else "无"
        return False, (
            "已自动尝试锁头图标中心及周边位置，但仍未检测到密码输入框；"
            f"最后命中元素={hit_tag}，cursor={hit_cursor}，"
            f"网页尺寸={width}×{height}，尝试点={';'.join(tried)}。"
            "为避免误填，已停止自动登录。"
        )
    except Error as exc:
        return False, f"锁头入口定位失败：{exc}"
