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

## VPS LIFT DONE 2026-11-21 16:20 ET
Everything that ran on the VPS now runs in the WSL distro `vps` on the closet PC, Jax included. The VPS is stopped and disabled, nothing deleted. Full report: `~/My Apps/_reports/VPS-LIFT-REPORT-20261121.md`.
- Verified after a full clone restart: 63 containers, 45 background apps, 15 tunnels, 17 runners, 80 Jax jobs, 65 of 67 web addresses same as the baseline, Jax text delivered.
- Open: `hermes.dreythomas.com` and `api.gitnexus.dreythomas.com` DNS, Multica login, PC auto-login, PC SSH allow-list for Tailscale, off-PC backup, SSH door into the clone for cancel day.
- Do not cancel the VPS before a quiet week and a working backup.

## FULL VPS LIFT (started 2026-11-21 11:50 ET) - Drey: "move everything off so I can get rid of the VPS"
Method: make the PC's Ubuntu look like the VPS, then move the public addresses. Same user name, same uid (hermes = 1000 on both now), same paths, same Docker version (29.1.3).

Done so far
- Docker installed in WSL. WSL memory raised to 26 GB (`.wslconfig`, backup `.wslconfig.bak-20261121`). Restart test passed: Jax, link and texting came back alone.
- Jax to Mac link rebuilt: `jax-mac-link.socket` forwards 127.0.0.1:22277 to the Mac over Tailscale (100.85.230.27:22). Tested.
- Bulk copy running as root in WSL: `/root/lift/lift1.sh`, log `/root/lift/lift1.log`. Copies /var/lib/docker (105 GB), /opt, /home/ghrunner, the rest of /home/hermes (never overwrites newer PC files, never touches the live Jax profile), and VPS config into `/root/lift/vps-etc` and `/home/hermes/vps-reference/systemd`. Read-only key `pc-lift-readonly` in the VPS root authorized_keys: REMOVE when the lift is done.

Inventory to move (VPS)
- 21 compose projects + 10 loose containers (73 containers, 41 volumes).
- About 45 systemd user services under hermes (dreysfield, dreyos, drechat, livekit-jax, jax-voice, codex-bridge, box counts, downloaders...). Unit files: `vps-reference/systemd`.
- 17 GitHub Actions runners (/home/ghrunner + system units).
- 11 cloudflared tunnels, about 70 hostnames (list: `~/.cloudflared/config-*.yml`). Client-facing: boxcounts.viraleditz.app, twitch.viraleditz.app, pass.dreytools.com (vault).
- Crons: root (disk alert, 1bb smoke, vault backup), hermes (notion sync, imsg watchdog, sessions watchdog, x-ray pull, design backup, disk hygiene).

METHOD CHANGE (12:45 ET): import the VPS's whole OS as its own WSL distro named `vps` (Ubuntu 22.04, same packages, units, crons, Python 3.10). Reason: the PC's Ubuntu is 26.04, so system packages and venvs built on 22.04 would break. All distros share one network, so ports behave like one machine.
- Rehearsal passed in the Ubuntu distro: dockerd with copied data shows 73 containers, 41 volumes; `trek` started and returned 200. All restart policies there were set to "no" so nothing double-runs.
- `/root/lift/base.sh` copies the VPS root filesystem (minus home/hermes, docker, opt, ghrunner) into `/root/lift/vpsroot`.
- Then: neutralize it before first boot (wsl.conf systemd=true, clear fstab, remove netplan, mask cloud-init, ufw, fail2ban, ssh, droplet-agent, networkd-wait-online, docker; remove linger; hold all custom units), tar to `X:\WSL\vps-base.tar`, `wsl --import vps X:\WSL\vps ...`.
- Fill it locally from the Ubuntu distro's copies via a `/mnt/wsl` bind mount: /var/lib/docker, /opt, /home/ghrunner, /home/hermes.
- NEVER let apps run on both machines at once: Postiz and Warmbly would double-post and double-send.
- Big-bang cutover: stop everything on the VPS (docker, hermes user services, tunnels, runners), final delta sync, move Jax's live profile from the Ubuntu distro into `vps`, start everything in `vps`, curl all ~70 hostnames. Rollback: start it all on the VPS again.
- Needs a Windows keepalive task for the `vps` distro like "Drey WSL Firecrawl Keepalive".

Order after the copy lands
1. Start Docker on the PC with the copied data. Containers come up on the same ports. Check each.
2. Enable the hermes user services in batches from vps-reference, check each port answers.
3. For each tunnel: stop it on the VPS, start it on the PC, curl every hostname. Vault and VE client tools last, with a fresh final data sync first.
4. Final sync pass with VPS Docker stopped (short downtime), then VPS services stay off.
5. Runners, crons, the 11 paused Jax jobs (they watch "the VPS", re-aim them at the PC).
6. Backup of the PC to Backblaze B2. Remove lift keys. Then the VPS can be cancelled after a quiet week.

## SWITCHED 2026-11-21 11:30 ET
Jax runs on the closet PC. Text test answered from DESKTOP-UD6M5TB, 4 minutes of downtime. Work folder and apps (99 GB) copied first. 11 VPS-keeper jobs paused, 69 active. VPS apps reach Jax through a reverse link (jax-brain-link). Rollback: stop and disable the PC unit, rename `hermes-gateway-jax.service.moved-to-pc-20261121` back on the VPS, enable it and the four jax timers.

Still open:
1. Push pages built on the PC back to the VPS (DreyOS, jax.dreytools.com dashboards), or move those sites.
2. Nightly backup of PC Jax off the PC.
3. Rebuild the 11 paused jobs as plain VPS timers.
4. Auto-login on the PC (Drey's clicks).
5. Fix whatever the first day of job runs shows.

## Where it stands (2026-11-21 morning)
- Step 1 done: twin built on the PC and verified. Parked (service disabled). Files in `/home/hermes` inside the PC's Ubuntu.
- Step 2 done differently: the orb uses the REAL Jax on the VPS through `jax-brain-link.service` (ssh -L 8642). One Jax for text and voice today.
- Step 3 HELD. Blocker below.
- Step 6 done: `jax-home-copy.timer` pulls a checked copy of state.db and the profile into `~/jax-home-copy` every night.

## Why the switch is blocked
- 80 active jobs. 32 run scripts and 24 prompts name VPS paths. They read `/home/hermes/workspace` (43 GB) and talk to services that live on the VPS (DreyOS, OpenBot, Utopia, Multica, the dashboards behind jax.dreytools.com).
- The scheduler lives inside the gateway, so texting and jobs move together or not at all.
- Hermes' ssh terminal mode is not the answer: its file sync timed out and it writes into the remote home, which is the live profile.
- VPS services call Jax at VPS localhost:8642 (jax-avatar, multica-llm-forward, hermes3d, openbot, the jax-briefs tunnel).

## What has to move before the switch
1. `/home/hermes/workspace` (43 GB; copies at about 2 GB a minute).
2. Each VPS service a job talks to, or a forward to it.
3. The public pages: move the jax.dreytools.com tunnel to the PC or push the built pages back.
4. Per-job review of the 80, with Drey awake, in daytime.
5. Then the switch itself, using the guards below.

## Switch guards (from the skeptic pass)
- Strip Photon, Telegram, Discord from the twin's `.env` AND `auth.json` until the moment of the switch.
- On the VPS: stop and mask the gateway, and stop `jax-cron-watchdog.timer` (it texts Drey when the heartbeat is missing).
- Final copy after stop: whole profile plus a fresh database backup; delete WAL and SHM on the PC first.
- Run the PC gateway with TZ=UTC through a systemd drop-in. Hermes rewrites its own unit file, and the job times are in UTC.
- The unit must be named `hermes-gateway-jax.service` or Hermes refuses to start a profile gateway.
- Never copy `~/.config/systemd` into place: it carries the VPS auto-start list.

## Decisions so far
- Hermes runs in the PC's Ubuntu, not native Windows (it is Linux software).
- Twin first, switch second. Texting never depends on an untested box.

## Fog
- Do voice chats and text chats share one thread, or only memory?
- Hermes on Python 3.14: untested.
- The Mac job that syncs iMessage history to Jax points at the VPS today.
- jax.dreytools.com and the Jax web pages are served from the VPS.

## Needs Drey
- Enable Serve in Tailscale (one click) so the phone can use the orb's mic over https.
- The auto-login clicks. Now required, not optional: the PC's Ubuntu only starts when the PC is signed in.
- A go at step 3.

## Out of scope: retiring the VPS
Jax is one tenant. The VPS also runs about 60 containers (OpenBot, Vaultwarden, Utopia, Dreysfield and more), 17 GitHub site builders, a dozen public tunnels, and the relay that lets the Mac reach this PC from outside the house. Each needs its own move before the VPS can be cancelled.

## Risks
- PC power or internet goes out = Jax is off iMessage until it is back. The VPS does not have that problem.
- Windows 10 is out of support.
