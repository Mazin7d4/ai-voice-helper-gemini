"""
gui/overlay.py — Premium dark GUI for the AI Voice Helper.

Tesla / Grok inspired design:
  - Deep black background with glowing cyan/electric blue accents
  - Pulsing status indicators
  - Glowing borders and neon highlights
  - Clean, minimal layout with premium typography
"""

import tkinter as tk
from tkinter import scrolledtext
import threading
import queue
import sys
import os
import time

# Add parent dir to path so we can import agent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent import (
    start_agent, submit_goal, submit_describe,
    stop_agent, quit_app, status_queue, quit_event,
    mic_muted, handle_key_space, handle_key_enter, handle_key_escape,
)

# ── Premium Color Palette (Tesla/Grok inspired) ──
BG_DEEP = "#0a0a0f"        # near-black background
BG_SURFACE = "#12121a"     # card surface
BG_ELEVATED = "#1a1a2e"    # elevated sections
BORDER = "#1e1e3a"         # subtle borders
GLOW_CYAN = "#00d4ff"      # primary glow — electric cyan
GLOW_BLUE = "#4488ff"      # secondary glow — blue
GLOW_GREEN = "#00ff88"     # success / mic on
GLOW_RED = "#ff3366"       # danger / error
GLOW_AMBER = "#ffaa00"     # warning / thinking
GLOW_PURPLE = "#aa44ff"    # accent purple
TEXT_PRIMARY = "#e8eaed"   # primary text — near white
TEXT_SECONDARY = "#8892a4" # secondary text — muted
TEXT_DIM = "#4a5568"       # very dim text


class VoiceHelperApp:
    """Premium dark GUI window for the AI Voice Helper."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AI Voice Helper")
        self.root.geometry("780x900")
        self.root.configure(bg=BG_DEEP)
        self.root.resizable(True, True)
        self.root.attributes("-topmost", True)
        self.root.minsize(600, 700)

        # Remove default window decorations styling
        try:
            self.root.iconbitmap(default="")
        except Exception:
            pass

        self._pulse_state = True
        self._build_ui()
        self._bind_keys()

        # Start polling status queue
        self.root.after(50, self._poll_status)

        # Start pulsing animation
        self.root.after(800, self._pulse_animation)

    def _make_glow_frame(self, parent, glow_color=GLOW_CYAN, pad=1):
        """Create a frame with a glowing border effect."""
        outer = tk.Frame(parent, bg=glow_color, padx=pad, pady=pad)
        inner = tk.Frame(outer, bg=BG_SURFACE)
        inner.pack(fill="both", expand=True)
        return outer, inner

    def _build_ui(self):
        """Build all UI elements with premium styling."""

        # ── Header bar with glow underline ──
        header = tk.Frame(self.root, bg=BG_DEEP)
        header.pack(fill="x", padx=0, pady=0)

        header_inner = tk.Frame(header, bg=BG_DEEP)
        header_inner.pack(fill="x", padx=24, pady=(16, 8))

        # App title — clean, minimal
        title_label = tk.Label(
            header_inner, text="AI VOICE HELPER",
            font=("Segoe UI", 24, "bold"), bg=BG_DEEP, fg=GLOW_CYAN,
        )
        title_label.pack(side="left")

        # Mic status — glowing indicator
        self.mic_frame = tk.Frame(header_inner, bg=BG_DEEP)
        self.mic_frame.pack(side="right")

        self.mic_dot = tk.Label(
            self.mic_frame, text="●", font=("Segoe UI", 16),
            bg=BG_DEEP, fg=GLOW_GREEN,
        )
        self.mic_dot.pack(side="left", padx=(0, 6))

        self.mic_label = tk.Label(
            self.mic_frame, text="LISTENING",
            font=("Segoe UI", 12, "bold"), bg=BG_DEEP, fg=GLOW_GREEN,
        )
        self.mic_label.pack(side="left")

        # Glowing accent line under header
        glow_line = tk.Frame(self.root, bg=GLOW_CYAN, height=2)
        glow_line.pack(fill="x", padx=24)
        self._glow_line = glow_line

        # ── Status card ──
        status_outer, status_inner = self._make_glow_frame(self.root, BORDER)
        status_outer.pack(fill="x", padx=24, pady=(12, 4))

        status_row = tk.Frame(status_inner, bg=BG_SURFACE)
        status_row.pack(fill="x", padx=16, pady=10)

        tk.Label(
            status_row, text="STATUS",
            font=("Segoe UI", 10, "bold"), bg=BG_SURFACE, fg=TEXT_DIM,
        ).pack(side="left")

        self.status_var = tk.StringVar(value="⏳ Initializing...")
        self.status_label = tk.Label(
            status_row, textvariable=self.status_var,
            font=("Segoe UI", 14, "bold"), bg=BG_SURFACE, fg=GLOW_AMBER,
        )
        self.status_label.pack(side="left", padx=12)

        # ── Goal card ──
        goal_outer, goal_inner = self._make_glow_frame(self.root, BORDER)
        goal_outer.pack(fill="x", padx=24, pady=4)

        goal_row = tk.Frame(goal_inner, bg=BG_SURFACE)
        goal_row.pack(fill="x", padx=16, pady=10)

        tk.Label(
            goal_row, text="GOAL",
            font=("Segoe UI", 10, "bold"), bg=BG_SURFACE, fg=TEXT_DIM,
        ).pack(side="left")

        self.goal_var = tk.StringVar(value="Speak or type a command...")
        self.goal_label = tk.Label(
            goal_row, textvariable=self.goal_var,
            font=("Segoe UI", 13), bg=BG_SURFACE, fg=TEXT_PRIMARY,
            wraplength=550, justify="left", anchor="w",
        )
        self.goal_label.pack(side="left", padx=12, fill="x", expand=True)

        # ── Action Log ──
        log_header = tk.Frame(self.root, bg=BG_DEEP)
        log_header.pack(fill="x", padx=24, pady=(12, 2))

        tk.Label(
            log_header, text="─── ACTIVITY LOG ───",
            font=("Segoe UI", 10, "bold"), bg=BG_DEEP, fg=TEXT_DIM,
        ).pack(side="left")

        log_outer, log_inner = self._make_glow_frame(self.root, BORDER)
        log_outer.pack(fill="both", expand=True, padx=24, pady=(0, 8))

        self.log_text = scrolledtext.ScrolledText(
            log_inner,
            font=("Cascadia Code", 11),
            bg=BG_SURFACE, fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            relief="flat",
            height=14,
            wrap="word",
            state="disabled",
            borderwidth=0,
            highlightthickness=0,
            selectbackground=GLOW_BLUE,
            selectforeground=TEXT_PRIMARY,
        )
        self.log_text.pack(fill="both", expand=True, padx=2, pady=2)

        # Premium tag colors
        self.log_text.tag_configure("user", foreground=GLOW_CYAN)
        self.log_text.tag_configure("gemini", foreground=GLOW_GREEN)
        self.log_text.tag_configure("action", foreground=TEXT_SECONDARY)
        self.log_text.tag_configure("error", foreground=GLOW_RED)
        self.log_text.tag_configure("system", foreground=GLOW_AMBER)

        # ── Input Section ──
        input_outer, input_inner = self._make_glow_frame(self.root, GLOW_CYAN)
        input_outer.pack(fill="x", padx=24, pady=(4, 8))

        input_row = tk.Frame(input_inner, bg=BG_SURFACE)
        input_row.pack(fill="x", padx=8, pady=8)

        self.goal_entry = tk.Entry(
            input_row, font=("Segoe UI", 14),
            bg=BG_ELEVATED, fg=TEXT_PRIMARY, insertbackground=GLOW_CYAN,
            relief="flat", highlightthickness=0,
        )
        self.goal_entry.pack(side="left", fill="x", expand=True, padx=(4, 8), ipady=8)
        self.goal_entry.insert(0, "")
        self.goal_entry.bind("<Return>", self._on_submit_goal)
        self.goal_entry.bind("<FocusIn>", lambda e: self.goal_entry.config(bg="#1e1e3a"))
        self.goal_entry.bind("<FocusOut>", lambda e: self.goal_entry.config(bg=BG_ELEVATED))

        self.submit_btn = tk.Button(
            input_row, text="▶  GO", font=("Segoe UI", 13, "bold"),
            bg=GLOW_CYAN, fg=BG_DEEP,
            activebackground=GLOW_BLUE, activeforeground=BG_DEEP,
            relief="flat", cursor="hand2",
            padx=20, pady=6,
            command=self._on_submit_goal,
        )
        self.submit_btn.pack(side="right")

        # ── Control Buttons ──
        btn_frame = tk.Frame(self.root, bg=BG_DEEP)
        btn_frame.pack(fill="x", padx=24, pady=(0, 8))

        # Mute button
        self.mute_btn = tk.Button(
            btn_frame, text="🎤  MUTE", font=("Segoe UI", 11, "bold"),
            bg=BG_ELEVATED, fg=TEXT_PRIMARY,
            activebackground=BORDER, activeforeground=TEXT_PRIMARY,
            relief="flat", cursor="hand2",
            command=self._toggle_mute, width=14, pady=8,
            highlightthickness=0,
        )
        self.mute_btn.pack(side="left", padx=(0, 6))

        # Describe button
        self.describe_btn = tk.Button(
            btn_frame, text="👁  DESCRIBE", font=("Segoe UI", 11, "bold"),
            bg=BG_ELEVATED, fg=TEXT_PRIMARY,
            activebackground=BORDER, activeforeground=TEXT_PRIMARY,
            relief="flat", cursor="hand2",
            command=lambda: submit_describe(), width=14, pady=8,
            highlightthickness=0,
        )
        self.describe_btn.pack(side="left", padx=6)

        # Stop button — red glow
        self.stop_btn = tk.Button(
            btn_frame, text="⏹  STOP", font=("Segoe UI", 11, "bold"),
            bg=GLOW_RED, fg=TEXT_PRIMARY,
            activebackground="#cc2952", activeforeground=TEXT_PRIMARY,
            relief="flat", cursor="hand2",
            command=lambda: stop_agent(), width=14, pady=8,
            highlightthickness=0,
        )
        self.stop_btn.pack(side="right", padx=(6, 0))

        # Quit button
        self.quit_btn = tk.Button(
            btn_frame, text="✕  QUIT", font=("Segoe UI", 11, "bold"),
            bg=BG_ELEVATED, fg=TEXT_SECONDARY,
            activebackground=BORDER, activeforeground=TEXT_PRIMARY,
            relief="flat", cursor="hand2",
            command=self._on_quit, width=14, pady=8,
            highlightthickness=0,
        )
        self.quit_btn.pack(side="right", padx=6)

        # ── Bottom status bar ──
        bottom_bar = tk.Frame(self.root, bg=BG_ELEVATED, height=36)
        bottom_bar.pack(fill="x", side="bottom")
        bottom_bar.pack_propagate(False)

        tk.Label(
            bottom_bar,
            text="SPACE  mute   │   ENTER  stop   │   ESC  quit",
            font=("Cascadia Code", 9), bg=BG_ELEVATED, fg=TEXT_DIM,
        ).pack(expand=True)

    def _pulse_animation(self):
        """Animate the mic dot and glow line for a living, breathing feel."""
        if quit_event.is_set():
            return

        self._pulse_state = not self._pulse_state

        if not mic_muted.is_set():
            if self._pulse_state:
                self.mic_dot.config(fg=GLOW_GREEN)
                self._glow_line.config(bg=GLOW_CYAN)
            else:
                self.mic_dot.config(fg="#00aa55")
                self._glow_line.config(bg=GLOW_BLUE)
        else:
            self.mic_dot.config(fg=GLOW_RED if self._pulse_state else "#aa2244")

        self.root.after(800, self._pulse_animation)

    def _bind_keys(self):
        """Bind keyboard shortcuts."""
        self.root.bind("<Escape>", lambda e: handle_key_escape())
        self.root.bind("<space>", self._on_space)
        self.root.bind("<Return>", self._on_enter)

    def _on_space(self, event):
        """Space = mute toggle, unless typing in the goal entry."""
        if event.widget == self.goal_entry:
            return
        handle_key_space()
        return "break"

    def _on_enter(self, event):
        """Enter = stop agent, unless typing in the goal entry (then submit)."""
        if event.widget == self.goal_entry:
            self._on_submit_goal(event)
            return "break"
        handle_key_enter()
        return "break"

    def _on_submit_goal(self, event=None):
        """Submit a goal from the text entry."""
        text = self.goal_entry.get().strip()
        if text:
            submit_goal(text)
            self.goal_var.set(text)
            self._log(f"▶ {text}", "system")
            self.goal_entry.delete(0, "end")

    def _toggle_mute(self):
        """Toggle mic mute via button."""
        if mic_muted.is_set():
            mic_muted.clear()
            self.mic_label.config(text="LISTENING", fg=GLOW_GREEN)
            self.mic_dot.config(fg=GLOW_GREEN)
            self.mute_btn.config(text="🎤  MUTE")
        else:
            mic_muted.set()
            self.mic_label.config(text="MUTED", fg=GLOW_RED)
            self.mic_dot.config(fg=GLOW_RED)
            self.mute_btn.config(text="🔊  UNMUTE")

    def _on_quit(self):
        """Quit the app."""
        quit_app()
        self.root.after(200, self.root.destroy)

    def _log(self, text: str, tag: str = "action"):
        """Append a line to the action log."""
        self.log_text.config(state="normal")
        self.log_text.insert("end", text + "\n", tag)
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def _poll_status(self):
        """Poll the status queue and update GUI."""
        try:
            while True:
                status_type, data = status_queue.get_nowait()

                if status_type == "voice_ready":
                    self.status_var.set("🎤 Ready — Listening")
                    self.status_label.config(fg=GLOW_GREEN)
                    self._log("Voice connected. Speak or type a goal.", "system")

                elif status_type == "status":
                    self.status_var.set(data)
                    # Color the status based on content
                    if "done" in data.lower() or "stopped" in data.lower():
                        self.status_label.config(fg=GLOW_GREEN)
                    elif "error" in data.lower() or "⚠" in data:
                        self.status_label.config(fg=GLOW_RED)
                    elif "📸" in data or "capturing" in data.lower():
                        self.status_label.config(fg=GLOW_PURPLE)
                    elif "🧠" in data or "analyz" in data.lower():
                        self.status_label.config(fg=GLOW_BLUE)
                    elif "⚡" in data or "execut" in data.lower():
                        self.status_label.config(fg=GLOW_CYAN)
                    elif "✅" in data or "verif" in data.lower():
                        self.status_label.config(fg=GLOW_AMBER)
                    else:
                        self.status_label.config(fg=GLOW_AMBER)

                elif status_type == "goal":
                    self.goal_var.set(data)

                elif status_type == "action_log":
                    self._log(data, "action")

                elif status_type == "user_speech":
                    self._log(f"You: {data}", "user")

                elif status_type == "gemini_speech":
                    self._log(f"Gemini: {data}", "gemini")

                elif status_type == "error":
                    self._log(f"⚠ ERROR: {data}", "error")
                    self.status_var.set(f"⚠ {data[:50]}")
                    self.status_label.config(fg=GLOW_RED)

                elif status_type == "mic":
                    if data == "muted":
                        self.mic_label.config(text="MUTED", fg=GLOW_RED)
                        self.mic_dot.config(fg=GLOW_RED)
                        self.mute_btn.config(text="🔊  UNMUTE")
                    else:
                        self.mic_label.config(text="LISTENING", fg=GLOW_GREEN)
                        self.mic_dot.config(fg=GLOW_GREEN)
                        self.mute_btn.config(text="🎤  MUTE")

                elif status_type == "minimize":
                    self.root.iconify()

                elif status_type == "restore":
                    self.root.deiconify()
                    self.root.lift()

                elif status_type == "quit":
                    self.root.after(100, self.root.destroy)
                    return

        except queue.Empty:
            pass

        if not quit_event.is_set():
            self.root.after(50, self._poll_status)

    def run(self):
        """Start agent threads and run the GUI."""
        start_agent()
        self.root.mainloop()


def main():
    app = VoiceHelperApp()
    app.run()


if __name__ == "__main__":
    main()
