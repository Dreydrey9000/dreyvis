#!/bin/bash
# Start Dreyvis (local Kokoro voice, no Vite).
# Used by the launchd service; Dreyvis.app shows the page.
cd "$(dirname "$0")" || exit 1
exec .venv/bin/python "$HOME/.local/bin/pyname" dreyvis server.py --host 127.0.0.1 --port 8340
