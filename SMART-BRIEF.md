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

## Ledger
- [ ] Phase 1 copy + install
- [ ] Phase 2 twin verified
- [ ] Phase 3 orb wired
- [ ] Phase 4 texting switched
- [ ] Phase 5 jobs + backup
- [ ] Phase 6 Tailscale orb
- [ ] Phase 7 text + morning report
