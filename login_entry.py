from __future__ import annotations

from playwright.sync_api import Error


# Ratios are measured against the webpage viewport, excluding Edge chrome.
# In the user's full-window screenshot, the folded lock badge center is
# approximately x=88.5%, y=20.5% of this viewport.
LOCK_CANDIDATES = (
    (0.885, 0.205),
    (0.875, 0.205),
    (0.895, 0.205),
    (0.885, 0.195),
    (0.885, 0.215),
    (0.875, 0.215),
    (0.895, 0.215),
    (0.875, 0.195),
    (0.895, 0.195),
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
    to account/password mode. No per-run manual click is required.
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
            """() => ({
                width: window.innerWidth,
                height: window.innerHeight,
                dpr: window.devicePixelRatio || 1,
                visualScale: window.visualViewport ? window.visualViewport.scale : 1,
                visualOffsetTop: window.visualViewport ? window.visualViewport.offsetTop : 0
            })"""
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
                    const stack = document.elementsFromPoint(x, y).slice(0, 5);
                    const describe = (el) => {
                        const r = el.getBoundingClientRect();
                        const s = getComputedStyle(el);
                        return {
                            tag: el.tagName,
                            id: el.id || '',
                            className: typeof el.className === 'string' ?
                                el.className.slice(0, 120) : '',
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
                    const top = stack[0];
                    if (!top) return null;
                    const chain = [];
                    for (let node = top; node && chain.length < 6; node = node.parentElement) {
                        chain.push(describe(node));
                    }
                    return {top: describe(top), chain, stack: stack.map(describe)};
                }""",
                {"x": x, "y": y},
            )
            last_hit = hit
            tried.append({
                "ratio": (x_ratio, y_ratio),
                "hit": hit,
            })
            if hit is None:
                continue

            # Use a real mouse click so the site's normal pointer/click handlers run.
            page.mouse.click(x, y)
            for _ in range(8):
                page.wait_for_timeout(200)
                if _password_fields(page) == 1:
                    return True, (
                        "已自动点击右上角锁头并检测到账号密码表单"
                        f"（网页坐标比例 {x_ratio:.3f},{y_ratio:.3f}）"
                    )

        top = last_hit.get("top", {}) if last_hit else {}
        chain_text = " > ".join(
            f"{node.get('tag')}#{node.get('id')}."
            f"{node.get('className','')[:45]}[cursor={node.get('cursor')}]"
            for node in (last_hit.get("chain", []) if last_hit else [])
        )
        return False, (
            "已按全屏截图校准锁头位置并尝试周边点位，但仍未检测到密码输入框。"
            f"最后命中={top.get('tag','无')}，cursor={top.get('cursor','无')}，"
            f"元素链={chain_text or '无'}；网页视口={width}×{height}，"
            f"DPR={viewport.get('dpr')}，visualScale={viewport.get('visualScale')}。"
            "为避免误填，已停止自动登录。"
        )
    except Error as exc:
        return False, f"锁头入口定位失败：{exc}"
