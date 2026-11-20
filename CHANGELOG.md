# Changelog

## [2026-11-20]
### Added
- Jax Desktop: the assistant can run on the closet PC as an always-on service. A Windows task named "Jax" starts jax_service.py at sign-in and re-checks every 5 minutes; the service restarts the server if it stops, and a JAX_OFF file turns it off. Listening uses whisper.cpp on the PC (ears_worker_cpp.py), because the Mac's mlx-whisper only runs on Apple chips. The Mac reaches it with the `jax-pc` command (a private SSH tunnel to 127.0.0.1:8341).
- Jax plan (docs/jax): the assistant on the closet PC, reached from anywhere through the VPS behind Google sign-in, with a diagram. A plan only; it waits on Drey's yes.

### Fixed
- The server and brain now start on Windows. Four Unix-only spots blocked it: a date limit in the usage scanner, the stack-dump signal, splitting the Claude path with shell rules (which ate the backslashes), and the tool token's Unix-only file calls. On Windows the brain runs the real claude.exe, because npm's claude.cmd goes through cmd.exe's 8,191-character limit.
- 93 brain and build tests had been failing because the repo path has a space ("My Apps"); the fake Claude path is quoted now.
- Dashboard: the run drawer is a right-hand drawer again (a style rule had dropped it into the page at the left), opaque, below the sticky header, and full width on phones. A failed load offers Try again and Close, and Escape works in every state.
- Dashboard: tab badges no longer push the tabs around while counts load, and each badge says what it counts. Only Specs, which waits on Drey, is filled.
- Dashboard: run times show a date when not from today, so "Last 24 hours: 0" no longer looks wrong next to yesterday's runs.

### Changed
- Dashboard: the summary sentence is the headline, with one "Review them" button for waiting specs. The plan percentage is the biggest number in the header. The open tab stays in the address after a reload, and the drawer opens with plain facts ("Took 43m 19s", cost in cents), with tokens, model and session folded under "Technical details".

## [2026-11-19]
### Changed
- Dashboard header and tabs in the orb look: a plain "Dashboard" title, sentence case, no scan lines, grid, corner brackets or numbered tabs. "Plan use" replaces "Subscription", the header counts say "Last 24 hours" because that is what they count, and phones hide them since the summary sentence covers it.

### Fixed
- Texts are wrapped as outside text, one line per message, and reading them is refused on a turn that already read a page or file. A staged text sends only when Drey's very next words are a yes (a "no, wait" or an unrelated question no longer releases it).

### Added
- `kill -USR1 <pid>` prints every thread's stack to the server log, to see what a busy server is doing without admin rights.

## [2026-11-18] (evening)
### Added
- Texts: Dreyvis reads your iMessages and sends one only after reading it back and hearing a yes on a later turn. The two-step rule lives in messages_bridge.py, not in the prompt, so a text it read can't send one.
- Dreyvis finds projects in ~/My Apps as well as the Desktop.
- The persona now tries Composio for calendar and mail before saying it isn't connected.

### Changed
- Connectors page matches the orb: #050508, one sky blue, system font, a field of blue dots.
- Connectors shows each app's real logo (initials only as a fallback), lists every app that needs signing in again at once instead of in a sideways row, and uses "Sign in again" everywhere for that one action.
- Connector errors are plain sentences that stay on the card or in the restart banner instead of a toast that vanished.
- Dashboard opens with one sentence on how today went, including specs waiting for review. On phones, run rows keep the project and reason, tabs wrap instead of hiding, and tapping a run scrolls to its details.
- Dashboard speaks plainly: each run shows its project name and a short reason ("Stopped because Dreyvis restarted mid-build") instead of the raw build prompt. "Needs attention" became "Needs you" and only lists failures from the last 3 days that weren't redone later.
- The voice and ears helpers show up as dreyvis-voice and dreyvis-ears in Activity Monitor.

### Fixed
- First spoken reply took 23s on average (80s worst) because the voice model loaded on the first sentence and often timed out. It now loads at startup; each sentence takes 0.3 to 0.9s.

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
- Connectors page redesign (Shelves layout on Aurora Glass, picked from a six-option board in docs/theme-board): a row per group (sign in again first, then connected, popular and Claude Code), unique app badges, its own remove dialog, and a pause button for the background motion.
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
