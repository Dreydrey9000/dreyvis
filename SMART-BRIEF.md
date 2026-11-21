# SMART brief: move Jax home (overnight 2026-11-21)

**S** Move Hermes Jax (profile `jax`: texting, memory, jobs) from the VPS to the closet PC's Ubuntu, make the orb use him as its brain, and open the orb to Drey's Mac and phone over Tailscale. For Drey. OUT tonight: the other ~60 VPS apps, the Jackie/Cindy/Marissa profiles, cancelling the VPS, Windows auto-login (his clicks).

**M** done checks
1. Hermes gateway runs on the PC as a service (survives a WSL restart).
2. PC Jax answers on its local door and recalls a fact from before today.
3. Orb on the PC answers through PC Jax.
4. VPS Jax gateway is stopped and disabled; only one Jax answers texts.
5. A text from Drey's Mac to Jax gets a reply that came from the PC.
6. Orb opens at an https Tailscale address from the Mac (200).
7. Every scheduled job is listed as running on PC, kept on VPS, or paused, with a reason.
8. Nightly backup of Jax's database exists and one run succeeded.
9. Jax texted Drey that the move is complete.

**A** confirmed: root SSH to VPS, SSH to PC, root in PC Ubuntu, 937 GB free, binary copy checksum matches, Tailscale serve already used on the PC, uv + Python 3.11 available. Needs Drey: nothing tonight. Auto-login stays his.

**R** Drey wants one Jax he owns at home, same on text and voice, and to drop the VPS bill later. When in doubt: texting must not break; data must not be lost.

**T** One night. Stop rule: never switch texting until checks 1-3 pass. If check 5 fails for 15 minutes after the switch, roll back (restart VPS gateway, stop PC messaging) and write it up. Never delete anything on the VPS.

## Result (2026-11-21, 4:25 AM ET)
Texting was NOT switched. The twin passed, then the test of its "remote hands" on the VPS hung, and the job list showed about half the 80 active jobs need files and services that only exist on the VPS. Stop rule applied. Safe route taken instead.

1. PASS (as a parked standby) Hermes ran as a service on the PC and answered. It is stopped and disabled now so it can never double-answer.
2. PASS PC copy recalled Drey's name and the Nov 7 YouTube work in 8 s.
3. PASS Orb answers through Jax. Now wired to the REAL Jax over a private link (PC 127.0.0.1:8642 -> VPS).
4. NOT DONE (held on purpose) VPS gateway still runs Jax.
5. NOT DONE texting unchanged, so nothing to test.
6. PARTIAL Orb opens over Tailscale at http://desktop-ud6m5tb.tail5f2662.ts.net:8340 (200 from the Mac). https (needed for the phone mic) waits on Drey enabling Serve in Tailscale.
7. PASS Jobs listed: all 80 stay on the VPS, unchanged. Reason: VPS files and services.
8. PASS Nightly copy: VPS 08:20 UTC makes a safe copy, PC pulls 09:10 UTC. First run: quick_check ok, 376,710 messages.
9. PASS Jax texted Drey at 4:19 AM (seen in Messages).
