@echo off
echo Installing dependencies...
pip install -r requirements.txt
pip install pyinstaller==6.15.0

echo Building OpenAIUsageTray.exe...
python -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name OpenAIUsageTray ^
    --manifest dpi_aware.manifest ^
    main.py

echo.
echo Done! Executable: dist\OpenAIUsageTray.exe
