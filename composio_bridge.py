"""
composio_bridge.py — Dreyvis's door to 1,000+ apps (Gmail, Calendar, Drive, Slack,
GitHub, Notion...) through Drey's logged-in Composio CLI.

Two tools instead of hundreds, so they cost the brain little context:
  composio_search   find the right action and the inputs it needs (read-only)
  composio_execute  run one action (an ACTING tool: only on a turn the user drove)

Arguments go to the CLI as a list, never through a shell.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path

HOME = Path.home()
CLI = str(HOME / ".composio/composio")
TIMEOUT_SEC = 120
MAX_OUT = 6000
SLUG = re.compile(r"[A-Z0-9_]{3,120}")


async def _run(args: list[str]) -> tuple[int, str]:
    keep = ("HOME", "USER", "LOGNAME", "PATH", "LANG", "TMPDIR")
    env = {k: os.environ[k] for k in keep if k in os.environ}
    env["NO_COLOR"] = "1"
    proc = await asyncio.create_subprocess_exec(
        CLI, *args, env=env, stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), TIMEOUT_SEC)
    except asyncio.TimeoutError:
        proc.kill()
        return 124, "Composio timed out."
    text = re.sub(r"\x1b\[[0-9;]*m", "", out.decode(errors="replace"))
    return proc.returncode, text


def _schema(slug: str) -> str:
    p = HOME / ".composio/tool_definitions" / f"{slug}.json"
    try:
        d = json.loads(p.read_text())
    except (OSError, ValueError):
        return ""
    schema = d.get("inputSchema") or d.get("input_parameters") or {}
    props = {k: {"type": v.get("type"), "about": (v.get("description") or "")[:120]}
             for k, v in (schema.get("properties") or {}).items()}
    return json.dumps({"slug": slug, "required": schema.get("required", []), "inputs": props},
                      separators=(",", ":"))[:2500]


async def search(args: dict) -> str:
    query = str(args.get("query", "")).strip()
    if not query:
        return "No query given."
    if not Path(CLI).exists():
        return "Composio is not installed."
    code, out = await _run(["search", query, "--limit", "3"])
    try:
        d = json.loads(out)
    except ValueError:
        return f"Composio search failed: {out.strip()[:400]}"
    lines = []
    for r in d.get("results", []):
        lines.append(f"For '{r.get('use_case')}': best {r.get('primary_tool_slugs')}, also {r.get('related_tool_slugs')}")
        for slug in r.get("primary_tool_slugs", [])[:2]:
            lines.append(_schema(slug))
    lines.append(f"Connected apps: {d.get('connected_toolkits')}")
    return "\n".join(x for x in lines if x)[:MAX_OUT]


async def execute(args: dict) -> str:
    slug = str(args.get("slug", "")).strip().upper()
    if not SLUG.fullmatch(slug):
        return "That is not a Composio action name (like GMAIL_FETCH_EMAILS)."
    data = args.get("arguments") or {}
    if not isinstance(data, dict):
        return "arguments must be an object."
    code, out = await _run(["execute", slug, "-d", json.dumps(data)])
    return (out.strip() or f"Composio exited {code} with no output.")[:MAX_OUT]
