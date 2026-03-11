"""
browser.py — Playwright-based browser controller.

Used for ALL web browsing tasks. More reliable than screenshot+click
because it uses DOM selectors, not pixel coordinates.

Hybrid architecture:
  - Browser tasks → Playwright (this module)
  - OS tasks     → pyautogui  (executor.py)
"""

import re
import time
from playwright.sync_api import sync_playwright, Page


# ── Known websites for direct URL mapping ───────────────────────────────────

_KNOWN_SITES: dict[str, str] = {
    "chatgpt": "https://chatgpt.com",
    "chat gpt": "https://chatgpt.com",
    "google": "https://www.google.com",
    "youtube": "https://www.youtube.com",
    "gmail": "https://mail.google.com",
    "google maps": "https://maps.google.com",
    "google drive": "https://drive.google.com",
    "google docs": "https://docs.google.com",
    "facebook": "https://www.facebook.com",
    "twitter": "https://x.com",
    "reddit": "https://www.reddit.com",
    "github": "https://github.com",
    "amazon": "https://www.amazon.com",
    "netflix": "https://www.netflix.com",
    "spotify": "https://open.spotify.com",
    "linkedin": "https://www.linkedin.com",
    "wikipedia": "https://www.wikipedia.org",
    "stackoverflow": "https://stackoverflow.com",
    "stack overflow": "https://stackoverflow.com",
    "instagram": "https://www.instagram.com",
    "whatsapp": "https://web.whatsapp.com",
    "outlook": "https://outlook.live.com",
    "discord": "https://discord.com/app",
    "twitch": "https://www.twitch.tv",
    "pinterest": "https://www.pinterest.com",
    "bing": "https://www.bing.com",
    "yahoo": "https://www.yahoo.com",
}

_URL_PATTERN = re.compile(
    r"(?:https?://)?[\w.-]+\.(?:com|org|net|io|dev|edu|gov|co|me|app|ai|tv)\b",
    re.IGNORECASE,
)

_BROWSER_NAMES = {
    "chrome", "firefox", "edge", "browser", "chromium",
    "opera", "brave", "safari", "web browser",
}

_BROWSER_KEYWORDS = re.compile(
    r"\b(?:website|web ?site|web ?page|url|browse|surf|internet|online|"
    r"in (?:the )?(?:chrome|firefox|edge|browser)|"
    r"open (?:the )?(?:website|web ?page|site|link))\b",
    re.IGNORECASE,
)

_SEARCH_PATTERN = re.compile(
    r"(?:search (?:for|about)|look up|find (?:info|information) (?:on|about)|google)\s+(.+)",
    re.IGNORECASE,
)


# ── BrowserController ──────────────────────────────────────────────────────

class BrowserController:
    """Controls a Chromium browser via Playwright for reliable web automation."""

    def __init__(self):
        self._pw = None
        self._browser = None
        self._context = None
        self._page: Page | None = None

    @property
    def is_active(self) -> bool:
        try:
            return self._page is not None and not self._page.is_closed()
        except Exception:
            return False

    @property
    def page(self) -> Page | None:
        return self._page if self.is_active else None

    def launch(self, url: str | None = None) -> str:
        """Launch the browser. Returns status message."""
        if self.is_active:
            if url:
                return self.navigate(url)
            return "Browser is already open"

        try:
            if self._pw is None:
                self._pw = sync_playwright().start()

            self._browser = self._pw.chromium.launch(
                headless=False,
                args=["--start-maximized"],
            )
            self._context = self._browser.new_context(
                viewport=None,
                no_viewport=True,
            )
            self._page = self._context.new_page()

            if url:
                self._page.goto(url, wait_until="domcontentloaded", timeout=15000)
                title = self._page.title()
                return f"Opened browser — {title}"
            else:
                self._page.goto("about:blank")
                return "Browser opened"

        except Exception as e:
            self._page = None
            return f"Failed to launch browser: {e}"

    def navigate(self, url: str) -> str:
        """Navigate to a URL."""
        if not self.is_active:
            return self.launch(url)

        if not url.startswith("http"):
            url = "https://" + url
        try:
            self._page.goto(url, wait_until="domcontentloaded", timeout=15000)
            return f"Navigated to {self._page.title()}"
        except Exception as e:
            return f"Navigation failed: {e}"

    def click_element(self, target_text: str) -> str:
        """Click an element by its visible text, label, or placeholder."""
        if not self.is_active:
            return "Browser is not open"

        page = self._page
        strategies = [
            ("link",        lambda: page.get_by_role("link", name=target_text)),
            ("button",      lambda: page.get_by_role("button", name=target_text)),
            ("placeholder", lambda: page.get_by_placeholder(target_text)),
            ("label",       lambda: page.get_by_label(target_text)),
            ("textbox",     lambda: page.get_by_role("textbox", name=target_text)),
            ("tab",         lambda: page.get_by_role("tab", name=target_text)),
            ("menuitem",    lambda: page.get_by_role("menuitem", name=target_text)),
            ("heading",     lambda: page.get_by_role("heading", name=target_text)),
            ("text",        lambda: page.get_by_text(target_text, exact=False)),
        ]

        for name, get_locator in strategies:
            try:
                loc = get_locator()
                if loc.count() > 0 and loc.first.is_visible(timeout=600):
                    loc.first.click(timeout=2000)
                    return f"Clicked [{name}] \"{target_text}\""
            except Exception:
                continue

        return f"Could not find element: \"{target_text}\""

    def type_text(self, text: str, field_hint: str | None = None) -> str:
        """Type text. If field_hint given, find and focus that field first."""
        if not self.is_active:
            return "Browser is not open"

        page = self._page

        if field_hint:
            field_strategies = [
                lambda: page.get_by_placeholder(field_hint),
                lambda: page.get_by_label(field_hint),
                lambda: page.get_by_role("textbox", name=field_hint),
                lambda: page.get_by_role("searchbox", name=field_hint),
                lambda: page.get_by_role("combobox", name=field_hint),
            ]
            for get_loc in field_strategies:
                try:
                    loc = get_loc()
                    if loc.count() > 0 and loc.first.is_visible(timeout=500):
                        loc.first.fill(text, timeout=2000)
                        return f"Typed \"{text}\" in \"{field_hint}\""
                except Exception:
                    continue

        # Fallback: type into whatever is focused
        try:
            page.keyboard.type(text, delay=30)
            return f"Typed: \"{text}\""
        except Exception as e:
            return f"Could not type: {e}"

    def press_key(self, key: str) -> str:
        """Press a keyboard key (Enter, Tab, Escape, etc.)."""
        if not self.is_active:
            return "Browser is not open"
        try:
            self._page.keyboard.press(key)
            return f"Pressed {key}"
        except Exception as e:
            return f"Key press failed: {e}"

    def scroll_page(self, direction: str = "down", amount: int = 3) -> str:
        """Scroll the page up or down."""
        if not self.is_active:
            return "Browser is not open"
        try:
            delta = 300 * amount * (1 if direction == "down" else -1)
            self._page.mouse.wheel(0, delta)
            return f"Scrolled {direction}"
        except Exception as e:
            return f"Scroll failed: {e}"

    def go_back(self) -> str:
        """Navigate back in browser history."""
        if not self.is_active:
            return "Browser is not open"
        try:
            self._page.go_back(timeout=5000)
            return f"Went back to {self._page.title()}"
        except Exception as e:
            return f"Go back failed: {e}"

    def search_google(self, query: str) -> str:
        """Navigate to Google search results."""
        url = f"https://www.google.com/search?q={query}"
        if not self.is_active:
            return self.launch(url)
        try:
            self._page.goto(url, wait_until="domcontentloaded", timeout=15000)
            return f"Searched for: {query}"
        except Exception as e:
            return f"Search failed: {e}"

    def screenshot(self) -> bytes:
        """Take a JPEG screenshot of the current browser page."""
        if not self.is_active:
            return b""
        try:
            return self._page.screenshot(type="jpeg", quality=80)
        except Exception:
            return b""

    def get_page_info(self) -> dict:
        """Get current page title and URL."""
        if not self.is_active:
            return {"title": "", "url": ""}
        try:
            return {"title": self._page.title(), "url": self._page.url}
        except Exception:
            return {"title": "", "url": ""}

    def get_interactive_elements(self, max_elements: int = 35) -> str:
        """
        Get a formatted list of interactive elements visible on the page.
        Sent to the vision model so it can reference elements by text.
        """
        if not self.is_active:
            return ""
        try:
            elements = self._page.evaluate("""
                (maxElements) => {
                    const results = [];
                    const seen = new Set();

                    const selectors = [
                        'a[href]', 'button', 'input', 'textarea', 'select',
                        '[role="button"]', '[role="link"]', '[role="tab"]',
                        '[role="menuitem"]', '[role="option"]', '[role="searchbox"]',
                        '[role="combobox"]', '[contenteditable="true"]'
                    ].join(', ');
                    const els = document.querySelectorAll(selectors);

                    for (const el of els) {
                        if (results.length >= maxElements) break;

                        const rect = el.getBoundingClientRect();
                        if (rect.width === 0 || rect.height === 0) continue;
                        if (rect.top > window.innerHeight || rect.bottom < 0) continue;
                        if (window.getComputedStyle(el).display === 'none') continue;

                        let text = (
                            el.innerText?.trim() ||
                            el.value ||
                            el.placeholder ||
                            el.getAttribute('aria-label') ||
                            el.getAttribute('title') ||
                            el.getAttribute('alt') ||
                            ''
                        ).substring(0, 80).replace(/\\n/g, ' ').trim();

                        if (!text || text.length < 1 || seen.has(text)) continue;
                        seen.add(text);

                        const tag = el.tagName.toLowerCase();
                        let role = el.getAttribute('role') || '';
                        if (!role) {
                            if (tag === 'a') role = 'link';
                            else if (tag === 'button') role = 'button';
                            else if (tag === 'input') role = el.type || 'input';
                            else if (tag === 'textarea') role = 'textbox';
                            else if (tag === 'select') role = 'select';
                            else role = tag;
                        }

                        results.push({
                            text,
                            role,
                            href: (el.href && el.href.startsWith('http'))
                                  ? el.href.substring(0, 120) : '',
                        });
                    }
                    return results;
                }
            """, max_elements)

            lines = []
            for el in elements:
                role = el.get("role", "element")
                text = el.get("text", "")
                href = el.get("href", "")
                extra = f" → {href}" if href else ""
                lines.append(f"  [{role}] \"{text}\"{extra}")
            return "\n".join(lines)

        except Exception:
            return ""

    def close(self):
        """Close the browser and clean up resources."""
        try:
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
            if self._pw:
                self._pw.stop()
        except Exception:
            pass
        finally:
            self._page = None
            self._context = None
            self._browser = None
            self._pw = None


# ── Singleton ───────────────────────────────────────────────────────────────

_controller: BrowserController | None = None


def get_browser() -> BrowserController:
    """Get the singleton BrowserController instance."""
    global _controller
    if _controller is None:
        _controller = BrowserController()
    return _controller


# ── URL / goal helpers ──────────────────────────────────────────────────────

def resolve_url(goal: str) -> str | None:
    """Try to extract or resolve a URL from the goal text."""
    lower = goal.lower().strip()

    # Check known sites (longest match first to avoid partial matches)
    for name in sorted(_KNOWN_SITES, key=len, reverse=True):
        if name in lower:
            return _KNOWN_SITES[name]

    # Check for explicit URL pattern
    m = _URL_PATTERN.search(goal)
    if m:
        url = m.group()
        if not url.startswith("http"):
            url = "https://" + url
        return url

    return None


def extract_search_query(goal: str) -> str | None:
    """Extract a search query from 'search for X' style goals."""
    m = _SEARCH_PATTERN.search(goal)
    if m:
        query = m.group(1).strip().rstrip(".")
        # Don't return if it's about an OS action
        if re.search(r"\b(open|launch|click|press|type|save|close)\b", query, re.IGNORECASE):
            return None
        return query
    return None


def is_browser_goal(goal: str, app_name_extractor=None) -> bool:
    """
    Check if this goal should be handled by the Playwright browser.

    Args:
        goal: The user's goal text.
        app_name_extractor: Optional callable(goal) → str|None.
                            Returns an app name if the goal is 'open <app>'.
                            Prevents routing OS apps to the browser.
    """
    lower = goal.lower().strip()

    # Opening a known browser → yes, use Playwright
    for name in _BROWSER_NAMES:
        if re.match(rf"^(?:open|launch|start)\s+{re.escape(name)}$", lower):
            return True
        if lower == name:
            return True

    # Known website name → yes
    for site_name in _KNOWN_SITES:
        if site_name in lower:
            return True

    # Explicit URL → yes
    if _URL_PATTERN.search(lower):
        return True

    # Browser-related keywords → yes
    if _BROWSER_KEYWORDS.search(lower):
        return True

    # "search for X" (web search) → yes, unless about local files/apps
    if extract_search_query(goal) is not None:
        if not re.search(r"\b(notepad|excel|word|explorer|file|folder|settings)\b", lower):
            return True

    # If Playwright browser is already active, interactive goals go to it
    browser = get_browser()
    if browser.is_active:
        # But not if it's about opening an OS-level app
        if app_name_extractor and app_name_extractor(goal):
            return False
        # Interactive verbs → browser
        if re.search(
            r"\b(click|type|scroll|go to|navigate|enter|submit|fill|select|choose|ask)\b",
            lower,
        ):
            return True

    return False
