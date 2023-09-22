@echo off
rem Run PyInstaller command
pyinstaller --onefile --noconsole exiftoolgui.py
xcopy /s /e ".\config\" ".\dist\config\"

rem Pause to view the output (optional)
pause