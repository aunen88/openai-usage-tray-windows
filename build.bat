@echo off
echo Installing dependencies...
pip install -r requirements.txt
pip install "pefile==2023.2.7"
pip install "pyinstaller==6.15.0"

echo Building OpenAIUsageTray.exe...
python -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name OpenAIUsageTray ^
    --icon chatgpt_icon.ico ^
    --manifest dpi_aware.manifest ^
    --add-data "chatgpt_icon.png;." ^
    main.py

echo.
echo Done! Executable: dist\OpenAIUsageTray.exe
