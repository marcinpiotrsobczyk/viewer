@echo off
cd /d "%~dp0\.."
pip install pyinstaller
pyinstaller --onefile --windowed --name ImageViewer ^
    --exclude-module tkinter ^
    --exclude-module matplotlib ^
    --exclude-module numpy ^
    main.py
echo Build complete: dist\ImageViewer.exe
