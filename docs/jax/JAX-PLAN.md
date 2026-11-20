# Jax: one assistant, living on the PC, reachable from anywhere

Written overnight on November 20, 2026. Nothing here is built past step 1 yet. It needs Drey's yes.

## My vote on the name

**Jax. Joint Agent Execution.** Keep your version, not ChatGPT's "Executive".

- "Execution" says what the code actually does: it runs Claude, Codex, Grok, GLM and DeepSeek jobs side by side.
- "Executive" promises judgment the software doesn't have yet.
- Use one name everywhere. Jax introduces himself as "Jax". The letters explain the name on the README; nobody says them out loud.

**The catch: Jax already exists.** Your Hermes agent on the VPS (jax.dreytools.com) is Jax. It already holds your iMessage history and your Omi recordings, and it runs your daily jobs. So this isn't a rename. It's a merge: Dreyvis becomes Jax's voice, his face (the orb) and his dashboard. That's good news, because you end up with one assistant instead of two.

## The setup I recommend

Think of a restaurant with three spaces:

- **The PC is the kitchen.** It does the heavy work: Jax's server, the voice, the ears, the builds, and local AI on the graphics card. It has 32 GB of memory, 876 GB free on X:, a 16 GB graphics card, and it's always on.
- **The VPS is the front door.** It's already reachable from anywhere and already has a private tunnel into the PC. Your phone or laptop opens jax.dreytools.com, signs in with Google, and the VPS passes the conversation through the tunnel to the PC. The PC never opens a door to the internet.
- **The Mac is the hands for Mac-only jobs.** iMessage, Mac apps and Mac notifications can't move to Windows. The PC asks the Mac to do those through the same private tunnel.

```
Phone / laptop, anywhere
  -> jax.dreytools.com (Google sign-in, Cloudflare Access)
  -> VPS front door
  -> private tunnel (already built and tested)
  -> PC: Jax server on 127.0.0.1 (voice, orb, dashboard, builds, local AI)
       -> Mac helper for iMessage and Mac apps
       -> Codex, Claude, Grok, GLM, DeepSeek, Hark
```

**The other option was Tailscale.** It's a private network app you'd install on the PC, the Mac and your phone. It's simple and safe. But the VPS route is already built, tested and running, and adding a second way in is one more thing to keep secure. Keep Tailscale as the backup if the VPS route ever feels slow for voice.

## Steps

1. **Prove the server runs on Windows. Done tonight.** Jax's server started on the PC in its own folder (`X:\Workspaces\jax-pc-spike`). It listens on 127.0.0.1 only, and the dashboard, connectors and specs pages answered 200. The brain started there too, on the PC's own Claude login. Four Windows bugs were found and fixed on the way, and the test server was stopped afterward.
2. **Make it a real PC service.** It starts when Windows starts, shows as "jax" in Task Manager, and you reach it from the Mac through the existing old-pc tunnel. Voice uses Kokoro and ears use Whisper on the PC (Whisper already tested there).
3. **Reachable from anywhere.** Add the jax.dreytools.com route on the VPS behind Google sign-in. Then test it from your phone on cell data.
4. **The merge.** Rename Dreyvis to Jax everywhere, persona included. Give both halves one shared memory. Hermes keeps iMessage, Omi and the scheduled jobs. The PC half takes everything you see and hear.
5. **The "Joint" part.** One menu of every brain you pay for, plus the free local models. Jax picks the right one per job and shows you which one it used. Dreyvis already calls Codex, Grok and DeepSeek, so this extends what exists.

## Blind spots

- **Windows 10 Home stopped getting free security updates in October 2025.** Extended updates (ESU) aren't turned on. An always-on assistant that can run commands shouldn't live on an unpatched system. Fix it before step 3: turn on consumer ESU, or move to Windows 11 if the PC qualifies (the Ryzen 5800X does).
- **The license.** Dreyvis is built on Ethan Rogers' JARVIS, which bans commercial use. If Jax is ever sold, used inside a paid product or open sourced under a normal license, that needs his permission or a rewrite of his parts.
- **Home power and internet.** If the PC or the router is off, Jax's kitchen is closed. The VPS can still answer, "Jax is offline," and keep the Hermes jobs running.
- **The VPS is tight.** Its disk is 93% full and its swap is full. The front door can't fall over, so clear it before step 3.
- **Mac-only features stay on the Mac.** These are texts, Mac app control, the Accessibility checks and screen recording. The PC version shows them as "needs the Mac", not as broken.

## What I need from you

1. Yes or no on the merge (Dreyvis becomes the voice of the existing Jax).
2. Yes on turning on Windows security updates (ESU) or moving to Windows 11.
3. Go on steps 2 and 3.
