import pyautogui
import keyboard
import time

print("Hover your mouse over the bobber, then press 'p' to print its position.")
print("Press 'q' to quit.")

while True:
    if keyboard.is_pressed('p'):
        x, y = pyautogui.position()
        print(f"Position captured: X={x} Y={y}")
        time.sleep(0.3)  # avoid multiple triggers from one press
    if keyboard.is_pressed('q'):
        print("Quitting.")
        break