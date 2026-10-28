from __future__ import annotations

from playwright.sync_api import Error


def click_lock_corner_entry(page) -> tuple[bool, str]:
    """
    The supplied screenshot shows the password-mode control as a folded-corner
    lock icon at the upper-right of the white panel containing both login tabs.
    Locate that panel from its two tab labels, then click the same relative
    point. Refuse to guess if the panel cannot be identified.
    """
    try:
        point = page.evaluate("""() => {
            const findExact = (label) => [...document.querySelectorAll('body *')]
                .filter(el => el.children.length === 0 &&
                    (el.textContent || '').trim() === label);
            const a = findExact('易学堂登录');
            const b = findExact('云助理登录');
            if (a.length !== 1 || b.length !== 1) return null;

            let panel = a[0].parentElement;
            while (panel && !panel.contains(b[0])) panel = panel.parentElement;
            while (panel) {
                const r = panel.getBoundingClientRect();
                if (r.width >= 550 && r.height >= 300) {
                    const x = r.right - r.width * 0.07;
                    const y = r.top + r.height * 0.08;
                    const target = document.elementFromPoint(x, y);
                    if (!target || !panel.contains(target)) return null;
                    return {x, y, width: r.width, height: r.height};
                }
                panel = panel.parentElement;
            }
            return null;
        }""")
        if not point:
            return False, "无法唯一定位包含两个登录标签的登录面板"
        page.mouse.click(point["x"], point["y"])
        page.wait_for_timeout(700)
        return True, "已点击登录面板右上角锁头入口"
    except Error as exc:
        return False, f"锁头入口定位失败：{exc}"
