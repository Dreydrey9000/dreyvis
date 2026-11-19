"""
connectors.py — the data behind the Connectors page.

Two kinds of connector:
  apps    Composio's 1,000 apps (Gmail, Slack, Notion...). Adding one asks
          Composio for a sign-in link; Drey clicks Authorize there.
  custom  Any remote MCP server by URL (plus an optional key), written into
          connections.json — the same file the brain's MCP config is built from.

Secrets never leave this module: the page sees names, hosts and statuses only.
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from urllib.parse import urlsplit

import composio_bridge
import data_paths

APP_SLUG = re.compile(r"[a-z0-9_]{2,60}")
# Same rule server.py applies to connections.json names (`_SERVER_NAME_RE`).
CUSTOM_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
CATALOG_MAX_AGE = 24 * 3600
STATUS_MAX_AGE = 15

# The short list shown first. Every slug was checked against Composio's catalog
# on 2026-11-18; anything else is one search away on the page.
RECOMMENDED = [
    ("gmail", "Read, sort and draft email"),
    ("googlecalendar", "Your schedule and invites"),
    ("googledrive", "Find and share files"),
    ("googledocs", "Read and write docs"),
    ("googlesheets", "Read and update sheets"),
    ("googlemeet", "Meetings and recordings"),
    ("slack", "Read channels, send messages"),
    ("notion", "Pages, notes and databases"),
    ("github", "Repos, issues and pull requests"),
    ("linear", "Tickets and projects"),
    ("stripe", "Payments, customers and invoices"),
    ("calendly", "Bookings"),
    ("cal", "Cal.com bookings"),
    ("zoom", "Meetings"),
    ("airtable", "Bases and records"),
    ("hubspot", "Contacts and deals"),
    ("youtube", "Your channel and videos"),
    ("instagram", "Posts and comments"),
    ("linkedin", "Posts and profile"),
    ("twitter", "Posts on X"),
    ("facebook", "Pages and posts"),
    ("reddit", "Posts and comments"),
    ("discord", "Servers and messages"),
    ("whatsapp", "WhatsApp Business messages"),
    ("dropbox", "Files"),
    ("one_drive", "OneDrive files"),
    ("outlook", "Outlook mail and calendar"),
    ("figma", "Design files"),
    ("canva", "Designs"),
    ("asana", "Tasks"),
    ("clickup", "Tasks"),
    ("trello", "Boards"),
    ("todoist", "To-dos"),
    ("jira", "Tickets"),
    ("shopify", "Store, orders and products"),
    ("supabase", "Databases"),
    ("elevenlabs", "Voices"),
    ("heygen", "AI video"),
    ("firecrawl", "Read any web page"),
    ("perplexityai", "Web answers"),
]

_status_cache: tuple[float, dict] = (0.0, {})


# ── Composio apps ────────────────────────────────────────────────────────────

def _catalog_path() -> Path:
    return data_paths.connections_path().parent / "composio-catalog.json"


async def catalog() -> list[dict]:
    """Every Composio app as {slug, name, about, tools}. Refreshed once a day;
    a stale copy beats an empty page when Composio is slow."""
    path = _catalog_path()
    try:
        if time.time() - path.stat().st_mtime < CATALOG_MAX_AGE:
            return json.loads(path.read_text())
    except (OSError, ValueError):
        pass
    code, out = await composio_bridge._run(["dev", "toolkits", "list", "--limit", "1000"])
    try:
        rows = json.loads(out)
        apps = [{"slug": r["slug"], "name": r["name"],
                 "about": (r.get("description") or "")[:140],
                 "tools": r.get("tools_count") or 0}
                for r in rows if APP_SLUG.fullmatch(r.get("slug") or "")]
    except (ValueError, KeyError, TypeError):
        apps = []
    if apps:
        path.write_text(json.dumps(apps))
        return apps
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return []


async def statuses(fresh: bool = False) -> dict[str, str]:
    """{slug: "connected" | "waiting" | "expired"}. ACTIVE wins, then a sign-in
    that's still open (INITIALIZING), then EXPIRED/REVOKED."""
    global _status_cache
    if not fresh and time.time() - _status_cache[0] < STATUS_MAX_AGE:
        return _status_cache[1]
    code, out = await composio_bridge._run(["connections", "list"])
    try:
        rows = json.loads(out)
    except ValueError:
        return _status_cache[1]
    result = {}
    for slug, accounts in rows.items():
        states = {a.get("status") for a in accounts if isinstance(a, dict)}
        if "ACTIVE" in states:
            result[slug] = "connected"
        elif "INITIALIZING" in states:
            result[slug] = "waiting"
        elif states:
            result[slug] = "expired"
    _status_cache = (time.time(), result)
    return result


async def link(slug: str) -> dict:
    """Ask Composio for a sign-in link. Returns {url} or {error}."""
    slug = (slug or "").strip().lower()
    if not APP_SLUG.fullmatch(slug):
        return {"error": "That is not an app name."}
    if slug not in {a["slug"] for a in await catalog()}:
        return {"error": f"Composio has no app called {slug}."}
    code, out = await composio_bridge._run(["link", slug, "--no-wait", "--no-browser"])
    try:
        url = json.loads(out).get("redirect_url") or ""
    except ValueError:
        url = ""
    if not url.startswith("https://"):
        return {"error": f"Composio did not give a sign-in link: {out.strip()[:200]}"}
    return {"url": url}


# ── Custom connectors (remote MCP servers) ──────────────────────────────────

def _read_file() -> dict:
    try:
        body = json.loads(data_paths.connections_path().read_text())
    except FileNotFoundError:
        return {"mcpServers": {}}
    if not isinstance(body, dict) or not isinstance(body.get("mcpServers"), dict):
        raise ValueError("connections.json is damaged, so I won't overwrite it.")
    return body


def _write_file(body: dict) -> None:
    path = data_paths.connections_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    # Created 0600 so the key inside is never readable by anyone else, even briefly.
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(body, f, indent=2)
    os.replace(tmp, path)


def custom_list() -> list[dict]:
    """Name, where it points and whether a key is saved. Never the key itself."""
    try:
        servers = _read_file()["mcpServers"]
    except ValueError:
        return []
    out = []
    for name, e in servers.items():
        if not isinstance(e, dict):
            continue
        if e.get("url"):
            u = urlsplit(e["url"])
            where = f"{u.scheme}://{u.netloc}{u.path}"      # no query string: it can hold a key
        else:
            where = "local program: " + Path(str(e.get("command", ""))).name
        out.append({"name": name, "where": where,
                    "has_key": bool(e.get("headers") or e.get("env"))})
    return out


def custom_add(name: str, url: str, key: str = "") -> str | None:
    """Add or replace a remote MCP server. Returns an error sentence, or None."""
    name, url, key = (name or "").strip(), (url or "").strip(), (key or "").strip()
    if not CUSTOM_NAME.fullmatch(name) or "__" in name or name == "jarvis":
        return "Pick a short name: letters, numbers, dots and dashes."
    u = urlsplit(url)
    local = u.hostname in ("127.0.0.1", "localhost", "::1")
    if not (u.scheme == "https" or (u.scheme == "http" and local)) or not u.netloc:
        return "The address must start with https:// (http:// only for this Mac)."
    if any(c in key for c in "\r\n"):
        return "The key can't contain line breaks."
    try:
        body = _read_file()
    except ValueError as e:
        return str(e)
    entry: dict = {"type": "http", "url": url}
    if key:
        entry["headers"] = {"Authorization": key if " " in key else f"Bearer {key}"}
    body["mcpServers"][name] = entry
    _write_file(body)
    return None


def _claude_code_servers() -> dict:
    """MCP servers from Claude Code's own config: user scope first, then any
    project scope. Read fresh each time so new ones show up."""
    try:
        cfg = json.loads((Path.home() / ".claude.json").read_text())
    except (OSError, ValueError):
        return {}
    found = {}
    for proj in (cfg.get("projects") or {}).values():
        for n, e in ((proj or {}).get("mcpServers") or {}).items():
            found.setdefault(n, e)
    found.update(cfg.get("mcpServers") or {})          # user scope wins
    return {n: e for n, e in found.items()
            if isinstance(e, dict) and (e.get("url") or e.get("command"))}


def claude_code_list() -> list[dict]:
    """What Claude Code has, for the import list. Names and hosts only."""
    try:
        mine = set(_read_file()["mcpServers"])
    except ValueError:
        mine = set()
    out = []
    for name, e in sorted(_claude_code_servers().items(), key=lambda kv: kv[0].lower()):
        if e.get("url"):
            u = urlsplit(e["url"])
            where = u.netloc
            # A web server with no saved key signs in through Claude Code; that
            # sign-in may not carry over to Dreyvis.
            note = "" if e.get("headers") else "may ask you to sign in"
        else:
            where, note = "runs on this Mac: " + Path(str(e["command"])).name, ""
        out.append({"name": name, "where": where, "note": note, "added": name in mine})
    return out


def import_from_claude_code(name: str) -> str | None:
    """Copy one server, exactly as Claude Code runs it, into connections.json."""
    entry = _claude_code_servers().get(name)
    if entry is None:
        return f"Claude Code has no connector called {name}."
    if not CUSTOM_NAME.fullmatch(name) or "__" in name or name == "jarvis":
        return f"{name} isn't a name Dreyvis can use."
    try:
        body = _read_file()
    except ValueError as e:
        return str(e)
    body["mcpServers"][name] = entry
    _write_file(body)
    return None


def custom_remove(name: str) -> str | None:
    try:
        body = _read_file()
    except ValueError as e:
        return str(e)
    if name not in body["mcpServers"]:
        return f"There is no connector called {name}."
    del body["mcpServers"][name]
    _write_file(body)
    return None


if __name__ == "__main__":
    # ponytail: one self-check for the parts that guard the file and the key.
    import tempfile
    d = Path(tempfile.mkdtemp())
    data_paths.connections_path = lambda: d / "connections.json"
    assert custom_add("bad name", "https://x.com/mcp") is not None
    assert custom_add("jarvis", "https://x.com/mcp") is not None
    assert custom_add("x", "http://evil.com/mcp") is not None
    assert custom_add("x", "https://x.com/mcp?token=s3cret", "abc") is None
    assert (d / "connections.json").stat().st_mode & 0o777 == 0o600
    row = custom_list()[0]
    assert row == {"name": "x", "where": "https://x.com/mcp", "has_key": True}, row
    assert "s3cret" not in json.dumps(custom_list())
    assert json.loads((d / "connections.json").read_text())["mcpServers"]["x"]["headers"]["Authorization"] == "Bearer abc"
    assert custom_remove("x") is None and custom_list() == []
    print("connectors self-check: ok")
