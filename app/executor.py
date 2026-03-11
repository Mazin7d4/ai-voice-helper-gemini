"""
executor.py — OS-level action execution via pyautogui.

Translates coordinate-based action JSON into real mouse/keyboard events.
Works with ANY application on Windows.
"""

import time
import subprocess
import ctypes
import ctypes.wintypes
import pyautogui
import pyperclip

# Safety: moving mouse to corner won't trigger pyautogui failsafe
# (we have our own safety layer in safety.py)
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1  # 100ms pause between pyautogui calls (was 50ms — too fast)

# ── Overlay z-order management ──────────────────────────────────────────────
_OVERLAY_TITLE = "AI Voice Helper"
_SWP_NOSIZE = 0x0001
_SWP_NOMOVE = 0x0002
_HWND_NOTOPMOST = -2
_HWND_TOPMOST = -1


def _lower_overlay():
    """Remove topmost from the overlay so launched apps can appear above it."""
    try:
        hwnd = ctypes.windll.user32.FindWindowW(None, _OVERLAY_TITLE)
        if hwnd:
            ctypes.windll.user32.SetWindowPos(
                hwnd, _HWND_NOTOPMOST, 0, 0, 0, 0, _SWP_NOMOVE | _SWP_NOSIZE
            )
    except Exception:
        pass


def _raise_overlay():
    """Restore topmost on the overlay."""
    try:
        hwnd = ctypes.windll.user32.FindWindowW(None, _OVERLAY_TITLE)
        if hwnd:
            ctypes.windll.user32.SetWindowPos(
                hwnd, _HWND_TOPMOST, 0, 0, 0, 0, _SWP_NOMOVE | _SWP_NOSIZE
            )
    except Exception:
        pass


def execute_action(
    action: dict,
    screenshot_size: tuple[int, int],
    native_size: tuple[int, int],
) -> tuple[bool, str]:
    """
    Execute a single action on the OS.

    Args:
        action: Action dict from vision.py (e.g., {"action": "click", "x": 100, "y": 200})
        screenshot_size: (w, h) of the downscaled screenshot that was sent to Gemini
        native_size: (w, h) of the actual screen resolution

    Returns:
        (success: bool, message: str)
    """
    act = action.get("action", "").lower()
    explanation = action.get("explanation", "")

    # Lower the overlay for all interactive actions so clicks/launches
    # hit the actual app, not the always-on-top overlay
    if act not in ("wait", "done"):
        _lower_overlay()

    try:
        if act == "open_app":
            app_name = action.get("app_name", "")
            if not app_name:
                return False, "No app_name specified"
            force_new = action.get("force_new", False)
            return _open_app(app_name, explanation, force_new=force_new)

        elif act == "click":
            x, y = _to_native(action, screenshot_size, native_size)
            button = action.get("button", "left")
            pyautogui.click(x, y, button=button)
            time.sleep(0.3)
            return True, f"Clicked at ({x}, {y}) — {explanation}"

        elif act == "double_click":
            x, y = _to_native(action, screenshot_size, native_size)
            pyautogui.doubleClick(x, y)
            time.sleep(0.3)
            return True, f"Double-clicked at ({x}, {y}) — {explanation}"

        elif act == "right_click":
            x, y = _to_native(action, screenshot_size, native_size)
            pyautogui.rightClick(x, y)
            time.sleep(0.3)
            return True, f"Right-clicked at ({x}, {y}) — {explanation}"

        elif act == "type":
            text = action.get("text", "")
            if not text:
                return False, "No text to type"
            # Use clipboard paste — far more reliable than keystroke-by-keystroke
            # especially for Windows Search, Run dialog, and other system UIs
            old_clipboard = ""
            try:
                old_clipboard = pyperclip.paste()
            except Exception:
                pass
            pyperclip.copy(text)
            time.sleep(0.05)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.2)
            # Restore old clipboard
            try:
                pyperclip.copy(old_clipboard)
            except Exception:
                pass
            return True, f"Typed: \"{text}\" — {explanation}"

        elif act == "hotkey":
            keys = action.get("keys", [])
            if not keys:
                return False, "No keys specified for hotkey"
            pyautogui.hotkey(*keys)
            return True, f"Pressed: {'+'.join(keys)} — {explanation}"

        elif act == "scroll":
            direction = action.get("direction", "down")
            amount = int(action.get("amount", 3))
            clicks = amount if direction == "down" else -amount
            pyautogui.scroll(-clicks)  # pyautogui: negative = scroll down
            return True, f"Scrolled {direction} {amount} — {explanation}"

        elif act == "wait":
            ms = int(action.get("ms", 1000))
            time.sleep(ms / 1000)
            return True, f"Waited {ms}ms — {explanation}"

        elif act == "done":
            summary = action.get("summary", "Goal completed")
            return True, f"Done: {summary}"

        else:
            return False, f"Unknown action type: {act}"

    except Exception as e:
        return False, f"Execution error: {e}"


def _to_native(
    action: dict,
    screenshot_size: tuple[int, int],
    native_size: tuple[int, int],
) -> tuple[int, int]:
    """Convert screenshot coordinates to native screen coordinates."""
    sx, sy = screenshot_size
    nx, ny = native_size
    x = int(action["x"] * (nx / sx))
    y = int(action["y"] * (ny / sy))
    # Clamp to screen bounds
    x = max(0, min(x, nx - 1))
    y = max(0, min(y, ny - 1))
    return x, y


# ── Common Windows apps → executable paths / start commands ──
_APP_ALIASES = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "paint": "mspaint.exe",
    "wordpad": "wordpad.exe",
    "cmd": "cmd.exe",
    "command prompt": "cmd.exe",
    "terminal": "wt.exe",
    "windows terminal": "wt.exe",
    "powershell": "powershell.exe",
    "file explorer": "explorer.exe",
    "explorer": "explorer.exe",
    "task manager": "taskmgr.exe",
    "settings": "ms-settings:",
    "control panel": "control.exe",
    "snipping tool": "snippingtool.exe",
    "chrome": "chrome",
    "google chrome": "chrome",
    "firefox": "firefox",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "excel": "excel",
    "microsoft excel": "excel",
    "word": "winword",
    "microsoft word": "winword",
    "powerpoint": "powerpnt",
    "outlook": "outlook",
    "teams": "msteams",
    "spotify": "spotify",
    "discord": "discord",
    "slack": "slack",
    "vscode": "code",
    "visual studio code": "code",
    "vs code": "code",
    "brave": "brave",
    "opera": "opera",
    "notepad++": "notepad++",
}


def _get_process_pids(exe_name: str) -> set[int]:
    """Get PIDs for a running process by executable name."""
    pids: set[int] = set()
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {exe_name}", "/NH", "/FO", "CSV"],
            capture_output=True, text=True, timeout=3,
            creationflags=0x08000000,  # CREATE_NO_WINDOW
        )
        for line in result.stdout.strip().splitlines():
            parts = line.replace('"', '').split(',')
            if len(parts) >= 2 and exe_name.lower() in parts[0].lower():
                try:
                    pids.add(int(parts[1].strip()))
                except ValueError:
                    pass
    except Exception:
        pass
    return pids


def _activate_window_by_pids(pids: set[int]) -> bool:
    """Find and bring to foreground a visible window belonging to one of the given PIDs."""
    if not pids:
        return False
    try:
        user32 = ctypes.windll.user32
        found = [0]  # store HWND as int

        @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        def _cb(hwnd, _lparam):  # type: ignore[no-untyped-def]
            if not user32.IsWindowVisible(hwnd):
                return True
            pid = ctypes.wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value in pids and user32.GetWindowTextLengthW(hwnd) > 0:
                found[0] = hwnd
                return False  # stop enumeration
            return True

        user32.EnumWindows(_cb, 0)

        if found[0]:
            # Alt-key trick: allows SetForegroundWindow from background process
            user32.keybd_event(0x12, 0, 0, 0)  # VK_MENU down
            user32.keybd_event(0x12, 0, 2, 0)  # VK_MENU up
            user32.ShowWindow(found[0], 9)  # SW_RESTORE
            user32.SetForegroundWindow(found[0])
            return True
    except Exception:
        pass
    return False


def _activate_window_by_title(title_substring: str) -> bool:
    """Find and activate a visible window whose title contains the given substring."""
    try:
        user32 = ctypes.windll.user32
        found = [0]

        @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        def _cb(hwnd, _lparam):
            if not user32.IsWindowVisible(hwnd):
                return True
            buf = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, buf, 256)
            title = buf.value
            if title_substring.lower() in title.lower() and len(title) > 0:
                # Skip the AI Voice Helper window
                if "AI Voice Helper" in title:
                    return True
                found[0] = hwnd
                return False
            return True

        user32.EnumWindows(_cb, 0)

        if found[0]:
            user32.keybd_event(0x12, 0, 0, 0)  # VK_MENU down
            user32.keybd_event(0x12, 0, 2, 0)  # VK_MENU up
            user32.ShowWindow(found[0], 9)  # SW_RESTORE
            user32.SetForegroundWindow(found[0])
            return True
    except Exception:
        pass
    return False


# Title substrings for finding app windows after launch
_APP_WINDOW_TITLES: dict[str, str] = {
    "msedge": "Edge",
    "chrome": "Chrome",
    "firefox": "Firefox",
    "brave": "Brave",
    "opera": "Opera",
    "notepad.exe": "Notepad",
    "calc.exe": "Calculator",
    "mspaint.exe": "Paint",
    "explorer.exe": "File Explorer",
    "code": "Visual Studio Code",
    "excel": "Excel",
    "winword": "Word",
    "powerpnt": "PowerPoint",
    "outlook": "Outlook",
    "spotify": "Spotify",
    "discord": "Discord",
    "slack": "Slack",
    "msteams": "Teams",
}


def _open_app(app_name: str, explanation: str, force_new: bool = False) -> tuple[bool, str]:
    """Open an application by name, or activate it if already running."""
    name_lower = app_name.lower().strip()

    # 1) Check our alias table first
    exe = _APP_ALIASES.get(name_lower)

    if exe:
        # Resolve the exe name to check in tasklist
        check_name = exe if exe.endswith(".exe") else exe + ".exe"

        # If already running and we don't need a new window, try to bring to foreground
        if not force_new:
            pids = _get_process_pids(check_name)
            if pids:
                _lower_overlay()  # let the app appear above the overlay
                activated = _activate_window_by_pids(pids)
                if activated:
                    time.sleep(0.5)
                    return True, f"{app_name} is already open — brought to foreground"
                # PIDs exist but no visible window — fall through to launch

        # Not running (or no visible window) — launch it
        try:
            _lower_overlay()  # let the new window appear above the overlay
            subprocess.Popen(
                exe,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            # Wait for the window to appear, then force-activate it
            title_hint = _APP_WINDOW_TITLES.get(exe, app_name)
            for _attempt in range(8):  # up to 4 seconds
                time.sleep(0.5)
                if _activate_window_by_title(title_hint):
                    return True, f"Opened {app_name} — {explanation}"
            # Window didn't appear but process launched
            return True, f"Launched {app_name} (window may take a moment)"
        except Exception:
            pass  # fall through to search

    # 2) Fallback: use Windows Search (Win+S → type name → Enter)
    try:
        _lower_overlay()  # let the search UI and app appear above the overlay
        pyautogui.hotkey("win", "s")
        time.sleep(0.8)  # wait for search to open

        # Type using clipboard paste (more reliable)
        pyperclip.copy(app_name)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(1.0)  # wait for search results

        pyautogui.press("enter")
        time.sleep(1.5)  # wait for app to launch

        return True, f"Opened {app_name} via search — {explanation}"
    except Exception as e:
        return False, f"Could not open {app_name}: {e}"
