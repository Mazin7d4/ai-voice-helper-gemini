"""
agent.py — Main orchestrator for the AI Voice Helper.

Architecture:
  - Main thread:  tkinter GUI event loop
  - Thread 1:     asyncio event loop for voice (Gemini Live API)
  - Thread 2:     vision/action loop (standard Gemini API + pyautogui)

Communication via thread-safe queues:
  - goal_queue:      voice/GUI → agent  (user's goal text)
  - narration_queue: agent → voice      (text for Gemini to speak)
  - status_queue:    agent → GUI        (status updates for display)
  - stop_event:      threading.Event    (stops the action loop)
"""

import os
import sys
import time
import queue
import asyncio
import threading
import numpy as np
import json
import re
import traceback
from dotenv import load_dotenv

load_dotenv()

import sounddevice as sd
from google import genai
from google.genai import types

from app.screen import capture_screen, get_screen_resolution, screenshot_to_native_coords
from app.vision import decide_action, describe_screen
from app.executor import execute_action, _APP_ALIASES
from app.safety import needs_confirmation
from app.ui_elements import get_ui_elements

# ── Config ──────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
LIVE_MODEL = os.getenv("LIVE_MODEL", "gemini-2.5-flash-native-audio-preview-12-2025")

INPUT_SAMPLE_RATE = 16000
OUTPUT_SAMPLE_RATE = 24000
CHANNELS = 1
INPUT_CHUNK = 1024
MAX_STEPS = 15
POST_ACTION_DELAY = 0.3  # seconds to wait after action before next screenshot

# ── Shared state ────────────────────────────────────────────────────────────
goal_queue = queue.Queue()          # text goals from voice/GUI
narration_queue = queue.Queue()     # text to speak via voice
status_queue = queue.Queue()        # (status_type, data) tuples for GUI

stop_event = threading.Event()      # stops the action loop
quit_event = threading.Event()      # full app shutdown
mic_muted = threading.Event()       # mic mute state (set = muted)
confirm_event = threading.Event()   # user said "confirm"
deny_event = threading.Event()      # user said "cancel"/ "no"

# Audio globals
audio_in_queue = queue.Queue()
audio_buffer = bytearray()
buffer_lock = threading.Lock()


def post_status(status_type: str, data: str = ""):
    """Post a status update to the GUI."""
    status_queue.put((status_type, data))


def _is_non_english(text: str) -> bool:
    """Return True if the text contains primarily non-Latin characters (Hindi, Arabic, etc.).
    Used to filter out wrongly transcribed speech."""
    if not text:
        return False
    # Count non-ASCII, non-punctuation characters
    non_latin = sum(1 for c in text if ord(c) > 0x024F and c not in ' \t\n')
    total = max(len(text.replace(' ', '')), 1)
    return (non_latin / total) > 0.3  # more than 30% non-Latin → probably wrong language


# ── Voice thread (async) ───────────────────────────────────────────────────

def voice_thread_entry():
    """Entry point for the voice thread — runs the asyncio event loop with auto-reconnect."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    retries = 0
    max_retries = 10
    while not quit_event.is_set() and retries < max_retries:
        try:
            loop.run_until_complete(voice_session())
            if quit_event.is_set():
                break
            # Session ended without quit — reconnect
            retries += 1
            delay = min(2 ** retries, 30)
            post_status("status", f"Voice disconnected — reconnecting in {delay}s...")
            time.sleep(delay)
        except Exception as e:
            retries += 1
            delay = min(2 ** retries, 30)
            post_status("error", f"Voice error: {e} — reconnecting in {delay}s...")
            time.sleep(delay)
    if retries >= max_retries and not quit_event.is_set():
        post_status("error", "Voice connection failed after multiple retries. Please restart.")
    loop.close()


async def voice_session():
    """Run the Gemini Live API voice session."""
    if not GEMINI_API_KEY:
        post_status("error", "Missing GEMINI_API_KEY")
        return

    client = genai.Client(api_key=GEMINI_API_KEY)

    # Define tools for the voice model to call
    execute_task_declaration = types.FunctionDeclaration(
        name="execute_task",
        description="Execute a computer task the user requested. Call this for ANY command like opening apps, navigating websites, typing, clicking, searching, etc. If user just says an app name like 'notepad' or 'chrome', treat it as opening that app.",
        parameters={
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "The task to execute, e.g. 'open notepad', 'go to google.com', 'close this window', 'search for weather'"
                }
            },
            "required": ["task"]
        }
    )

    describe_screen_declaration = types.FunctionDeclaration(
        name="describe_screen",
        description="Look at what's on the user's screen. Call this when the user asks what's on their screen, what they're looking at, what app is open, etc.",
        parameters={
            "type": "object",
            "properties": {},
        }
    )

    confirm_declaration = types.FunctionDeclaration(
        name="user_confirmed",
        description="The user confirmed/agreed (said yes, confirm, go ahead, sure, etc.)",
        parameters={
            "type": "object",
            "properties": {},
        }
    )

    deny_declaration = types.FunctionDeclaration(
        name="user_denied",
        description="The user denied/cancelled/stopped (said no, cancel, stop, nevermind, etc.). Do NOT call this for similar-sounding words like 'fast', 'last', 'past'.",
        parameters={
            "type": "object",
            "properties": {},
        }
    )

    config = types.LiveConnectConfig(
        response_modalities=[types.Modality.AUDIO],
        speech_config=types.SpeechConfig(
            language_code="en-US",
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Aoede")
            )
        ),
        system_instruction=types.Content(
            parts=[types.Part.from_text(
                text=(
                    "LANGUAGE: The user speaks ENGLISH. You MUST always listen, transcribe, "
                    "and respond in ENGLISH only. Even if the audio sounds like another language, "
                    "interpret it as English. NEVER transcribe in Hindi, Spanish, or any other language. "
                    "You are a friendly AI assistant helping a visually impaired person use their computer. "
                    "Talk to them like a helpful friend — warm, natural, casual. "
                    "NEVER use technical jargon, step numbers, or describe internal system actions. "
                    "THE USER IS BLIND. NEVER ask them to describe what they see, check the screen, "
                    "or look at anything. YOU are their eyes. If you need to know what's on screen, "
                    "call the describe_screen tool yourself — never ask the user to look. "
                    "\n\nCRITICAL: Use the execute_task tool for ANY computer command the user gives. "
                    "If user says just an app name like 'notepad' or 'chrome', call execute_task with 'open notepad' or 'open chrome'. "
                    "Use describe_screen when user asks what's on screen, OR when you need to check screen state yourself. "
                    "Use user_confirmed when user says yes/confirm. Use user_denied when user says stop/cancel. "
                    "\n"
                    "When a [System] message tells you what happened on screen, describe it naturally "
                    "as if YOU did it: 'I opened Chrome for you' not 'The system clicked the Chrome icon.' "
                    "When a [Screen description] message arrives, describe the screen conversationally. "
                    "CRITICAL RULE — NEVER say 'Done', 'Finished', 'All done', 'It's done', "
                    "'I've typed...', 'I've written...', or ANY task-completion language on your own. "
                    "You do NOT know if the task succeeded. ONLY echo completion AFTER a [System] message "
                    "explicitly says the task is complete. Until then, stay quiet or say 'Working on it'. "
                    "Keep ALL responses to 1 sentence. Be concise. Sound human."
                )
            )]
        ),
        tools=[types.Tool(function_declarations=[
            execute_task_declaration,
            describe_screen_declaration,
            confirm_declaration,
            deny_declaration,
        ])],
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
    )

    def mic_callback(indata, frames, time_info, status):
        if mic_muted.is_set():
            return
        pcm = (indata[:, 0] * 32767).astype(np.int16).tobytes()
        audio_in_queue.put(pcm)

    def speaker_callback(outdata, frames, time_info, status):
        bytes_needed = frames * 2
        with buffer_lock:
            if len(audio_buffer) >= bytes_needed:
                data = bytes(audio_buffer[:bytes_needed])
                del audio_buffer[:bytes_needed]
            else:
                available = bytes(audio_buffer)
                audio_buffer.clear()
                data = available + b"\x00" * (bytes_needed - len(available))
        outdata[:, 0] = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32767.0

    mic_stream = sd.InputStream(
        samplerate=INPUT_SAMPLE_RATE, channels=CHANNELS,
        dtype="float32", blocksize=INPUT_CHUNK, callback=mic_callback,
    )
    speaker_stream = sd.OutputStream(
        samplerate=OUTPUT_SAMPLE_RATE, channels=CHANNELS,
        dtype="float32", blocksize=512, callback=speaker_callback,
    )
    mic_stream.start()
    speaker_stream.start()

    post_status("voice_ready", "")

    # Send the greeting
    narration_queue.put(
        "[System] The user just connected. Greet them warmly. Say something like: "
        "Hi there! I'm your AI assistant, here to help you use this computer. "
        "Just tell me what you'd like to do and I'll take care of it."
    )

    try:
        async with client.aio.live.connect(model=LIVE_MODEL, config=config) as session:

            async def send_audio():
                while not quit_event.is_set():
                    try:
                        chunk = audio_in_queue.get(timeout=0.05)
                    except queue.Empty:
                        await asyncio.sleep(0.01)
                        continue
                    try:
                        await session.send_realtime_input(
                            audio=types.Blob(data=chunk, mime_type="audio/pcm;rate=16000")
                        )
                    except Exception:
                        break

            async def send_narrations():
                """Send narration text to the voice session for Gemini to speak."""
                while not quit_event.is_set():
                    try:
                        text = narration_queue.get(timeout=0.1)
                    except queue.Empty:
                        await asyncio.sleep(0.05)
                        continue
                    try:
                        await session.send_client_content(
                            turns=types.Content(
                                role="user",
                                parts=[types.Part.from_text(text=f"[System update] {text}")]
                            ),
                            turn_complete=True,
                        )
                    except Exception:
                        break

            async def receive_responses():
                user_text = ""
                gemini_text = ""
                while not quit_event.is_set():
                    try:
                        async for response in session.receive():
                            if quit_event.is_set():
                                break

                            # Handle tool calls (function calling)
                            if response.tool_call:
                                for fc in response.tool_call.function_calls:
                                    fn = fc.name
                                    args = fc.args or {}
                                    print(f"[FUNC-CALL] {fn}({args})")

                                    if fn == "execute_task":
                                        task_text = args.get("task", "")
                                        if task_text:
                                            print(f"[FUNC-CALL] Routing task: '{task_text}'")
                                            goal_queue.put(("goal", task_text))
                                        result = {"status": "ok", "message": f"Executing: {task_text}"}

                                    elif fn == "describe_screen":
                                        print(f"[FUNC-CALL] Routing describe")
                                        goal_queue.put(("describe", ""))
                                        result = {"status": "ok", "message": "Taking screenshot now"}

                                    elif fn == "user_confirmed":
                                        print(f"[FUNC-CALL] User confirmed")
                                        confirm_event.set()
                                        result = {"status": "ok"}

                                    elif fn == "user_denied":
                                        print(f"[FUNC-CALL] User denied/stopped")
                                        deny_event.set()
                                        stop_event.set()
                                        result = {"status": "ok"}

                                    else:
                                        result = {"error": f"Unknown function: {fn}"}

                                    # Send function response back
                                    try:
                                        await session.send_tool_response(
                                            function_responses=[types.FunctionResponse(
                                                name=fc.name,
                                                id=fc.id,
                                                response=result,
                                            )]
                                        )
                                    except Exception as e:
                                        print(f"[FUNC-CALL] Error sending response: {e}")
                                continue

                            server = response.server_content
                            if server:
                                if getattr(server, 'interrupted', False):
                                    with buffer_lock:
                                        audio_buffer.clear()

                                if server.model_turn and server.model_turn.parts:
                                    for part in server.model_turn.parts:
                                        if part.inline_data and part.inline_data.data:
                                            with buffer_lock:
                                                audio_buffer.extend(part.inline_data.data)

                                if server.input_transcription:
                                    txt = server.input_transcription.text
                                    if txt and txt.strip():
                                        cleaned = txt.strip()
                                        if _is_non_english(cleaned):
                                            continue
                                        if user_text and not user_text.endswith((' ', '\n')):
                                            user_text += " "
                                        user_text += cleaned

                                if server.output_transcription:
                                    txt = server.output_transcription.text
                                    if txt and txt.strip():
                                        if gemini_text and not gemini_text.endswith((' ', '\n')):
                                            gemini_text += " "
                                        gemini_text += txt.strip()

                                if server.turn_complete:
                                    if gemini_text.strip():
                                        post_status("gemini_speech", gemini_text.strip())
                                    if user_text.strip():
                                        post_status("user_speech", user_text.strip())
                                    user_text = ""
                                    gemini_text = ""

                    except Exception as e:
                        if not quit_event.is_set():
                            post_status("error", f"Voice recv: {e}")
                        break

            tasks = [
                asyncio.create_task(send_audio()),
                asyncio.create_task(send_narrations()),
                asyncio.create_task(receive_responses()),
            ]
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for t in pending:
                t.cancel()

    except Exception as e:
        post_status("error", f"Voice session: {e}")
    finally:
        mic_stream.stop()
        mic_stream.close()
        speaker_stream.stop()
        speaker_stream.close()


# ── Intent classification (regex-based — no hardcoded phrase lists) ──────

_ACTION_PATTERN = re.compile(
    r"\b("
    r"open|close|launch|start|run|go to|navigate|search for|search|find|type|write|"
    r"click|press|tap|scroll|download|upload|install|uninstall|delete|remove|copy|"
    r"paste|save|print|send|play|pause|skip|mute|unmute|"
    r"sign in|log in|sign out|log out|"
    r"create|edit|change|update|"
    r"turn on|turn off|minimize|maximize|"
    r"switch to|shut down|restart|refresh"
    r")",
    re.IGNORECASE,
)

_SCREEN_QUERY_PATTERN = re.compile(
    r"(?:"
    r"what do you see|what can you see|what's on (?:the |my )?screen|what is on (?:the |my )?screen|"
    r"what's happening|what is happening|read (?:the |my )?screen|describe (?:the |my )?screen|"
    r"what am i looking at|what's open|what is open|what's showing|what is showing|"
    r"what (?:website|app|page|window|tab|program|document|file|folder)|"
    r"can you see|what does it say|do you see|"
    r"read this|read that|tell me what(?:'s| is) (?:on|here|there|showing|visible)|"
    r"where am i|which (?:app|page|window|tab|site|document|file)|"
    r"look at (?:the |my )?screen|"
    r"what's this|what is this|what's that|what is that|describe what|"
    r"what.*(?:open|showing|running|visible).*(?:screen|computer|desktop)|"
    r"what.*(?:screen|computer|desktop).*(?:show|display|have)"
    r")",
    re.IGNORECASE,
)

_CONFIRM_PATTERN = re.compile(
    r"\b(yes|confirm|go ahead|do it|proceed|sure thing|approved|please do|"
    r"yep do it|yeah do it|yes do it|that's right|correct)\b",
    re.IGNORECASE,
)

_DENY_PATTERN = re.compile(
    r"\b(cancel|don't do|dont do|stop|nevermind|never mind|abort|"
    r"no don't|no dont|hold on|not yet|nope|no way|wait wait|stop stop)\b",
    re.IGNORECASE,
)


_QUESTION_PATTERN = re.compile(
    r"^\s*(?:what|which|where|who|how|is there|are there|do you|can you (?:see|tell|check|look|read))",
    re.IGNORECASE,
)

# Build a regex of known app names for fast detection
_APP_NAMES_SET = set(_APP_ALIASES.keys())
_APP_NAME_PATTERN = re.compile(
    r"^\s*(?:" + "|".join(re.escape(n) for n in sorted(_APP_NAMES_SET, key=len, reverse=True)) + r")\s*$",
    re.IGNORECASE,
)

# Pattern to extract app name from "open/launch/start/run <app>" commands
_OPEN_CMD_PATTERN = re.compile(
    r"^\s*(?:open|launch|start|run)\s+(.+?)\s*$",
    re.IGNORECASE,
)


def _is_computer_task(text: str) -> bool:
    """Return True if the text contains action verbs indicating a computer task."""
    # Questions about the screen state are NOT tasks
    if _QUESTION_PATTERN.search(text) and not re.search(
        r"\b(open|close|launch|start|run|create|delete|save|download|install|type|write|edit|send|play)\b",
        text, re.IGNORECASE
    ):
        return False
    # Bare app names like "notepad", "chrome", "spotify" → treat as "open <app>"
    if _APP_NAME_PATTERN.match(text):
        return True
    return bool(_ACTION_PATTERN.search(text))


def _is_screen_query(text: str) -> bool:
    """Return True if the user is asking about what's visible on screen."""
    return bool(_SCREEN_QUERY_PATTERN.search(text))


_TASK_TAG_PATTERN = re.compile(r"\[TASK:\s*(.+?)\]", re.IGNORECASE)
_DESCRIBE_TAG_PATTERN = re.compile(r"\[DESCRIBE\]", re.IGNORECASE)


def _parse_gemini_commands(gemini_output: str):
    """Parse Gemini's output for [TASK: ...] and [DESCRIBE] tags and route them."""
    # Check for [TASK: ...]
    task_match = _TASK_TAG_PATTERN.search(gemini_output)
    if task_match:
        task_text = task_match.group(1).strip()
        print(f"[ROUTE-TAG] Found [TASK: {task_text}] in Gemini output")
        goal_queue.put(("goal", task_text))
        return

    # Check for [DESCRIBE]
    if _DESCRIBE_TAG_PATTERN.search(gemini_output):
        print(f"[ROUTE-TAG] Found [DESCRIBE] in Gemini output")
        narration_queue.put(
            "[System] The user asked about the screen. Taking a screenshot now. "
            "Wait for the [Screen description] message before responding."
        )
        goal_queue.put(("describe", ""))
        return


def _process_user_speech(text: str):
    """Analyze user speech and route to the right handler."""
    lower = text.lower().strip()
    if not lower:
        return

    print(f"[ROUTE] text='{text}' is_task={_is_computer_task(lower)} fast_app={_extract_open_app(text)}")

    # 1) Confirmation (highest priority — time-sensitive when waiting)
    if _CONFIRM_PATTERN.search(lower):
        confirm_event.set()
        return

    # 2) Denial / stop
    if _DENY_PATTERN.search(lower):
        deny_event.set()
        stop_event.set()
        return

    # 3) Screen description request
    if _is_screen_query(lower):
        narration_queue.put(
            "[System] The user asked about the screen. Taking a screenshot now. "
            "Wait for the [Screen description] message before responding."
        )
        goal_queue.put(("describe", text))
        return

    # 4) Computer task — route to action loop
    if _is_computer_task(lower):
        goal_queue.put(("goal", text))
        return

    # 5) Everything else = conversation — voice model handles it naturally


# ── Action loop thread ──────────────────────────────────────────────────────

def action_thread_entry():
    """Entry point for the action/vision loop thread."""
    while not quit_event.is_set():
        try:
            cmd_type, cmd_text = goal_queue.get(timeout=0.3)
        except queue.Empty:
            continue

        if cmd_type == "describe":
            # Drain any additional queued describe requests (debounce)
            while True:
                try:
                    peek = goal_queue.get_nowait()
                    if peek[0] != "describe":
                        # Put non-describe back and break
                        goal_queue.put(peek)
                        break
                except queue.Empty:
                    break
            try:
                _handle_describe()
            except Exception as e:
                traceback.print_exc()
                post_status("error", f"Describe failed: {e}")
        elif cmd_type == "goal":
            try:
                _handle_goal(cmd_text)
            except Exception as e:
                traceback.print_exc()
                post_status("error", f"Goal failed: {e}")
                post_status("status", "Ready — Listening")
                post_status("goal", "")


def _handle_describe():
    """Take a screenshot and describe what's on screen."""
    post_status("status", "📸 Looking...")
    try:
        png_bytes, ss_size = capture_screen(monitor_index=1)
        post_status("status", "🔍 Analyzing screen...")
        description = describe_screen(png_bytes)
        narration_queue.put(f"[Screen description] {description}")
        post_status("action_log", f"Screen: {description}")
    except Exception as e:
        narration_queue.put(f"Sorry, I couldn't see the screen right now.")
        post_status("error", str(e))


def _extract_open_app(goal: str) -> str | None:
    """If the goal is clearly 'open <app>' or just an app name, return the app name.
    Returns None if it's not a simple app-open command."""
    text = goal.strip()
    # Case 1: bare app name like "notepad", "chrome"
    if _APP_NAME_PATTERN.match(text):
        return text.strip().lower()
    # Case 2: "open notepad", "launch chrome", "start excel"
    m = _OPEN_CMD_PATTERN.match(text)
    if m:
        app_name = m.group(1).strip().lower()
        # Verify it's a known app or a reasonable name (not a complex sentence)
        if app_name in _APP_NAMES_SET or len(app_name.split()) <= 3:
            return app_name
    return None


def _handle_goal(goal: str):
    """Run the screenshot → action → execute loop for a goal."""
    print(f"[ACTION] _handle_goal called with: '{goal}'")
    stop_event.clear()
    post_status("goal", goal)
    post_status("status", "Working...")
    narration_queue.put(f"On it.")

    native_size = get_screen_resolution()
    last_action = None
    last_error = None
    action_history: list[dict] = []  # full history for loop detection

    # ── Fast-path: if goal is clearly "open <app>", do it immediately ──
    fast_app = _extract_open_app(goal)
    print(f"[ACTION] fast_app = {fast_app!r}")
    if fast_app:
        fast_action = {"action": "open_app", "app_name": fast_app, "explanation": f"Open {fast_app}"}
        post_status("action_log", f"open_app: {fast_app} (fast-path)")
        try:
            ok, msg = execute_action(fast_action, screenshot_size=native_size, native_size=native_size)
            print(f"[ACTION] fast-path result: ok={ok}, msg={msg}")
        except Exception as e:
            print(f"[ACTION] fast-path EXCEPTION: {e}")
            traceback.print_exc()
            ok, msg = False, str(e)
        post_status("action_log", f"  {'✓' if ok else '✗'} {msg}")
        if ok:
            narration_queue.put(f"Opened {fast_app}.")
            post_status("status", "Done")
            post_status("goal", "")
            return
        else:
            # Fast-path failed — fall through to vision loop
            last_action = fast_action
            last_error = msg
            action_history.append(fast_action)

    step = 0
    while step < MAX_STEPS:
        step += 1
        if stop_event.is_set() or quit_event.is_set():
            narration_queue.put("[System] Stopped.")
            post_status("status", "Stopped")
            return

        # ── Check for new goal mid-task (real-time steering) ──
        try:
            new_cmd = goal_queue.get_nowait()
            if new_cmd[0] == "goal":
                new_goal = new_cmd[1]
                post_status("action_log", f"↪ Switching to: {new_goal}")
                narration_queue.put("[System] Got it, switching to the new request.")
                goal = new_goal
                post_status("goal", goal)
                last_action = None
                last_error = None
                action_history = []
                step = 0  # actually resets now (while loop)
                continue
            elif new_cmd[0] == "describe":
                _handle_describe()
                step -= 1  # don't count describe as a step
                continue
        except queue.Empty:
            pass

        # 1) Screenshot
        post_status("status", f"📸 Step {step}...")
        try:
            img_bytes, ss_size = capture_screen(monitor_index=1)
        except Exception as e:
            post_status("error", f"Screenshot failed: {e}")
            narration_queue.put("[System] I can't see the screen right now.")
            return

        # 2) Ask Gemini for next action
        post_status("status", f"🧠 Step {step}...")

        # Gather UI elements for clicking accuracy — skip step 1 (usually open_app)
        # and skip after non-interactive actions (open_app, hotkey, done, wait)
        ui_text = None
        last_act_type = (last_action or {}).get("action", "")
        if step > 1 and last_act_type not in ("open_app", "hotkey", "done", "wait", ""):
            try:
                _, ui_text = get_ui_elements(screen_size=ss_size)
            except Exception:
                pass  # non-critical — vision model works without it

        try:
            action = decide_action(
                goal=goal,
                screenshot_bytes=img_bytes,
                last_action=last_action,
                last_error=last_error,
                step=step,
                max_steps=MAX_STEPS,
                action_history=action_history,
                ui_elements_text=ui_text,
            )
        except Exception as e:
            # Don't give up — retry with a fresh screenshot next loop
            post_status("action_log", f"  Vision hiccup: {e}")
            last_error = f"Vision failed: {e}"
            time.sleep(0.3)
            continue

        explanation = action.get("explanation", "")
        act_type = action.get("action", "")
        post_status("action_log", f"{act_type}: {explanation}")

        # Hard loop breaker: if same action type repeated 4+ times, force error
        if len(action_history) >= 3:
            last_types = [a.get("action") for a in action_history[-3:]]
            if all(t == act_type for t in last_types):
                post_status("action_log", f"  Loop detected: {act_type} x4 — forcing change")
                last_action = action
                last_error = (
                    f"LOOP DETECTED: '{act_type}' has been attempted 4 times in a row and keeps failing. "
                    f"You MUST use a completely different approach. "
                    f"If the app is visible on screen, click its window to focus it instead of using open_app. "
                    f"If typing didn't work, try clicking the text field first."
                )
                action_history.append(action)
                time.sleep(POST_ACTION_DELAY)
                continue

        action_history.append(action)

        # 3) Check if done
        if act_type == "done":
            summary = action.get("summary", "All done.")
            narration_queue.put(f"[System] {summary}")
            post_status("status", "Done")
            return

        # 3b) Auto-done: if action is open_app and goal is just "open X",
        # mark done after executing to avoid re-opening in a loop
        is_simple_open = (
            act_type == "open_app"
            and _is_simple_open_goal(goal)
        )

        # 4) Safety check
        risky, reason = needs_confirmation(action)
        if risky:
            narration_queue.put(
                f"[System] Hold on — I want to {explanation}. Should I go ahead? Say confirm or cancel."
            )
            post_status("status", "Waiting for confirmation...")
            confirm_event.clear()
            deny_event.clear()

            confirmed = False
            for _ in range(600):  # 60 seconds — elderly users need more time
                if confirm_event.is_set():
                    confirmed = True
                    break
                if deny_event.is_set() or stop_event.is_set():
                    break
                time.sleep(0.1)

            if not confirmed:
                narration_queue.put("[System] Okay, I won't do that.")
                post_status("status", "Cancelled")
                return

            narration_queue.put("[System] Alright, doing it.")

        # 5) Execute the action
        post_status("status", f"⚡ Step {step}...")
        success, message = execute_action(action, ss_size, native_size)

        if success:
            last_action = action
            last_error = None

            # Narrate significant actions so the user knows progress
            narr = _short_narration(action)
            if narr:
                narration_queue.put(f"[System] {narr}")

            # Auto-done after simple open_app goal
            if is_simple_open:
                narration_queue.put(f"[System] {action.get('app_name', 'The app')} is open now.")
                post_status("status", "Done")
                return
        else:
            last_action = action
            last_error = message
            post_status("action_log", f"  ERROR: {message}")

        # 6) Wait for the UI to settle
        time.sleep(POST_ACTION_DELAY)

    narration_queue.put(f"[System] I've tried {MAX_STEPS} steps. Let me know if you need more help.")
    post_status("status", "Done")


def _is_simple_open_goal(goal: str) -> bool:
    """Check if goal is just 'open X' with no follow-up actions."""
    lower = goal.lower().strip()
    # Match: "open notepad", "launch chrome", "start excel", etc.
    # But NOT: "open notepad and type hello", "open chrome and go to google"
    if " and " in lower or " then " in lower:
        return False
    for prefix in ["open ", "launch ", "start ", "run "]:
        if lower.startswith(prefix):
            return True
    return False


def _short_narration(action: dict) -> str | None:
    """Generate a short, natural narration. Returns None to skip.
    Only narrate truly significant milestones, not every micro-step."""
    act = action.get("action", "")
    # Skip micro-steps entirely — reduces chatter, feels faster
    if act in ("scroll", "wait", "click", "hotkey"):
        return None
    if act == "open_app":
        return f"Opening {action.get('app_name', 'app')}"
    if act == "type":
        text = action.get('text', '')
        if len(text) > 50:
            return "Typing..."
        return f"Typed: {text[:40]}" if text else None
    if act == "double_click":
        return None
    return None


# ── Keyboard handling ───────────────────────────────────────────────────────
# Keyboard is now handled by tkinter key bindings in gui/overlay.py
# (msvcrt doesn't work when tkinter has focus)

def handle_key_space():
    """Toggle mic mute — called from GUI key binding."""
    if mic_muted.is_set():
        mic_muted.clear()
        post_status("mic", "unmuted")
    else:
        mic_muted.set()
        post_status("mic", "muted")


def handle_key_enter():
    """Interrupt: clear audio + stop action loop."""
    with buffer_lock:
        audio_buffer.clear()
    stop_event.set()
    post_status("status", "Interrupted")


def handle_key_escape():
    """Full quit."""
    quit_event.set()
    stop_event.set()
    post_status("quit", "")


# ── Start everything ────────────────────────────────────────────────────────

def start_agent():
    """
    Start all background threads. Call this from GUI or standalone.
    Returns the thread objects so the caller can join them.
    """
    threads = []

    t_voice = threading.Thread(target=voice_thread_entry, daemon=True, name="voice")
    t_voice.start()
    threads.append(t_voice)

    t_action = threading.Thread(target=action_thread_entry, daemon=True, name="action")
    t_action.start()
    threads.append(t_action)

    return threads


def submit_goal(text: str):
    """Submit a goal programmatically (from GUI text input)."""
    goal_queue.put(("goal", text))


def submit_describe():
    """Request a screen description programmatically."""
    goal_queue.put(("describe", ""))


def stop_agent():
    """Stop the current action loop."""
    stop_event.set()


def quit_app():
    """Full shutdown."""
    quit_event.set()
    stop_event.set()
