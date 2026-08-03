@echo off
REM Builds a standalone MinecraftAutoFisher.exe into the dist\ folder.
REM Requires: pip install pyinstaller
REM cv2 is an optional pyscreeze dependency we don't use; excluding it shrinks the exe a lot.
pyinstaller --noconfirm --onefile --windowed --name MinecraftAutoFisher --exclude-module cv2 app.py
echo.
echo Done. The exe is at dist\MinecraftAutoFisher.exe
pause
