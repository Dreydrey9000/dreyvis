#!/bin/bash
# Builds Dreyvis.app from the Electron in node_modules and installs it in ~/Applications.
# Manual packaging (no extra tools): copy Electron.app, rename it, drop our code in Resources/app.
set -euo pipefail
cd "$(dirname "$0")"
OUT="dist/Dreyvis.app"
rm -rf dist && mkdir -p dist
cp -R node_modules/electron/dist/Electron.app "$OUT"
mkdir -p "$OUT/Contents/Resources/app"
cp package.json main.js preload.js off.html "$OUT/Contents/Resources/app/"
[ -f trayTemplate.png ] && cp trayTemplate.png trayTemplate@2x.png "$OUT/Contents/Resources/app/" 2>/dev/null || true
mv "$OUT/Contents/MacOS/Electron" "$OUT/Contents/MacOS/Dreyvis"
P="$OUT/Contents/Info.plist"
plutil -replace CFBundleExecutable -string Dreyvis "$P"
plutil -replace CFBundleName -string Dreyvis "$P"
plutil -replace CFBundleDisplayName -string Dreyvis "$P"
plutil -replace CFBundleIdentifier -string com.drey.dreyvis.app "$P"
plutil -replace NSMicrophoneUsageDescription -string "Dreyvis listens for your voice." "$P"
if [ -f icon.icns ]; then cp icon.icns "$OUT/Contents/Resources/electron.icns"; fi
codesign --force --deep --sign - "$OUT" >/dev/null 2>&1   # ad-hoc signature so macOS remembers the mic permission
mkdir -p "$HOME/Applications"
rm -rf "$HOME/Applications/Dreyvis.app"
cp -R "$OUT" "$HOME/Applications/Dreyvis.app"
echo "Installed $HOME/Applications/Dreyvis.app"
