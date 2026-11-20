# Jax: one assistant, living on the PC, reachable from anywhere

Written overnight on November 20, 2026. Updated the same afternoon.

**Update, November 20 afternoon:** Drey decided to keep the two assistants separate (no merge). This one is **Jax Desktop**, living on the PC. The Hermes agent on the VPS stays its own thing. Step 2 is built and tested; steps 3 and 4 below are what's left.

## My vote on the name

**Jax. Joint Agent Execution.** Keep your version, not ChatGPT's "Executive".

- "Execution" says what the code actually does: it runs Claude, Codex, Grok, GLM and DeepSeek jobs side by side.
- "Executive" promises judgment the software doesn't have yet.
- Use one name everywhere. Jax introduces himself as "Jax". The letters explain the name on the README; nobody says them out loud.

**The catch: a Jax already exists.** Your Hermes agent on the VPS (jax.dreytools.com) is also called Jax. Drey chose to keep them separate, so where both appear this one is labelled **Jax Desktop** and the other **Jax (Hermes)**. Jax Desktop needs its own web address later, not jax.dreytools.com.

## The setup I recommend

Think of a restaurant with three spaces:

- **The PC is the kitchen.** It does the heavy work: Jax's server, the voice, the ears, the builds, and local AI on the graphics card. It has 32 GB of memory, 876 GB free on X:, a 16 GB graphics card, and it's always on.
- **The VPS is the front door.** It's already reachable from anywhere and already has a private tunnel into the PC. Your phone or laptop opens Jax Desktop's own address (to be picked), signs in with Google, and the VPS passes the conversation through the tunnel to the PC. The PC never opens a door to the internet.
- **The Mac is the hands for Mac-only jobs.** iMessage, Mac apps and Mac notifications can't move to Windows. The PC asks the Mac to do those through the same private tunnel.

```
Phone / laptop, anywhere
  -> Jax Desktop's own address (Google sign-in, Cloudflare Access)
  -> VPS front door
  -> private tunnel (already built and tested)
  -> PC: Jax server on 127.0.0.1 (voice, orb, dashboard, builds, local AI)
       -> Mac helper for iMessage and Mac apps
       -> Codex, Claude, Grok, GLM, DeepSeek, Hark
```

**The other option was Tailscale.** It's a private network app you'd install on the PC, the Mac and your phone. It's simple and safe. But the VPS route is already built, tested and running, and adding a second way in is one more thing to keep secure. Keep Tailscale as the backup if the VPS route ever feels slow for voice.

## Steps

1. **Prove the server runs on Windows. Done tonight.** Jax's server started on the PC in its own folder (`X:\Workspaces\jax-pc-spike`). It listens on 127.0.0.1 only, and the dashboard, connectors and specs pages answered 200. The brain started there too, on the PC's own Claude login. Four Windows bugs were found and fixed on the way, and the test server was stopped afterward.
2. **Make it a real PC service. Done November 20.**
   - Code lives at `X:\Workspaces\jax`, data at `X:\Workspaces\jax-data`. Settings in `.env` there hold no keys; the brain uses the PC's own Claude login.
   - A Windows task named **Jax** runs `jax_service.py` at sign-in and re-checks every 5 minutes. The service starts the server on 127.0.0.1:8340 and restarts it if it stops. Task Manager shows `jax.exe` (the service) and `jax-server.exe` (the server).
   - **Turn it off:** create the file `X:\Workspaces\jax\logs\JAX_OFF`. Delete it to turn back on. Logs are in the same folder.
   - **Voice:** Kokoro, the same pinned versions as the Mac, in `.venv-voice`. It loads in about 17 seconds and speaks a sentence in about 1 second (the Mac took 3 minutes to load).
   - **Ears:** whisper.cpp with the base.en model, about 1 second per phrase. The large-v3-turbo model is there too but takes 8 seconds per clip on this processor, too slow to talk to. Jax has its own copy in `jax-data\whisper` because the shared `X:\AI` folder is locked to admin and service accounts on purpose.
   - **From the Mac:** run `jax-pc` (or `jax-pc open`). It opens a private SSH tunnel, home network first and the VPS relay otherwise, so Jax Desktop answers at `http://127.0.0.1:8341`. `jax-pc status` and `jax-pc stop` do what they say.
   - **Limit:** auto-login is off on the PC, so after a reboot Jax starts when someone signs in to Windows.
3. **Reachable from anywhere.** Give Jax Desktop its own address on the VPS behind Google sign-in (not jax.dreytools.com, which is Hermes). Then test it from your phone on cell data.
4. **The "Joint" part.** One menu of every brain you pay for, plus the free local models. Jax picks the right one per job and shows you which one it used. Dreyvis already calls Codex, Grok and DeepSeek, so this extends what exists.

## Blind spots

- **Windows 10 Home stopped getting free security updates in October 2025.** Extended updates (ESU) aren't turned on. An always-on assistant that can run commands shouldn't live on an unpatched system. Fix it before step 3: turn on consumer ESU, or move to Windows 11 if the PC qualifies (the Ryzen 5800X does).
- **The license.** Dreyvis is built on Ethan Rogers' JARVIS, which bans commercial use. If Jax is ever sold, used inside a paid product or open sourced under a normal license, that needs his permission or a rewrite of his parts.
- **Home power and internet.** If the PC or the router is off, Jax's kitchen is closed. The VPS can still answer, "Jax is offline," and keep the Hermes jobs running.
- **The VPS is tight.** Its disk is 93% full and its swap is full. The front door can't fall over, so clear it before step 3.
- **Mac-only features stay on the Mac.** These are texts, Mac app control, the Accessibility checks and screen recording. The PC version shows them as "needs the Mac", not as broken.

## What I need from you

1. Yes on turning on Windows security updates (ESU) or moving to Windows 11, before step 3.
2. A name for Jax Desktop's web address, then go on step 3.
3. Optional: turn on auto-login on the PC if Jax should come back on its own after a reboot.
