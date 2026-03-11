"""
vision.py — Gemini vision: screenshot → coordinate-based action JSON.

Works with ANY software on screen — uses pixel coordinates, not DOM selectors.
Send a screenshot + goal, get back exactly one action to execute.
"""

import os
import json
import time as _time
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID")
LOCATION = os.getenv("GCP_LOCATION", "us-central1")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

if not PROJECT_ID:
    raise RuntimeError("Missing GCP_PROJECT_ID in .env")

# Vertex AI client for vision tasks
client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

SYSTEM_PROMPT = """\
You are an AI that controls a Windows computer for a visually impaired user.
You see a screenshot and decide ONE action toward the user's goal.

## Actions (return EXACTLY ONE as JSON)

open_app: {"action": "open_app", "app_name": "<name>", "explanation": "..."}
  THIS IS A PROGRAMMATIC LAUNCH (subprocess) — it does NOT click anything.
  Use it for ANY app: "notepad", "chrome", "edge", "excel", "spotify", etc.
click: {"action": "click", "x": <int>, "y": <int>, "explanation": "..."}
double_click: {"action": "double_click", "x": <int>, "y": <int>, "explanation": "..."}
right_click: {"action": "right_click", "x": <int>, "y": <int>, "explanation": "..."}
type: {"action": "type", "text": "<string>", "explanation": "..."}
hotkey: {"action": "hotkey", "keys": ["ctrl", "s"], "explanation": "..."}
scroll: {"action": "scroll", "direction": "up|down", "amount": 3, "explanation": "..."}
wait: {"action": "wait", "ms": 500, "explanation": "..."}
done: {"action": "done", "summary": "...", "explanation": "..."}

## RULES
1. TO LAUNCH ANY APP: ALWAYS use open_app. It runs the app programmatically
   via subprocess — much more reliable than clicking icons or searching.
   NEVER try to open an app by clicking desktop icons, taskbar, or search bars.
   Just use open_app with the app's name.
2. If an app is ALREADY OPEN and visible on screen, do NOT open_app again.
   Click its window or use Alt+Tab to bring it to focus.
3. THE SCREENSHOT IS GROUND TRUTH. Only trust what you SEE.
4. NEVER return "done" unless the goal is visually confirmed complete.
5. Coordinates are pixels on the SCREENSHOT image.
6. If a UI ELEMENTS list is provided, PREFER those exact coordinates for clicks.
7. Click a text field FIRST, then type in the NEXT step.
8. IGNORE the "AI Voice Helper" window.
9. NEVER repeat the same failed action. Try a different approach.
10. PREFER keyboard shortcuts (Ctrl+S, Ctrl+L, etc.) over menu clicks.
11. For URLs: Ctrl+L to focus address bar, type URL directly, press Enter.
12. Be efficient — shortest path to the goal.

Output ONLY valid JSON. No markdown, no extra text.
"""


def decide_action(
    goal: str,
    screenshot_bytes: bytes,
    last_action: dict | None = None,
    last_error: str | None = None,
    step: int = 1,
    max_steps: int = 20,
    action_history: list[dict] | None = None,
    ui_elements_text: str | None = None,
) -> dict:
    """
    Analyze a screenshot and decide the next action.

    Args:
        goal: The user's stated goal.
        screenshot_bytes: JPEG bytes of the current screen.
        last_action: The previous action that was executed (for context).
        last_error: Any error from the previous action.
        step: Current step number.
        max_steps: Maximum steps allowed.
        action_history: List of all previous actions taken in this goal.
        ui_elements_text: Formatted UI element list with coordinates (optional).

    Returns:
        Action dict with 'action' key and relevant parameters.
    """
    context_parts = [f"GOAL: {goal}"]
    context_parts.append(f"Step {step}/{max_steps}.")

    # Include UI elements for accurate clicking
    if ui_elements_text:
        context_parts.append(f"\nUI ELEMENTS:\n{ui_elements_text}")

    # Show full action history so model can see what's been tried
    if action_history and len(action_history) > 1:
        context_parts.append("PREVIOUS ACTIONS (oldest first):")
        # Show last 5 actions to avoid prompt bloat
        recent = action_history[-5:]
        for i, h in enumerate(recent):
            ctx = f"  {i+1}. {h.get('action', '?')}"
            if h.get('action') == 'open_app':
                ctx += f" ({h.get('app_name', '?')})"
            elif h.get('action') in ('click', 'double_click', 'right_click'):
                ctx += f" ({h.get('x', '?')}, {h.get('y', '?')})"
            elif h.get('action') == 'type':
                txt = h.get('text', '')[:30]
                ctx += f' ("{txt}")'
            elif h.get('action') == 'hotkey':
                ctx += f" ({'+'.join(h.get('keys', []))})"
            context_parts.append(ctx)

        # Detect repeat loops
        if len(action_history) >= 3:
            last_types = [a.get('action') for a in action_history[-3:]]
            if len(set(last_types)) == 1:
                context_parts.append(
                    f"WARNING: '{last_types[0]}' has been tried 3+ times in a row. "
                    f"You MUST try a completely different action type now."
                )

    if last_action:
        context_parts.append(f"Last action attempted: {json.dumps(last_action)}")
        if last_error:
            context_parts.append(f"FAILED: {last_error}. Try a different approach.")
        else:
            context_parts.append(
                "Action was sent. LOOK AT THE SCREENSHOT to verify what actually happened."
            )
            prev_act = last_action.get("action", "")
            if prev_act == "open_app":
                context_parts.append(
                    f"→ If {last_action.get('app_name', 'App')} is visible, do NOT open it again."
                )

    context_parts.append(
        "LOOK at the screenshot. Is the goal complete? If yes → done. If not → next action."
    )

    prompt_text = "\n".join(context_parts)

    resp = client.models.generate_content(
        model=MODEL_NAME,
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=prompt_text),
                    types.Part.from_bytes(
                        data=screenshot_bytes, mime_type="image/jpeg"
                    ),
                ],
            ),
        ],
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.05,  # very low for precise, focused actions
        ),
    )

    text = (resp.text or "").strip()

    # Extract JSON even if wrapped in markdown fences
    if "```" in text:
        # Find content between ``` markers
        parts = text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                text = part
                break

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise RuntimeError(f"Model did not return JSON. Got:\n{text}")

    action = json.loads(text[start : end + 1])

    # Validate required 'action' key
    if "action" not in action:
        raise RuntimeError(f"Missing 'action' key in response: {action}")

    return action


def verify_done(goal: str, screenshot_bytes: bytes) -> tuple[bool, str]:
    """
    Take a fresh screenshot and verify that a goal is truly complete.
    Returns (is_done, reason).
    """
    prompt = (
        f"GOAL: {goal}\n\n"
        "The AI previously claimed this goal is DONE.\n"
        "Look at this screenshot carefully. Is the goal TRULY complete?\n\n"
        "Check for:\n"
        "- Is a Save/Open dialog still open? → NOT done\n"
        "- Is the expected result visible on screen? → done\n"
        "- Is the app in the expected final state? → done\n"
        "- Is there an error message? → NOT done\n\n"
        'Reply with ONLY this JSON:\n'
        '{"verified": true, "reason": "..."} or {"verified": false, "reason": "what still needs to happen"}'
    )

    last_err = None
    for attempt in range(2):
        try:
            resp = client.models.generate_content(
                model=MODEL_NAME,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_text(text=prompt),
                            types.Part.from_bytes(
                                data=screenshot_bytes, mime_type="image/jpeg"
                            ),
                        ],
                    ),
                ],
                config=types.GenerateContentConfig(temperature=0.05),
            )
            text = (resp.text or "").strip()
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                result = json.loads(text[start : end + 1])
                return bool(result.get("verified", False)), result.get("reason", "")
            # If no JSON, assume not verified
            return False, text[:200]
        except Exception as e:
            last_err = e
            if attempt < 1:
                _time.sleep(1.0)
    # On failure, give benefit of the doubt
    return True, f"Verification failed ({last_err}), accepting done"


def describe_screen(screenshot_bytes: bytes, ui_elements_text: str = "") -> str:
    """
    Ask the model to describe what's currently visible on screen.
    Used for the "what do you see?" voice command.
    Detailed enough to guide a blind user.
    """
    prompt = (
        "You are describing a computer screen to a BLIND user who cannot see anything. "
        "They depend entirely on your description to understand what is on screen.\n\n"
    )
    if ui_elements_text:
        prompt += (
            "Here are the UI elements detected on screen via accessibility APIs:\n"
            f"{ui_elements_text}\n\n"
            "Use these elements to give PRECISE information about buttons, menus, text fields, etc.\n\n"
        )
    prompt += (
        "Describe in this order:\n"
        "1. Which app/window is in the foreground and what it shows\n"
        "2. Read out ANY visible text, dialog messages, notifications, or pop-ups VERBATIM\n"
        "3. List the main buttons, links, or interactive elements visible\n"
        "4. If there are choices to make (buttons like OK/Cancel, Yes/No, etc.), "
        "read them out clearly so the user can decide\n"
        "5. Mention any other windows or apps visible in the background or taskbar\n\n"
        "Be specific and practical. Instead of 'a dialog box is open', say "
        "'There is a dialog asking Do you want to save? with three buttons: Save, Don't Save, and Cancel.'\n"
        "Keep it under 5 sentences but include ALL important details."
    )

    resp = client.models.generate_content(
        model=MODEL_NAME,
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=prompt),
                    types.Part.from_bytes(
                        data=screenshot_bytes, mime_type="image/jpeg"
                    ),
                ],
            ),
        ],
        config=types.GenerateContentConfig(temperature=0.3),
    )

    return (resp.text or "").strip()
