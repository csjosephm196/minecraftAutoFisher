# Minecraft Auto Fisher

Fish AFK in Minecraft and collect loot such as enchanted books, enchanted fishing
rods, enchanted bows, and name tags — without an auto-clicker, mods, or prior
building. The app simply watches your screen for the bobber sinking and
right-clicks to reel in and re-cast.

## How it works

The app watches a small box on your screen centered on the fishing bobber. When
a fish bites, the bobber dips underwater and its red/white pixels vanish from
the box — the app then right-clicks to reel in, right-clicks again to re-cast,
and keeps watching. It never reads game memory or touches the Minecraft process.

## Using the app (Windows .exe)

1. Download and run `MinecraftAutoFisher.exe`.
2. In Minecraft (windowed or borderless, not exclusive fullscreen), stand at
   your fishing spot and cast the rod. Keep the camera still from now on.
3. In the app, click **Calibrate** and click directly on the bobber. A red box
   flashes to show the watched region.
4. Press **F6** (or the Start button), switch back to Minecraft, and let it run.
   Press **F6** again to stop.

Don't move the mouse or camera while it runs. As a safety measure, slamming the
mouse into a screen corner stops the clicking (PyAutoGUI failsafe).

## Running from source

```bash
pip install -r requirements.txt
python app.py
```

Legacy scripts from before the GUI existed are still included: `autofish.py`
(console version with a hardcoded region) and `findpos.py` (prints mouse
coordinates for manual calibration).

## Building the exe

```bash
pip install pyinstaller
build.bat
```

The exe is written to `dist\MinecraftAutoFisher.exe`.

## Tips

- If the log warns about "almost no bobber-colored pixels", recalibrate — the
  box isn't centered on the bobber.
- Detection assumes the vanilla red/white bobber texture; resource packs or
  shaders may break it.
- Rain and nearby players' bobbers inside the box can cause false triggers.
- Settings (region, timings) are saved to `settings.json` next to the exe.
