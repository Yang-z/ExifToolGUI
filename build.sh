#!/bin/bash
# Run PyInstaller command
pyinstaller --onefile --noconsole exiftoolgui.py
cp -r config/ dist/

# Wait for user input to view the output (optional)
read -p "Press enter to continue"