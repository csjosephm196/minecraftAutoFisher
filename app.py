"""Minecraft Auto Fisher — desktop app.

Watches a small region of the screen around the fishing bobber and
right-clicks to reel in / re-cast when the bobber sinks (a bite).
No memory reading, no injection — pure screen watching.

Run:  python app.py
"""

import json
import queue
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import scrolledtext, ttk

import keyboard
import numpy as np
import pyautogui

APP_NAME = "Minecraft Auto Fisher"
HOTKEY = "f6"

DEFAULT_SETTINGS = {
    "center_x": 960,
    "center_y": 540,
    "box_size": 40,
    "check_interval": 0.1,
    "cooldown": 2.0,
    "missing_frames": 3,
    "recast_delay": 0.5,
    "start_delay": 3.0,
}


def settings_path() -> Path:
    """Store settings.json next to the exe (frozen) or this script."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "settings.json"
    return Path(__file__).parent / "settings.json"


def load_settings() -> dict:
    s = dict(DEFAULT_SETTINGS)
    try:
        with open(settings_path(), "r", encoding="utf-8") as f:
            saved = json.load(f)
        s.update({k: saved[k] for k in DEFAULT_SETTINGS if k in saved})
    except (OSError, ValueError):
        pass
    return s


def save_settings(s: dict) -> None:
    try:
        with open(settings_path(), "w", encoding="utf-8") as f:
            json.dump(s, f, indent=2)
    except OSError:
        pass


# ---------------------------------------------------------------- detection


def count_bobber_pixels(frame: np.ndarray) -> int:
    r, g, b = frame[:, :, 0], frame[:, :, 1], frame[:, :, 2]
    red_mask = (r > 150) & (g < 100) & (b < 100)      # red top of bobber
    white_mask = (r > 180) & (g > 180) & (b > 180)    # white body
    return int(np.sum(red_mask | white_mask))


class FisherEngine:
    """Background thread that runs the watch/reel/re-cast loop."""

    def __init__(self, get_settings, events: queue.Queue):
        self._get_settings = get_settings
        self._events = events
        self._stop = threading.Event()
        self._thread = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self):
        if self.running:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _emit(self, kind, **data):
        self._events.put({"kind": kind, **data})

    def _region(self, s):
        half = s["box_size"] // 2
        return (int(s["center_x"] - half), int(s["center_y"] - half),
                int(s["box_size"]), int(s["box_size"]))

    def _grab_count(self, region) -> int:
        img = pyautogui.screenshot(region=region)
        return count_bobber_pixels(np.array(img).astype(int))

    def _run(self):
        try:
            s = self._get_settings()

            delay = float(s["start_delay"])
            self._emit("status", text=f"Starting in {delay:.0f}s — switch to Minecraft, cast your line...")
            end = time.monotonic() + delay
            while time.monotonic() < end:
                if self._stop.is_set():
                    self._emit("stopped")
                    return
                time.sleep(0.05)

            region = self._region(s)
            baseline = self._grab_count(region)
            self._emit("log", text=f"Watching region {region}. Baseline bobber pixels: {baseline}")
            if baseline < 3:
                self._emit("log", text="WARNING: almost no bobber-colored pixels found. "
                                       "Recalibrate so the box is centered on the bobber.")
            self._emit("status", text="Watching for bites...")

            missing = 0
            catches = 0
            while not self._stop.is_set():
                time.sleep(float(s["check_interval"]))
                count = self._grab_count(region)
                self._emit("pixels", count=count, baseline=baseline)

                if count < max(baseline * 0.3, 1):
                    missing += 1
                else:
                    missing = 0
                    baseline = max(baseline, count)

                if missing >= int(s["missing_frames"]):
                    catches += 1
                    self._emit("log", text=f"Bite detected — reeling in (catch #{catches})")
                    pyautogui.click(button="right")
                    time.sleep(float(s["recast_delay"]))
                    pyautogui.click(button="right")
                    time.sleep(float(s["cooldown"]))
                    missing = 0
                    baseline = self._grab_count(region)

            self._emit("stopped")
        except pyautogui.FailSafeException:
            self._emit("log", text="Failsafe triggered (mouse moved to a screen corner). Stopped.")
            self._emit("stopped")
        except Exception as e:  # keep the GUI alive no matter what the loop hits
            self._emit("log", text=f"Error: {e}")
            self._emit("stopped")


# ---------------------------------------------------------------------- GUI


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.settings = load_settings()
        self.events = queue.Queue()
        self.engine = FisherEngine(self.current_settings, self.events)

        root.title(APP_NAME)
        root.resizable(False, False)
        root.attributes("-topmost", True)

        pad = {"padx": 10, "pady": 4}
        main = ttk.Frame(root, padding=10)
        main.grid(sticky="nsew")

        self.status_var = tk.StringVar(value="Idle")
        ttk.Label(main, textvariable=self.status_var, font=("Segoe UI", 11, "bold")).grid(
            row=0, column=0, columnspan=3, **pad)

        self.pixels_var = tk.StringVar(value="Bobber pixels: —")
        ttk.Label(main, textvariable=self.pixels_var).grid(row=1, column=0, columnspan=3, **pad)

        # --- region ---
        region_frame = ttk.LabelFrame(main, text="Bobber region", padding=8)
        region_frame.grid(row=2, column=0, columnspan=3, sticky="ew", **pad)
        self.region_var = tk.StringVar()
        ttk.Label(region_frame, textvariable=self.region_var).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Button(region_frame, text="Calibrate (click the bobber)",
                   command=self.calibrate).grid(row=1, column=0, pady=(6, 0), sticky="ew")
        ttk.Button(region_frame, text="Show region",
                   command=self.flash_region).grid(row=1, column=1, pady=(6, 0), padx=(6, 0), sticky="ew")
        region_frame.columnconfigure(0, weight=1)
        region_frame.columnconfigure(1, weight=1)

        # --- settings ---
        settings_frame = ttk.LabelFrame(main, text="Settings", padding=8)
        settings_frame.grid(row=3, column=0, columnspan=3, sticky="ew", **pad)
        self.setting_vars = {}
        fields = [
            ("box_size", "Box size (px)", 10, 200, 5),
            ("check_interval", "Check interval (s)", 0.02, 1.0, 0.02),
            ("cooldown", "Cooldown after cast (s)", 0.5, 10.0, 0.5),
            ("missing_frames", "Missing frames for bite", 1, 10, 1),
            ("start_delay", "Start delay (s)", 0, 15, 1),
        ]
        for i, (key, label, lo, hi, step) in enumerate(fields):
            ttk.Label(settings_frame, text=label).grid(row=i, column=0, sticky="w", pady=2)
            var = tk.StringVar(value=str(self.settings[key]))
            self.setting_vars[key] = var
            ttk.Spinbox(settings_frame, textvariable=var, from_=lo, to=hi,
                        increment=step, width=8).grid(row=i, column=1, sticky="e", pady=2)
        settings_frame.columnconfigure(0, weight=1)

        # --- start/stop ---
        self.toggle_btn = ttk.Button(main, text=f"Start  ({HOTKEY.upper()})", command=self.toggle)
        self.toggle_btn.grid(row=4, column=0, columnspan=3, sticky="ew", **pad)
        ttk.Label(main, text=f"Press {HOTKEY.upper()} to start/stop while Minecraft is focused.",
                  foreground="#666").grid(row=5, column=0, columnspan=3)

        # --- log ---
        self.log_box = scrolledtext.ScrolledText(main, width=52, height=10, state="disabled",
                                                 font=("Consolas", 9))
        self.log_box.grid(row=6, column=0, columnspan=3, **pad)

        self.update_region_label()
        self.log("Calibrate the bobber region, cast your rod in-game, then press "
                 f"{HOTKEY.upper()} or Start.")

        try:
            keyboard.add_hotkey(HOTKEY, lambda: self.root.after(0, self.toggle))
        except Exception:
            self.log(f"Could not register the {HOTKEY.upper()} hotkey; use the Start button.")

        root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(50, self.poll_events)

    # ---- settings plumbing ----

    def current_settings(self) -> dict:
        s = dict(self.settings)
        for key, var in self.setting_vars.items():
            try:
                val = float(var.get())
                s[key] = int(val) if key in ("box_size", "missing_frames") else val
            except ValueError:
                pass
        self.settings = s
        save_settings(s)
        return s

    def update_region_label(self):
        s = self.settings
        self.region_var.set(f"Center: ({s['center_x']}, {s['center_y']})   "
                            f"Box: {s['box_size']}x{s['box_size']} px")

    # ---- calibration ----

    def calibrate(self):
        if self.engine.running:
            self.log("Stop the fisher before calibrating.")
            return
        self.log("Click directly on the bobber. Press Esc to cancel.")
        overlay = tk.Toplevel(self.root)
        overlay.attributes("-fullscreen", True)
        overlay.attributes("-alpha", 0.25)
        overlay.attributes("-topmost", True)
        overlay.configure(bg="black", cursor="crosshair")
        tk.Label(overlay, text="Click on the bobber  (Esc to cancel)",
                 font=("Segoe UI", 18, "bold"), fg="white", bg="black").pack(pady=60)

        def picked(event):
            self.settings["center_x"] = event.x_root
            self.settings["center_y"] = event.y_root
            save_settings(self.current_settings())
            self.update_region_label()
            overlay.destroy()
            self.log(f"Region centered at ({event.x_root}, {event.y_root}).")
            self.flash_region()

        overlay.bind("<Button-1>", picked)
        overlay.bind("<Escape>", lambda e: overlay.destroy())
        overlay.focus_force()

    def flash_region(self):
        s = self.current_settings()
        half = int(s["box_size"]) // 2
        x, y, size = int(s["center_x"]) - half, int(s["center_y"]) - half, int(s["box_size"])
        box = tk.Toplevel(self.root)
        box.overrideredirect(True)
        box.attributes("-topmost", True)
        box.attributes("-alpha", 0.5)
        box.configure(bg="red")
        box.geometry(f"{size}x{size}+{x}+{y}")
        box.after(1500, box.destroy)

    # ---- run control ----

    def toggle(self):
        if self.engine.running:
            self.engine.stop()
            self.status_var.set("Stopping...")
        else:
            self.current_settings()
            self.engine.start()
            self.toggle_btn.config(text=f"Stop  ({HOTKEY.upper()})")

    def poll_events(self):
        try:
            while True:
                ev = self.events.get_nowait()
                kind = ev["kind"]
                if kind == "log":
                    self.log(ev["text"])
                elif kind == "status":
                    self.status_var.set(ev["text"])
                elif kind == "pixels":
                    self.pixels_var.set(f"Bobber pixels: {ev['count']}  (baseline {ev['baseline']})")
                elif kind == "stopped":
                    self.status_var.set("Idle")
                    self.pixels_var.set("Bobber pixels: —")
                    self.toggle_btn.config(text=f"Start  ({HOTKEY.upper()})")
                    self.log("Stopped.")
        except queue.Empty:
            pass
        self.root.after(50, self.poll_events)

    def log(self, text: str):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", time.strftime("[%H:%M:%S] ") + text + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def on_close(self):
        self.engine.stop()
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass
        self.root.destroy()


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
