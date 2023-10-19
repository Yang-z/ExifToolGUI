@echo off
rem Run PyInstaller command
pyinstaller --onefile --noconsole --strip exiftoolgui.py
xcopy /s /e /y ".\config\" ".\dist\config\"

rem Pause to view the output (optional)
pause