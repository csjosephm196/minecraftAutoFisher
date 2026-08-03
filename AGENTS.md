# AGENTS.md — Minecraft Auto Fisher

## What this project is

A screen-watching Minecraft auto-fisher for Windows, distributed on SourceForge
as a standalone .exe. It does NOT read game memory, inject into the client, or
use an auto-clicker. It watches a small region of the screen where the fishing
bobber sits, detects when the bobber dips underwater (a fish bite), and sends
two right-clicks: one to reel in, one to re-cast.

The player sets things up manually: stand still in-game, cast the rod, and
calibrate the app so its watch box is centered on the bobber.

## Files

| File | Purpose |
|---|---|
| `app.py` | The app. Tkinter GUI + threaded detection engine. This is what gets built into the exe. |
| `build.bat` | PyInstaller build: produces `dist\MinecraftAutoFisher.exe` (onefile, windowed). |
| `requirements.txt` | Runtime deps: `pyautogui`, `numpy`, `keyboard` (tkinter is stdlib). |
| `autofish.py` | Legacy console version with a hardcoded `REGION` constant. Same detection logic as the app. |
| `findpos.py` | Legacy calibration helper: prints mouse coordinates on `p`, quits on `q`. Superseded by the app's click-to-calibrate overlay. |
| `settings.json` | Created at runtime next to the exe/script; persisted user settings. Not committed. |

## Architecture of `app.py`

- `FisherEngine` — the detection loop, runs on a daemon thread. Communicates
  with the GUI exclusively through a `queue.Queue` of event dicts
  (`log`, `status`, `pixels`, `stopped`); the GUI polls the queue with
  `root.after(50, ...)`. Never touch tkinter from the engine thread.
- `App` — the tkinter GUI: status line, live pixel count, region calibration,
  settings spinboxes, start/stop button, scrolling log.
- Global **F6 hotkey** (via `keyboard.add_hotkey`) toggles start/stop so the
  user can control it while Minecraft has focus. The callback hops to the
  tkinter thread with `root.after(0, ...)`.
- **Calibration**: a fullscreen 25%-alpha black `Toplevel` overlay; the user
  clicks the bobber and `event.x_root/y_root` become the region center.
  "Show region" flashes a red translucent `Toplevel` over the watch box.
- **Settings** are stored in `settings.json` next to the exe when frozen
  (`sys.frozen` → `sys.executable` dir) or next to `app.py` otherwise.
  Keys: `center_x`, `center_y`, `box_size`, `check_interval`, `cooldown`,
  `missing_frames`, `recast_delay`, `start_delay`.

## How detection works

1. The watch region is a `box_size`² (default 40x40) pixel box centered on the
   calibrated point, in absolute screen coordinates.
2. Every `check_interval` (0.1 s) the engine screenshots the region with
   `pyautogui` and counts "bobber-colored" pixels via numpy masks:
   - red part: `r > 150 & g < 100 & b < 100`
   - white part: `r > 180 & g > 180 & b > 180`
3. On start it records a `baseline` count (logs a warning if < 3 — region
   probably mis-centered). Baseline ratchets upward whenever the bobber is
   visible.
4. A bite is declared when the count drops below `max(baseline * 0.3, 1)` for
   `missing_frames` (3) consecutive frames.
5. On a bite: right-click (reel in), wait `recast_delay` (0.5 s), right-click
   (re-cast), wait `cooldown` (2.0 s), re-measure baseline.
6. `pyautogui.FailSafeException` (mouse slammed into a screen corner) is caught
   and stops the engine cleanly — this is the user's emergency stop.

## Build and release

- Build: `pip install pyinstaller` then run `build.bat`
  (`pyinstaller --onefile --windowed --name MinecraftAutoFisher app.py`).
- Output: `dist\MinecraftAutoFisher.exe`. `build/`, `dist/`, and `*.spec` are
  build artifacts.
- Release target is SourceForge; the .exe is the primary artifact.
- Expect antivirus false positives with PyInstaller onefile builds — a known
  tradeoff, worth mentioning in release notes.

## Gotchas for future agents

- Coordinates are absolute screen pixels, not window-relative. `pyautogui`
  clicks land wherever the OS cursor is, so Minecraft must stay focused and the
  mouse untouched while running.
- Minecraft must be windowed/borderless (exclusive fullscreen screenshots can
  fail), camera perfectly still. Changing FOV, GUI scale, resolution, or camera
  angle invalidates calibration.
- The color masks assume the vanilla red/white bobber against darker water.
  Resource packs, shaders, sky glare, or rain can break detection.
- The engine never verifies a re-cast succeeded (rod broke, missed the water);
  there is no failure recovery.
- The `keyboard` lib hooks globally; on some setups hotkey registration can
  fail — the app logs it and falls back to the Start button.
- DPI scaling: on scaled displays tkinter's `x_root` and pyautogui screenshots
  must agree. If detection is offset for a user, suspect Windows display
  scaling first.
