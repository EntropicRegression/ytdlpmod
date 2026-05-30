@echo off
title yt-dlp Premium GUI Compiler and Packager
echo ==========================================
echo       yt-dlp Premium GUI Packager
echo ==========================================
echo.
echo Step 1: Cleaning previous builds...
if exist dist\yt-dlp-gui rd /s /q dist\yt-dlp-gui
if exist build rd /s /q build
if exist yt-dlp-gui.zip del /f /q yt-dlp-gui.zip

echo.
echo Step 2: Compiling standalone executable using PyInstaller...
pyinstaller yt-dlp-gui.spec --clean

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Compilation failed! Please check PyInstaller output.
    pause
    exit /b 1
)

echo.
echo Step 3: Verifying build outputs...
if not exist dist\yt-dlp-gui\yt-dlp-gui.exe (
    echo [ERROR] Compiled executable 'yt-dlp-gui.exe' was not found in 'dist\yt-dlp-gui'!
    pause
    exit /b 1
)

echo.
echo Step 4: Bundling into a portable ZIP archive...
powershell -Command "Compress-Archive -Path dist\yt-dlp-gui -DestinationPath yt-dlp-gui.zip -Force"

if %ERRORLEVEL% neq 0 (
    echo [ERROR] Zipping failed!
    pause
    exit /b 1
)

echo.
echo ==========================================
echo 🎉 SUCCESS! Standalone GUI compiled and packaged!
echo Output ZIP archive: yt-dlp-gui.zip
echo Output Directory: dist\yt-dlp-gui\
echo ==========================================
echo.
pause
