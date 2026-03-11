"""
ui_elements.py — Windows UI Automation element extraction.

Supplements the vision model with exact element names, types, and coordinates.
Uses the same Windows Accessibility API that screen readers like JAWS use.
"""

import time
import ctypes
import ctypes.wintypes

try:
    import uiautomation as auto
except ImportError:
    raise ImportError("pip install uiautomation")


# Element types we care about for interaction
_INTERACTIVE_TYPES = {
    "ButtonControl", "HyperlinkControl", "EditControl",
    "ComboBoxControl", "CheckBoxControl", "RadioButtonControl",
    "MenuItemControl", "TabItemControl", "ListItemControl",
    "TreeItemControl", "DocumentControl", "SplitButtonControl",
}

# Skip elements with these names (noise)
_SKIP_NAMES = {"", "System", "Minimize", "Maximize", "Restore", "Close",
               "Search tabs", "Side Panel Resize Handle (draggable)"}

# Max depth to walk the UI tree (deeper = more elements but slower)
_MAX_DEPTH = 10
_MAX_ELEMENTS = 25
_MAX_WALK = 400  # safety: stop walking after this many nodes
_TIMEOUT_MS = 400  # hard timeout for UI tree walk


def get_ui_elements(
    screen_size: tuple[int, int] | None = None,
) -> tuple[list[dict], str]:
    """
    Extract interactive UI elements from the foreground window.

    Args:
        screen_size: (w, h) of the screenshot. If provided, coordinates are
                     scaled to match the screenshot coordinate space.

    Returns:
        (elements: list of dicts, elements_text: formatted string for the vision prompt)

    Each element dict has:
        index, type, name, center_x, center_y, rect (left, top, right, bottom)
    """
    try:
        fg = auto.GetForegroundControl()
    except Exception:
        return [], ""

    window_name = fg.Name or "Unknown"
    window_type = fg.ControlTypeName or ""

    # Get native screen size for coordinate mapping
    user32 = ctypes.windll.user32
    native_w = user32.GetSystemMetrics(0)
    native_h = user32.GetSystemMetrics(1)

    elements = []
    walked = 0
    seen_names = set()  # deduplicate by name+type
    t_start = time.perf_counter()

    try:
        for ctrl, depth in auto.WalkControl(fg, maxDepth=_MAX_DEPTH):
            walked += 1
            if walked > _MAX_WALK:
                break
            # Hard timeout
            if (time.perf_counter() - t_start) * 1000 > _TIMEOUT_MS:
                break

            ctype = ctrl.ControlTypeName
            if ctype not in _INTERACTIVE_TYPES:
                continue

            name = (ctrl.Name or "").strip()
            if name in _SKIP_NAMES and ctype not in ("EditControl", "DocumentControl"):
                continue

            try:
                rect = ctrl.BoundingRectangle
                w = rect.width()
                h = rect.height()
            except Exception:
                continue

            if w <= 2 or h <= 2:
                continue  # not visible

            # Deduplicate: skip if same name+type already seen
            dedup_key = (ctype, name)
            if dedup_key in seen_names:
                continue
            seen_names.add(dedup_key)

            # Native coordinates (center of element)
            cx_native = int(rect.left + w / 2)
            cy_native = int(rect.top + h / 2)

            # Clamp to screen
            cx_native = max(0, min(cx_native, native_w - 1))
            cy_native = max(0, min(cy_native, native_h - 1))

            # Scale to screenshot coordinates if needed
            if screen_size:
                ss_w, ss_h = screen_size
                cx = int(cx_native * ss_w / native_w)
                cy = int(cy_native * ss_h / native_h)
            else:
                cx, cy = cx_native, cy_native

            # Friendly type name
            type_name = ctype.replace("Control", "").lower()

            # Clean up name — include keyboard shortcuts if present
            display_name = name[:80] if name else f"[unnamed {type_name}]"

            elements.append({
                "index": len(elements),
                "type": type_name,
                "name": display_name,
                "center_x": cx,
                "center_y": cy,
                "native_x": cx_native,
                "native_y": cy_native,
                "rect": (int(rect.left), int(rect.top), int(rect.right), int(rect.bottom)),
            })

            if len(elements) >= _MAX_ELEMENTS:
                break
    except Exception:
        pass  # UI tree walk can fail if window closes mid-scan

    # Build text representation for the vision prompt
    if not elements:
        elements_text = f"Window: {window_name}\nNo interactive elements detected."
    else:
        lines = [f"Window: {window_name}", "Interactive elements (click by coordinates):"]
        for e in elements:
            lines.append(
                f"  [{e['index']:2d}] {e['type']:12s} \"{e['name']}\" "
                f"at ({e['center_x']}, {e['center_y']})"
            )
        elements_text = "\n".join(lines)

    return elements, elements_text


def get_element_text(max_chars: int = 500) -> str:
    """
    Get the text content of the focused/foreground window.
    Useful for knowing what text is currently displayed (e.g., in Notepad).
    """
    try:
        fg = auto.GetForegroundControl()
        # Try to find a Document or Edit control
        for ctrl, depth in auto.WalkControl(fg, maxDepth=6):
            if ctrl.ControlTypeName in ("DocumentControl", "EditControl"):
                try:
                    val = ctrl.GetValuePattern()
                    if val:
                        text = val.Value or ""
                        if text:
                            return text[:max_chars]
                except Exception:
                    pass
                try:
                    text_pat = ctrl.GetTextPattern()
                    if text_pat:
                        text = text_pat.DocumentRange.GetText(max_chars)
                        if text:
                            return text[:max_chars]
                except Exception:
                    pass
        return ""
    except Exception:
        return ""
