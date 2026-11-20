# SMART brief: Dreyvis to Jax, overnight 2026-11-20

Drey went to sleep, so every gap below was filled with the safest choice (listed in the morning report).

## S, Specific
For Drey: (1) the dashboard fixes re-checked by both inspectors, (2) a read-only recon of the closet PC,
(3) a plan, as a visual page plus a diagram, for making Jax one assistant that lives on the PC and is reachable
from anywhere, (4) a name vote, (5) a proof that the assistant's server can start on the PC, private to the PC.
OUT tonight: renaming the live Mac app, exposing any PC port to the internet, merging with the VPS Jax,
touching Hermes on the VPS, buying anything, sending messages, interrupting other agents' PC work.

## M, Measurable (each reported PASS or FAIL)
1. ui-inspector and ux-inspector both ran on http://127.0.0.1:8340/dashboard; every FAIL is fixed or listed.
2. Frontend build exits 0 and the cognitive-load count stays at or under 20.
3. `old-pc hostname` returns the PC's name; the recon file lists Windows version, Python, Git, Node, Tailscale.
4. `docs/jax/JAX-PLAN.html` and `docs/jax/JAX-PLAN.md` exist; copy gate passes on the .md.
5. `docs/diagrams/jax-architecture` diagram exists (source plus rendered image).
6. On the PC, the server answers 200 on 127.0.0.1 only, or the exact blocker is recorded.
7. Changes committed and pushed; CHANGELOG updated; morning report opened.

## A, Achievable
Present: old-pc helper and its keys (Mac), the VPS route, repo, inspectors, copy gate. Needs Drey: anything
needing his Windows password, app sign-ins, the merge and rename decisions, any public exposure.

## R, Relevant
Drey wants one assistant (Jax) that pulls Codex, Claude, Grok, GLM, DeepSeek and the rest together and works
from anywhere. Judgment calls favor: safe remote access, nothing public, nothing that breaks today's Dreyvis.

## T, Time-bound
One night. Checkpoint after each M item. Stop rule: if the PC asks for a password, a UAC prompt, or another
agent is using the desktop, stop that step and note it. Never guess credentials.
