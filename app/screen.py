"""screen.py — Full-screen capture using mss (JPEG for speed)."""

import io
import ctypes
import time as _time
from PIL import Image

try:
    import mss
except ImportError:
    raise ImportError("pip install mss")


MAX_WIDTH = 1920
JPEG_QUALITY = 80  # good balance of quality vs speed

# ── Overlay hide/show for clean screenshots ─────────────────────────────────
_OVERLAY_TITLE = "AI Voice Helper"
_user32 = ctypes.windll.user32

# Win32 constants for layered windows
_GWL_EXSTYLE = -20
_WS_EX_LAYERED = 0x00080000
_LWA_ALPHA = 0x00000002


def _set_overlay_opacity(hwnd: int, alpha: int):
    """Set window opacity (0 = invisible, 255 = fully opaque). No minimize/restore."""
    # Ensure the window has the WS_EX_LAYERED style
    style = _user32.GetWindowLongW(hwnd, _GWL_EXSTYLE)
    if not (style & _WS_EX_LAYERED):
        _user32.SetWindowLongW(hwnd, _GWL_EXSTYLE, style | _WS_EX_LAYERED)
    _user32.SetLayeredWindowAttributes(hwnd, 0, alpha, _LWA_ALPHA)


def capture_screen(monitor_index: int = 0) -> tuple[bytes, tuple[int, int]]:
    """
    Capture the full screen as JPEG bytes.
    Makes the AI Voice Helper overlay fully transparent during capture
    so the vision model sees the actual desktop — no flicker.

    Returns:
        (jpeg_bytes, (width, height)) — the downscaled image and its dimensions.
    """
    # Make overlay invisible (alpha=0) — no minimize/restore, no flicker
    overlay_hwnd = _user32.FindWindowW(None, _OVERLAY_TITLE)
    if overlay_hwnd:
        _set_overlay_opacity(overlay_hwnd, 0)
        _time.sleep(0.02)  # one frame for compositor

    try:
        with mss.mss() as sct:
            monitors = sct.monitors
            if monitor_index >= len(monitors):
                monitor_index = 1
            monitor = monitors[monitor_index]
            raw = sct.grab(monitor)
            img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
    finally:
        # Always restore overlay opacity
        if overlay_hwnd:
            _set_overlay_opacity(overlay_hwnd, 255)

    orig_w, orig_h = img.size
    if orig_w > MAX_WIDTH:
        scale = MAX_WIDTH / orig_w
        new_h = int(orig_h * scale)
        img = img.resize((MAX_WIDTH, new_h), Image.Resampling.BILINEAR)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=JPEG_QUALITY)
    return buf.getvalue(), img.size


def get_screen_resolution() -> tuple[int, int]:
    """Return the primary monitor's native resolution."""
    with mss.mss() as sct:
        m = sct.monitors[1]  # primary
        return m["width"], m["height"]


def screenshot_to_native_coords(
    x: int, y: int,
    screenshot_size: tuple[int, int],
    native_size: tuple[int, int],
) -> tuple[int, int]:
    """
    Convert coordinates from the downscaled screenshot space
    back to native screen coordinates for pyautogui.
    """
    sx, sy = screenshot_size
    nx, ny = native_size
    scale_x = nx / sx
    scale_y = ny / sy
    return int(x * scale_x), int(y * scale_y)
