@echo off
rem Run PyInstaller command
pyinstaller --onefile --noconsole --strip exiftoolgui.py
xcopy /s /e /y ".\configs\" ".\dist\configs\"

rem Pause to view the output (optional)
pause