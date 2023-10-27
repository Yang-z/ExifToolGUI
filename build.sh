#!/bin/bash
# Run PyInstaller command
pyinstaller --onefile --noconsole --strip exiftoolgui.py
cp -r configs/ dist/

# Wait for user input to view the output (optional)
read -p "Press enter to continue"