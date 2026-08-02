import pyautogui
import numpy as np
import time

# ---- SETTINGS ----
REGION = (941, 523, 40, 40)   # (left, top, width, height) — tight box around bobber

CHECK_INTERVAL = 0.1
COOLDOWN = 2.0
MISSING_FRAMES_NEEDED = 3   # how many consecutive "bobber gone" frames before reeling


def get_frame(region):
    img = pyautogui.screenshot(region=region)
    return np.array(img).astype(int)


def count_bobber_pixels(frame):
    r, g, b = frame[:, :, 0], frame[:, :, 1], frame[:, :, 2]
    # red part of bobber: high red, low green/blue
    red_mask = (r > 150) & (g < 100) & (b < 100)
    # white part of bobber: all channels high
    white_mask = (r > 180) & (g > 180) & (b > 180)
    return int(np.sum(red_mask | white_mask))


def main():
    print("Starting in 6 seconds — alt-tab to Minecraft, cast your line so the bobber is visible...")
    time.sleep(6)

    baseline_count = count_bobber_pixels(get_frame(REGION))
    print(f"Bobber baseline pixel count: {baseline_count}")
    if baseline_count < 3:
        print("WARNING: barely any bobber-colored pixels detected. Check your REGION is centered correctly.\n")
    print("Watching for bites...\n")

    missing_streak = 0

    while True:
        time.sleep(CHECK_INTERVAL)
        frame = get_frame(REGION)
        bobber_count = count_bobber_pixels(frame)
        print(f"bobber pixels: {bobber_count}")

        if bobber_count < max(baseline_count * 0.3, 1):
            missing_streak += 1
        else:
            missing_streak = 0
            baseline_count = max(baseline_count, bobber_count)  # track true baseline when visible

        if missing_streak >= MISSING_FRAMES_NEEDED:
            print("Bobber disappeared — fish on! Reeling in\n")
            pyautogui.click(button='right')
            time.sleep(0.5)
            pyautogui.click(button='right')
            time.sleep(COOLDOWN)
            missing_streak = 0
            baseline_count = count_bobber_pixels(get_frame(REGION))


if __name__ == "__main__":
    main()