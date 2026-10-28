from __future__ import annotations

from playwright.sync_api import Error


_LOCATE_PANEL_JS = r"""
() => {
    const normalize = (value) => (value || '').replace(/[\\s\\u200b\\ufeff]+/g, '');
    const isVisible = (el) => {
        if (!el || !el.getClientRects().length) return false;
        const style = getComputedStyle(el);
        return style.display !== 'none' &&
            style.visibility !== 'hidden' &&
            style.opacity !== '0';
    };
    const labels = ['易学堂登录', '云助理登录'];
    const all = [...document.querySelectorAll('body *')];
    const candidates = labels.map((label) => {
        return all.map((el) => {
            const ownText = normalize(el.innerText || el.textContent);
            const aria = normalize(el.getAttribute('aria-label'));
            const matched = ownText.includes(label) || aria.includes(label);
            if (!matched || !isVisible(el)) return null;
            const rect = el.getBoundingClientRect();
            if (rect.width <= 0 || rect.height <= 0) return null;
            return {el, rect, textLength: Math.min(ownText.length || 9999, aria.length || 9999)};
        }).filter(Boolean).sort((a, b) => {
            // Prefer the smallest visible text node, rather than requiring a leaf node.
            return a.textLength - b.textLength ||
                (a.rect.width * a.rect.height) - (b.rect.width * b.rect.height);
        });
    });

    if (!candidates[0].length || !candidates[1].length) {
        return {
            ok: false,
            reason: 'labels_missing',
            firstLabelCount: candidates[0].length,
            secondLabelCount: candidates[1].length
        };
    }

    const vw = document.documentElement.clientWidth || window.innerWidth;
    const vh = document.documentElement.clientHeight || window.innerHeight;
    const minWidth = Math.max(280, vw * 0.25);
    const minHeight = Math.max(130, vh * 0.16);
    const panels = new Map();

    // Search every pair and choose the smallest visible common ancestor that
    // plausibly represents the login card. This works with nested spans/divs.
    for (const a of candidates[0].slice(0, 20)) {
        for (const b of candidates[1].slice(0, 20)) {
            if (a.el === b.el) continue;
            for (let panel = a.el.parentElement; panel; panel = panel.parentElement) {
                if (!panel.contains(b.el)) continue;
                const rect = panel.getBoundingClientRect();
                if (!isVisible(panel) ||
                    rect.width < minWidth || rect.height < minHeight ||
                    rect.width > vw * 0.99 || rect.height > vh * 0.99) {
                    continue;
                }
                const area = rect.width * rect.height;
                const previous = panels.get(panel);
                if (!previous || area < previous.area) {
                    panels.set(panel, {panel, rect, area});
                }
                break;
            }
        }
    }

    if (!panels.size) {
        return {
            ok: false,
            reason: 'common_panel_missing',
            firstLabelCount: candidates[0].length,
            secondLabelCount: candidates[1].length,
            viewport: {width: vw, height: vh}
        };
    }

    const ranked = [...panels.values()].sort((a, b) => a.area - b.area);
    const best = ranked[0];
    const r = best.rect;

    // The site presents the password-mode switch as a folded lock corner
    // near the upper-right of the card. Keep the hit point inside the card.
    const x = r.right - r.width * 0.07;
    const y = r.top + r.height * 0.08;
    const target = document.elementFromPoint(x, y);
    if (!target || !best.panel.contains(target)) {
        return {
            ok: false,
            reason: 'lock_corner_not_hit_testable',
            panel: {width: r.width, height: r.height},
            point: {x, y}
        };
    }

    return {
        ok: true,
        x, y,
        panel: {width: r.width, height: r.height},
        frameUrl: location.href,
        target: {
            tag: target.tagName,
            role: target.getAttribute('role') || '',
            aria: target.getAttribute('aria-label') || '',
            title: target.getAttribute('title') || '',
            className: typeof target.className === 'string' ? target.className : ''
        }
    };
}
"""


def click_lock_corner_entry(page) -> tuple[bool, str]:
    """
    Find the login card containing both login tabs in the main document or
    an iframe, then click the folded lock corner at the card's upper-right.
    Never click when the two labels/card cannot be identified safely.
    """
    try:
        frames = page.frames
        diagnostics = []
        matches = []

        for frame in frames:
            try:
                result = frame.evaluate(_LOCATE_PANEL_JS)
                if result and result.get("ok"):
                    matches.append((frame, result))
                elif result:
                    diagnostics.append(
                        f"{result.get('reason')} "
                        f"(易学堂登录={result.get('firstLabelCount', 0)}, "
                        f"云助理登录={result.get('secondLabelCount', 0)})"
                    )
            except Error:
                continue

        if not matches:
            detail = diagnostics[0] if diagnostics else "页面及内嵌页面均未找到两个登录标签"
            return False, f"未能定位账号密码入口：{detail}"

        if len(matches) != 1:
            return False, f"检测到 {len(matches)} 个可能的登录面板，为避免误点已停止"

        frame, point = matches[0]
        if frame == page.main_frame:
            page.mouse.click(point["x"], point["y"])
        else:
            # Coordinates returned by frame.evaluate are relative to that
            # frame's viewport; click the hit-tested element inside the frame.
            clicked = frame.evaluate(
                """({x, y}) => {
                    const target = document.elementFromPoint(x, y);
                    if (!target) return false;
                    const actionable = target.closest(
                        'button,a,[role="button"],[tabindex],input'
                    ) || target;
                    actionable.click();
                    return true;
                }""",
                {"x": point["x"], "y": point["y"]},
            )
            if not clicked:
                return False, "已定位登录面板，但无法触发折角锁头入口"

        page.wait_for_timeout(700)
        return True, "已点击登录面板右上角锁头入口"
    except Error as exc:
        return False, f"锁头入口定位失败：{exc}"
