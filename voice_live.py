"""
voice_live.py — Standalone Gemini Live API voice session.

Streams microphone audio to Gemini, plays back model audio responses,
and prints transcripts. Uses Vertex AI with Application Default Credentials.

Requirements:
    pip install google-genai sounddevice
"""

import asyncio
import os
import sys
import signal
import threading
import queue
import numpy as np
import msvcrt
from dotenv import load_dotenv

load_dotenv()

import sounddevice as sd
from google import genai
from google.genai import types

# ── Config ──────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
LIVE_MODEL = os.getenv("LIVE_MODEL", "gemini-2.5-flash-native-audio-preview-12-2025")

if not GEMINI_API_KEY:
    raise RuntimeError("Missing GEMINI_API_KEY in .env")

# Audio format constants (match Gemini Live API spec)
INPUT_SAMPLE_RATE = 16000   # 16 kHz mono PCM for input
OUTPUT_SAMPLE_RATE = 24000  # 24 kHz mono PCM for output
CHANNELS = 1
INPUT_CHUNK = 1024          # samples per chunk (~64ms at 16kHz)

# ── Globals ─────────────────────────────────────────────────────────────────
running = True
audio_in_queue = queue.Queue()
mic_muted = False  # spacebar toggles mute
audio_buffer = bytearray()  # continuous output buffer
buffer_lock = threading.Lock()


def signal_handler(sig, frame):
    global running
    print("\n[CTRL+C] Shutting down...")
    running = False


signal.signal(signal.SIGINT, signal_handler)


def mic_callback(indata, frames, time_info, status):
    """Called by sounddevice when mic data is available."""
    if status:
        pass  # ignore overflow warnings
    if mic_muted:
        return  # spacebar muted
    # indata is float32 [-1,1], convert to int16 PCM bytes
    pcm = (indata[:, 0] * 32767).astype(np.int16).tobytes()
    audio_in_queue.put(pcm)


async def main():
    global running

    print(f"[INIT] Connecting to Gemini Live API...")
    print(f"  Model   : {LIVE_MODEL}")

    # Create client with API key (Live API needs AI Developer API, not Vertex)
    client = genai.Client(api_key=GEMINI_API_KEY)

    # Live session config
    config = types.LiveConnectConfig(
        response_modalities=[types.Modality.AUDIO],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Aoede")
            )
        ),
        system_instruction=types.Content(
            parts=[types.Part.from_text(
                text="You are a helpful voice assistant. Keep responses short and conversational. "
                     "If the user says 'stop' or 'goodbye', say goodbye briefly."
            )]
        ),
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
    )

    # Speaker callback reads from the module-level audio_buffer
    def speaker_callback(outdata, frames, time_info, status):
        """Called by sounddevice when speaker needs data — reads from continuous buffer."""
        bytes_needed = frames * 2  # int16 = 2 bytes per sample
        with buffer_lock:
            if len(audio_buffer) >= bytes_needed:
                data = bytes(audio_buffer[:bytes_needed])
                del audio_buffer[:bytes_needed]
            else:
                # Drain whatever we have, pad the rest with silence
                available = bytes(audio_buffer)
                audio_buffer.clear()
                data = available + b"\x00" * (bytes_needed - len(available))
        outdata[:, 0] = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32767.0

    # Start audio streams
    mic_stream = sd.InputStream(
        samplerate=INPUT_SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        blocksize=INPUT_CHUNK,
        callback=mic_callback,
    )

    speaker_stream = sd.OutputStream(
        samplerate=OUTPUT_SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        blocksize=512,  # smaller blocks = smoother playback
        callback=speaker_callback,
    )

    mic_stream.start()
    speaker_stream.start()

    print("[READY] Microphone active. Speak now!")
    print("  SPACE = mute/unmute mic | ENTER = interrupt Gemini | Ctrl+C = quit\n")

    try:
        async with client.aio.live.connect(model=LIVE_MODEL, config=config) as session:

            # ── Task: send mic audio ────────────────────────────────────
            async def send_audio():
                """Read mic chunks from queue and send to Gemini."""
                while running:
                    try:
                        # Non-blocking check
                        try:
                            chunk = audio_in_queue.get(timeout=0.05)
                        except queue.Empty:
                            await asyncio.sleep(0.01)
                            continue

                        await session.send_realtime_input(
                            audio=types.Blob(
                                data=chunk,
                                mime_type="audio/pcm;rate=16000",
                            )
                        )
                    except Exception as e:
                        if running:
                            print(f"[MIC ERROR] {e}")
                        break

            # ── Task: receive responses ─────────────────────────────────
            async def receive_responses():
                """Receive audio + transcripts from Gemini."""
                global running, model_speaking
                user_text = ""
                gemini_text = ""
                while running:
                    try:
                        async for response in session.receive():
                            if not running:
                                break

                            server = response.server_content
                            if server:
                                # Handle interruption — clear audio buffer
                                if getattr(server, 'interrupted', False):
                                    with buffer_lock:
                                        audio_buffer.clear()

                                # Append audio to continuous buffer
                                if server.model_turn and server.model_turn.parts:
                                    for part in server.model_turn.parts:
                                        if part.inline_data and part.inline_data.data:
                                            with buffer_lock:
                                                audio_buffer.extend(part.inline_data.data)

                                # Accumulate transcripts silently
                                if server.input_transcription:
                                    txt = server.input_transcription.text
                                    if txt and txt.strip():
                                        user_text += txt

                                if server.output_transcription:
                                    txt = server.output_transcription.text
                                    if txt and txt.strip():
                                        gemini_text += txt

                                # Turn complete — print final transcript
                                if server.turn_complete:
                                    if user_text.strip():
                                        print(f"  YOU: {user_text.strip()}")
                                    if gemini_text.strip():
                                        print(f"  GEMINI: {gemini_text.strip()}")
                                    user_text = ""
                                    gemini_text = ""

                            # Handle tool calls (future use)
                            if response.tool_call:
                                print(f"  [TOOL CALL] {response.tool_call}")

                    except Exception as e:
                        if running:
                            print(f"[RECV ERROR] {e}")
                        break

            # ── Task: keyboard listener ──────────────────────────────
            async def keyboard_listener():
                """SPACE = mute/unmute, ENTER = interrupt Gemini playback."""
                global mic_muted
                loop = asyncio.get_event_loop()
                while running:
                    key_pressed = await loop.run_in_executor(None, msvcrt.kbhit)
                    if key_pressed:
                        key = await loop.run_in_executor(None, msvcrt.getch)
                        if key == b' ':
                            mic_muted = not mic_muted
                            state = "MUTED" if mic_muted else "UNMUTED"
                            print(f"  [MIC {state}]")
                        elif key in (b'\r', b'\n'):
                            with buffer_lock:
                                audio_buffer.clear()
                            print("  [INTERRUPTED]")
                    await asyncio.sleep(0.05)

            # Run all tasks concurrently
            send_task = asyncio.create_task(send_audio())
            recv_task = asyncio.create_task(receive_responses())
            key_task = asyncio.create_task(keyboard_listener())

            # Wait until one finishes (or Ctrl+C)
            done, pending = await asyncio.wait(
                [send_task, recv_task, key_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            running = False
            for t in pending:
                t.cancel()
                try:
                    await t
                except asyncio.CancelledError:
                    pass

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        mic_stream.stop()
        mic_stream.close()
        speaker_stream.stop()
        speaker_stream.close()
        print("\n[DONE] Session ended.")


if __name__ == "__main__":
    asyncio.run(main())
