from __future__ import annotations

from playwright.sync_api import Error


EXPECTED_HOST = "elearningbluefe.e-chinalife.com"

# Position relative to the site's own content canvas, not the desktop or
# entire Edge viewport. The canvas is max-width/layout bounded in the provided
# screenshot, so this remains stable as the native Edge window changes size.
LOCK_X_IN_CANVAS = 0.938
LOCK_Y_IN_CANVAS = 0.200
OFFSETS = (
    (0.000, 0.000),
    (-0.003, 0.000), (0.003, 0.000),
    (0.000, -0.004), (0.000, 0.004),
    (-0.003, -0.004), (-0.003, 0.004),
    (0.003, -0.004), (0.003, 0.004),
    (-0.006, 0.000), (0.006, 0.000),
    (0.000, -0.008), (0.000, 0.008),
)


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
    """Automatically click the site's lock corner; no manual selection needed."""
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
        canvas = page.evaluate(
            """() => {
                const vw = window.innerWidth, vh = window.innerHeight;
                const all = [...document.querySelectorAll('body *')];
                const candidates = [];
                for (const el of all) {
                    const r = el.getBoundingClientRect();
                    if (r.width <= 0 || r.height <= 0) continue;
                    if (r.left < -2 || r.left > 20 || r.top < -2 || r.top > 15) continue;
                    const minWidth = Math.min(vw * 0.60, 900);
                    const minHeight = Math.min(vh * 0.55, 400);
                    if (r.width < minWidth || r.width > vw * 0.97 || r.height < minHeight) continue;
                    const s = getComputedStyle(el);
                    if (s.display === 'none' || s.visibility === 'hidden' || s.opacity === '0') continue;
                    candidates.push({
                        left:r.left, top:r.top, width:r.width, height:r.height,
                        area:r.width*r.height, tag:el.tagName, id:el.id || '',
                        className:typeof el.className === 'string' ? el.className.slice(0,120) : '',
                        background:s.backgroundColor, backgroundImage:s.backgroundImage !== 'none'
                    });
                }
                candidates.sort((a,b) => b.area-a.area);
                return {
                    viewport:{width:vw,height:vh,dpr:window.devicePixelRatio||1},
                    canvas:candidates[0] || null,
                    candidateCount:candidates.length,
                    topCandidates:candidates.slice(0,5)
                };
            }"""
        )
        if not canvas or not canvas.get("canvas"):
            viewport = canvas.get("viewport") if canvas else "未知"
            return False, f"无法识别国寿 e 学主内容画布，未执行猜测性点击。网页视口={viewport}"

        bounds = canvas["canvas"]
        vw = float(canvas["viewport"]["width"])
        vh = float(canvas["viewport"]["height"])
        # Use container geometry; browser viewport/desktop DPI scaling no longer
        # multiplies into the target point.
        base_x = bounds["left"] + bounds["width"] * LOCK_X_IN_CANVAS
        base_y = bounds["top"] + min(bounds["height"] * LOCK_Y_IN_CANVAS, 120)
        last_hit = None
        for dx_ratio, dy_ratio in OFFSETS:
            x = base_x + bounds["width"] * dx_ratio
            y = base_y + bounds["height"] * dy_ratio
            hit = page.evaluate(
                """({x,y}) => {
                    const stack=document.elementsFromPoint(x,y).slice(0,5);
                    const describe=el=>{
                        const r=el.getBoundingClientRect(),s=getComputedStyle(el);
                        return {tag:el.tagName,id:el.id||'',
                            className:typeof el.className==='string'?el.className.slice(0,100):'',
                            role:el.getAttribute('role')||'',aria:el.getAttribute('aria-label')||'',
                            title:el.getAttribute('title')||'',cursor:s.cursor,
                            rect:{x:Math.round(r.x),y:Math.round(r.y),width:Math.round(r.width),height:Math.round(r.height)}};
                    };
                    const chain=[];
                    for(let el=stack[0];el&&chain.length<5;el=el.parentElement) chain.push(describe(el));
                    return stack.length?{top:describe(stack[0]),chain,stack:stack.map(describe)}:null;
                }""",
                {"x":x,"y":y},
            )
            last_hit = hit
            if hit is None:
                continue
            page.mouse.click(x,y)
            for _ in range(10):
                page.wait_for_timeout(180)
                count = _password_fields(page)
                if count == 1:
                    return True, (
                        "已自动点击右上角锁头并检测到账号密码表单"
                        f"（主内容画布 {bounds['width']:.0f}×{bounds['height']:.0f} CSS px）"
                    )
                if count > 1:
                    return False, f"点击后检测到 {count} 个密码框，为避免误填已停止"

        top=last_hit.get("top",{}) if last_hit else {}
        chain_text=" > ".join(
            f"{n.get('tag')}#{n.get('id')}.{n.get('className','')[:35]}[cursor={n.get('cursor')}]"
            for n in (last_hit.get("chain",[]) if last_hit else [])
        )
        return False, (
            "已按网页主内容画布边界尝试锁头及周围位置，但未检测到密码输入框。"
            f"画布={bounds['width']:.0f}×{bounds['height']:.0f} CSS px，"
            f"网页视口={vw:.0f}×{vh:.0f} CSS px，DPR={canvas['viewport']['dpr']}；"
            f"最后命中={top.get('tag','无')}，cursor={top.get('cursor','无')}，"
            f"元素链={chain_text or '无'}。为避免误填，已停止自动登录。"
        )
    except Error as exc:
        return False, f"锁头入口定位失败：{exc}"
