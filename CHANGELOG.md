# Changelog

## [2026-11-18]
### Added
- Dreyvis.app (Electron 45): its own window, menu-bar on/off switch, Option+Space mic mute, open at login. Replaces using a browser tab.
- Local ears: Whisper on Apple Silicon behind `/api/transcribe`, because Electron's built-in speech recognition refuses to run.
- `ask_model` tool: Dreyvis can hand a question to Codex, Grok or DeepSeek.
- Background service `com.drey.dreyvis`, so the server starts at login and restarts if it crashes.

### Changed
- Renamed to Dreyvis: app, window, persona, process name.
- The settings panel no longer asks for a Fish Audio key when the local voice is on.

## [2026-11-16]
### Added
- Local Kokoro voice instead of paid Fish Audio, switched on with `JARVIS_TTS=kokoro`.
- `start.sh` to run the server under a real process name.
