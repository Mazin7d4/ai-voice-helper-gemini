"""
safety.py — Safety gate for risky actions.

Checks if an action involves destructive/financial/irreversible operations
and requires explicit user confirmation before executing.
"""

# Keywords in action explanation or target that flag an action as risky
# Only truly dangerous/irreversible actions — not generic UI interactions
RISKY_KEYWORDS = [
    "buy", "purchase", "place order", "checkout", "pay",
    "complete purchase", "confirm purchase",
    "send email", "send message",
    "delete", "remove permanently", "uninstall", "format disk",
    "sign out", "log out",
    "authorize", "grant permission",
    "transfer money", "wire transfer",
]

# Actions that model can explicitly flag
CONFIRM_FLAG = "requires_confirm"


def needs_confirmation(action: dict) -> tuple[bool, str]:
    """
    Check if an action needs user confirmation before execution.

    Returns:
        (needs_confirm: bool, reason: str)
    """
    # 1) Model explicitly flagged it
    if action.get(CONFIRM_FLAG, False):
        reason = action.get("explanation", "Model flagged this as risky")
        return True, reason

    # 2) Keyword scan on explanation
    explanation = action.get("explanation", "").lower()
    text = action.get("text", "").lower()
    summary = action.get("summary", "").lower()

    combined = f"{explanation} {text} {summary}"

    for keyword in RISKY_KEYWORDS:
        if keyword in combined:
            return True, f"Action involves '{keyword}' — confirmation needed"

    # 3) Type-based heuristics
    act = action.get("action", "")
    if act == "hotkey":
        keys = [k.lower() for k in action.get("keys", [])]
        # Flag dangerous hotkeys
        if "delete" in keys:
            return True, "Delete key pressed"
        if set(keys) == {"alt", "f4"}:
            return True, "Closing application (Alt+F4)"

    return False, ""
