# Theme decision

- Project and purpose: Dreyvis Connectors page (`/connectors`) and the nav buttons on the orb. Connect apps and custom MCP servers to Dreyvis.
- Audience and main action: Drey (and friends he shares Dreyvis with). Main action: connect an app.
- User-selected direction and date: "A cross between 3 and 6" from `docs/theme-board/connectors-board.html`, 2026-11-18. Later that day Drey asked for it to match the orb look, so the colours and font below replace the aurora palette; the Shelves layout stays.
- Primary structure: 6, Shelves. Rows by group (Waiting for you, Connected, Needs sign-in again, Popular, From Claude Code, Search), scrolled sideways.
- Secondary accents: the orb look. Near-black background with a slow field of sky-blue dots, like the orb, and dark tiles with one blue accent.
- Palette and contrast targets: background #050508, one accent, sky blue rgb(14,165,233), coral only for "sign in again". Body text at least 4.5:1.
- Typography: the system font, 400 and 600 only. Body 16px, headings 24/32/40. Small letter-spaced DREYVIS label, as on the orb.
- Image and motion treatment: no logos. Each tile uses its app's colour and initial. Motion comes from Drey Motion 12 (@zeeuiux), played once: Spotlight Entrance for the title, Proof in Motion for the connected count (real data only), and Success Bloom only after the backend confirms a connection. The dots drift slowly and pause when hidden. Everything holds still under prefers-reduced-motion.
- References: Netflix and App Store shelves for the rows. Linear integrations and macOS glass for the cards.
- Existing content/functionality to preserve: adding and reconnecting Composio apps with their waiting state. Also search over every app, the custom connector form with remove, and the restart-brain prompt.
- Verification plan: phone (375) and desktop widths, keyboard through every row, reduced motion, both inspectors and the cognitive-load check.
- The dashboard now shares the orb look too (2026-11-19), as a layer in frontend/src/dashboard/theme/orb.css over its original theme.

Approval applies to this project, not automatically to future websites.
