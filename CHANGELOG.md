# Changelog

## [2026-11-18]
### Added
- Dreyvis.app (Electron 45): its own window, menu-bar on/off switch, Option+Space mic mute, open at login. Replaces using a browser tab.
- Local ears: Whisper on Apple Silicon behind `/api/transcribe`, because Electron's built-in speech recognition refuses to run.
- `ask_model` tool: Dreyvis can hand a question to Codex, Grok or DeepSeek.
- Standalone orb demo at dreydrey9000.github.io/dreyvis/orb, also saved in Drey Design.
- Background service `com.drey.dreyvis`, so the server starts at login and restarts if it crashes.

- Composio bridge (composio_search, composio_execute): Gmail and 1,000+ apps; execute is an acting tool and its results count as outside text.
- 1BB connected through connections.json.
- Connectors page (`/connectors`, Cmd+3, a button on the orb): 40 recommended apps plus search over all 1,000 Composio apps, with one-click sign-in links that update on their own. Built so adding an app no longer needs a terminal.
- Connectors page redesign (Shelves layout on Aurora Glass, picked from a six-option board in docs/theme-board): rows for Sign in again, Connected, Popular and From Claude Code, unique app badges, its own remove dialog, and a pause button for the background motion.
- Import from Claude Code: one click copies a connector from ~/.claude.json. Utopia, Omi, Firecrawl and Zernio were added this way.
- Saving or removing a custom connector no longer restarts the brain; the page asks first, so you don't lose the current chat by surprise.
- Connector statuses answer from a cache and refresh in the background, so the page opens in about 0.06s instead of 3 to 46s.
- Custom connectors: add any remote MCP server by address and optional key. It's saved 0600 in connections.json, the key never goes back to the page, and the brain restarts on its own (builds are separate processes, so they keep running).
- Dashboard opens inside the app: a button on the orb, Cmd+1 / Cmd+2, and the menu-bar item.
- Animated orb GIF in the README.

### Fixed
- Grok runs inside a macOS sandbox (grok.sb): its CLI can run commands and its tool flags don't stop that, so an injected question could have made it act on the Mac.
- Codex, Grok and DeepSeek calls get a minimal environment instead of all of Dreyvis's settings.

### Changed
- Renamed to Dreyvis: app, window, persona, process name.
- The settings panel no longer asks for a Fish Audio key when the local voice is on.

## [2026-11-16]
### Added
- Local Kokoro voice instead of paid Fish Audio, switched on with `JARVIS_TTS=kokoro`.
- `start.sh` to run the server under a real process name.
