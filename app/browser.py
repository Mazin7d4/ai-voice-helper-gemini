import time
from playwright.sync_api import sync_playwright

def open_browser(start_url: str):
    p = sync_playwright().start()
    browser = p.chromium.launch(headless=False, slow_mo=300)
    page = browser.new_page()
    page.goto(start_url, wait_until="domcontentloaded")
    return p, browser, page

def screenshot_png(page) -> bytes:
    page.wait_for_timeout(500)
    return page.screenshot(full_page=True)

def try_click_by_text(page, text: str) -> bool:
    if not text:
        return False

    locators = [
        page.get_by_role("link", name=text),
        page.get_by_role("button", name=text),
        page.get_by_text(text, exact=True),
        page.get_by_text(text),
    ]

    for loc in locators:
        try:
            if loc.first.is_visible(timeout=500):
                loc.first.click(timeout=1500)
                return True
        except Exception:
            pass
    return False

def try_type_near_text(page, target_text: str, to_type: str) -> bool:
    if not target_text or not to_type:
        return False
    try:
        # Try to find textbox by label
        tb = page.get_by_label(target_text)
        tb.fill(to_type, timeout=1500)
        return True
    except Exception:
        pass

    # fallback: click text then type
    if try_click_by_text(page, target_text):
        try:
            page.keyboard.type(to_type, delay=40)
            return True
        except Exception:
            return False

    return False

def apply_action(page, action: dict) -> bool:
    t = action.get("type")

    if t == "done":
        return True

    if t == "click":
        ok = try_click_by_text(page, action.get("target_text", ""))
        return ok

    if t == "type":
        ok = try_type_near_text(page, action.get("target_text", ""), action.get("text", ""))
        return ok

    if t == "scroll":
        scroll = action.get("scroll", {}) or {}
        direction = scroll.get("direction", "down")
        amount = int(scroll.get("amount", 1))
        delta = 700 * amount
        if direction == "up":
            delta = -delta
        page.mouse.wheel(0, delta)
        return True

    return False
