from __future__ import annotations

from playwright.sync_api import Error


# Ratios measured on the supplied native 1920x1080 screenshot:
# page viewport begins below the Edge toolbar/infobar; the lock badge center
# is approximately 88.2% from the left and 20.2% from the top.
#
# Playwright mouse coordinates and elementFromPoint both use CSS pixels.
# Windows 125% scaling is already represented by devicePixelRatio; do NOT
# multiply the CSS coordinates by DPR a second time.
LOCK_CENTER = (0.882, 0.202)
LOCK_OFFSETS = (
    (0.000, 0.000),
    (-0.004, 0.000), (0.004, 0.000),
    (0.000, -0.004), (0.000, 0.004),
    (-0.004, -0.004), (-0.004, 0.004),
    (0.004, -0.004), (0.004, 0.004),
    (-0.008, 0.000), (0.008, 0.000),
    (0.000, -0.008), (0.000, 0.008),
)
EXPECTED_HOST = "elearningbluefe.e-chinalife.com"


def _password_fields(page) -> int:
    selectors = (
        'input[type="password"]:visible, '
        'input[autocomplete="current-password"]:visible, '
        'input[placeholder*="密码"]:visible, '
        'input[aria-label*="密码"]:visible'
    )
    count = 0
    for frame in page.frames:
        try:
            count += frame.locator(selectors).count()
        except Error:
            continue
    return count


def click_lock_corner_entry(page) -> tuple[bool, str]:
    """
    Automatically open account/password login on the known e-learning page.
    No manual click or per-run calibration is required.
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

        page.bring_to_front()
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(300)

        metrics = page.evaluate(
            """() => {
                const vv = window.visualViewport;
                return {
                    width: vv ? vv.width : window.innerWidth,
                    height: vv ? vv.height : window.innerHeight,
                    offsetLeft: vv ? vv.offsetLeft : 0,
                    offsetTop: vv ? vv.offsetTop : 0,
                    innerWidth: window.innerWidth,
                    innerHeight: window.innerHeight,
                    dpr: window.devicePixelRatio || 1,
                    visualScale: vv ? vv.scale : 1,
                    screenWidth: window.screen.width,
                    screenHeight: window.screen.height
                };
            }"""
        )
        width = float(metrics.get("width") or 0)
        height = float(metrics.get("height") or 0)
        offset_left = float(metrics.get("offsetLeft") or 0)
        offset_top = float(metrics.get("offsetTop") or 0)
        if width < 500 or height < 350:
            return False, (
                f"网页可视区域异常（{width:.0f}×{height:.0f} CSS px），"
                "已停止点击"
            )

        last_hit = None
        last_ratio = LOCK_CENTER
        for dx, dy in LOCK_OFFSETS:
            x_ratio = LOCK_CENTER[0] + dx
            y_ratio = LOCK_CENTER[1] + dy
            x = offset_left + width * x_ratio
            y = offset_top + height * y_ratio

            hit = page.evaluate(
                """({x, y}) => {
                    const stack = document.elementsFromPoint(x, y).slice(0, 6);
                    const describe = (el) => {
                        const r = el.getBoundingClientRect();
                        const s = getComputedStyle(el);
                        return {
                            tag: el.tagName,
                            id: el.id || '',
                            className: typeof el.className === 'string' ?
                                el.className.slice(0, 100) : '',
                            role: el.getAttribute('role') || '',
                            aria: el.getAttribute('aria-label') || '',
                            title: el.getAttribute('title') || '',
                            cursor: s.cursor,
                            pointerEvents: s.pointerEvents,
                            rect: {
                                x: Math.round(r.x), y: Math.round(r.y),
                                width: Math.round(r.width), height: Math.round(r.height)
                            }
                        };
                    };
                    if (!stack.length) return null;
                    const chain = [];
                    for (let node = stack[0]; node && chain.length < 6;
                         node = node.parentElement) {
                        chain.push(describe(node));
                    }
                    return {
                        top: describe(stack[0]),
                        chain,
                        stack: stack.map(describe)
                    };
                }""",
                {"x": x, "y": y},
            )
            last_hit = hit
            last_ratio = (x_ratio, y_ratio)
            if hit is None:
                continue

            page.mouse.click(x, y)
            for _ in range(10):
                page.wait_for_timeout(180)
                count = _password_fields(page)
                if count == 1:
                    return True, (
                        "已自动点击右上角锁头并检测到账号密码表单"
                        f"（视口比例 {x_ratio:.3f},{y_ratio:.3f}）"
                    )
                if count > 1:
                    return False, (
                        f"点击后检测到 {count} 个密码输入框，为避免误填已停止"
                    )

        top = last_hit.get("top", {}) if last_hit else {}
        chain_text = " > ".join(
            f"{node.get('tag')}#{node.get('id')}."
            f"{node.get('className', '')[:38]}[cursor={node.get('cursor')}]"
            for node in (last_hit.get("chain", []) if last_hit else [])
        )
        return False, (
            "已按 1920×1080、Windows 125% 缩放截图自动尝试锁头及周边位置，"
            "但没有检测到密码输入框。"
            f"最后命中={top.get('tag', '无')}，cursor={top.get('cursor', '无')}，"
            f"元素链={chain_text or '无'}；"
            f"网页视口={width:.0f}×{height:.0f} CSS px，"
            f"DPR={metrics.get('dpr')}，"
            f"Edge screen={metrics.get('screenWidth')}×{metrics.get('screenHeight')}，"
            f"最后尝试比例={last_ratio[0]:.3f},{last_ratio[1]:.3f}。"
            "为避免误填，已停止自动登录。"
        )
    except Error as exc:
        return False, f"锁头入口定位失败：{exc}"
