# Jax: one system on the closet PC

Started 2026-11-21. Drey's call: merge Hermes Jax (VPS, the one on iMessage) with Jax Desktop (PC, voice orb), run it all on the PC, and retire the VPS later. This replaces the 2026-11-20 "keep them separate" call.

## Destination
One Jax on the closet PC. Texting, memory, scheduled jobs, voice and the orb all come from the same brain. Data lives at home. The VPS is no longer needed for Jax.

## What exists today (checked 2026-11-21)
- VPS `Drey-vps`: Hermes agent 0.21.5, profile `jax`, gateway running, chat door on 127.0.0.1:8642 (key protected). iMessage goes through Photon (a cloud service, outbound only), plus Telegram and Discord.
- Jax profile is 9.3 GB: state.db 3.8 GB, snapshots 2.1 GB, backups 2.1 GB, the rest small. 95 scheduled jobs. About 60 secrets in `.env`.
- PC: Windows 10, Ryzen 7 5800X, 32 GB RAM. Ubuntu 26.04 runs inside it (WSL2, systemd on, 937 GB free, Python 3.14, 15 GB RAM). Hermes is Linux software, so it runs there.
- PC Jax Desktop: `X:\Workspaces\jax`, Windows task "Jax", orb on 127.0.0.1:8340.

## Route
1. **Twin on the PC, messaging off.** Install Hermes in the PC's Ubuntu. Copy the Jax profile (safe database copy, skip old backups). Start it with Photon, Telegram and Discord OFF so two Jaxes never answer the same text. Check: it answers on the PC and recalls something from Drey's history.
2. **Orb uses the twin.** Point Jax Desktop's brain at the local Hermes door. Check: ask the orb something only iMessage Jax knows.
3. **Switch texting over.** Stop the VPS gateway, final database copy, turn messaging on at the PC. A few minutes of downtime. Undo = start the VPS gateway again. Needs Drey's go at that moment.
4. **Sort the 95 jobs.** Keep the personal ones (briefs, email watch, diary). Drop or re-point the ones that babysit the VPS itself.
5. **One repo.** Fold the orb code and the Jax setup into one `jax` repo, no secrets in it.
6. **Backups.** Nightly encrypted copy of state.db off the PC (Backblaze B2).

## Decisions so far
- Hermes runs in the PC's Ubuntu, not native Windows (it is Linux software).
- Twin first, switch second. Texting never depends on an untested box.

## Fog
- Do voice chats and text chats share one thread, or only memory?
- Hermes on Python 3.14: untested.
- The Mac job that syncs iMessage history to Jax points at the VPS today.
- jax.dreytools.com and the Jax web pages are served from the VPS.

## Needs Drey
- A password on the PC account before step 1 (every Jax key will sit on that disk).
- The auto-login clicks. Now required, not optional: the PC's Ubuntu only starts when the PC is signed in.
- A go at step 3.

## Out of scope: retiring the VPS
Jax is one tenant. The VPS also runs about 60 containers (OpenBot, Vaultwarden, Utopia, Dreysfield and more), 17 GitHub site builders, a dozen public tunnels, and the relay that lets the Mac reach this PC from outside the house. Each needs its own move before the VPS can be cancelled.

## Risks
- PC power or internet goes out = Jax is off iMessage until it is back. The VPS does not have that problem.
- Windows 10 is out of support.
