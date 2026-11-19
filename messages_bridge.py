"""
messages_bridge.py — Dreyvis reads and sends iMessages on this Mac.

read_texts   recent texts, optionally with one person (read-only; a text is
             somebody else's words, so server.py marks the turn untrusted).
send_text    two steps, enforced here, not left to the brain's manners:
             1. the first call only STAGES the text and asks Dreyvis to read
                it back;
             2. the same call again sends it, and only after Drey has spoken
                since it was staged (his yes is a new turn). Nothing sends on
                the turn that proposed it.

Needs two macOS permissions for whatever runs the Dreyvis server: Full Disk
Access (to read ~/Library/Messages/chat.db and Contacts) and Automation for
Messages (asked for the first time a text is sent).
"""
from __future__ import annotations

import asyncio
import glob
import re
import sqlite3
import time
from pathlib import Path

HOME = Path.home()
CHAT_DB = HOME / "Library/Messages/chat.db"
APPLE_EPOCH = 978307200            # 2001-01-01 in Unix time
MAX_TEXT = 1000
# Who a text can go to: a phone number or an email, never something that starts with "-".
_HANDLE = re.compile(r"\+?[0-9][0-9 ().\-]{5,19}|[^@\s\-][^@\s]*@[^@\s]+\.[^@\s]+")
NO_ACCESS = ("I can't open your Messages yet, sir: macOS hasn't given me Full Disk "
             "Access. It's one switch in System Settings, under Privacy and Security.")

_heard = 0                         # how many times Drey has spoken; server.py bumps it
_staged: dict | None = None        # {"to", "handle", "message", "at": _heard when staged}


def heard() -> None:
    """Called by server.py each time Drey says something."""
    global _heard
    _heard += 1


def _digits(s: str) -> str:
    return re.sub(r"\D", "", s)[-10:]


def _contacts() -> list[tuple[str, str]]:
    """(name, phone-or-email) from every local Contacts database."""
    out = []
    for db in glob.glob(str(HOME / "Library/Application Support/AddressBook/Sources/*/AddressBook-v22.abcddb")):
        try:
            con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            rows = con.execute(
                "SELECT TRIM(COALESCE(r.ZFIRSTNAME,'')||' '||COALESCE(r.ZLASTNAME,'')), p.ZFULLNUMBER "
                "FROM ZABCDRECORD r JOIN ZABCDPHONENUMBER p ON p.ZOWNER=r.Z_PK "
                "UNION ALL SELECT TRIM(COALESCE(r.ZFIRSTNAME,'')||' '||COALESCE(r.ZLASTNAME,'')), e.ZADDRESS "
                "FROM ZABCDRECORD r JOIN ZABCDEMAILADDRESS e ON e.ZOWNER=r.Z_PK").fetchall()
            con.close()
            out += [(n, v) for n, v in rows if n and v]
        except sqlite3.Error:
            continue
    return out


def _who(handle: str, book: list[tuple[str, str]]) -> str:
    key = _digits(handle) or handle.lower()
    for name, value in book:
        if (_digits(value) or value.lower()) == key:
            return name
    return "an unknown number"


def _resolve(to: str) -> tuple[str | None, str]:
    """(handle, spoken name) or (None, the question to ask)."""
    to = to.strip()
    if "@" in to or len(_digits(to)) >= 7:
        return to, to
    book = _contacts()
    hits = {}
    for name, value in book:
        if to.lower() in name.lower():
            hits.setdefault(name, value)
    if not hits:
        return None, f"I can't find {to} in your contacts, sir. Give me the number?"
    if len(hits) > 1:
        names = ", ".join(sorted(hits)[:4])
        return None, f"I have more than one {to}, sir: {names}. Which one?"
    name, value = next(iter(hits.items()))
    return value, name


def _text_of(text, body) -> str:
    """Newer macOS keeps the words in attributedBody, not text."""
    if text:
        return text
    if not body:
        return ""
    m = re.search(rb"NSString\x01\x94\x84\x01\+(.)(.*)", body, re.S)
    if not m:
        return ""
    raw = m.group(2)
    n = m.group(1)[0]
    if n == 0x81:                   # long string: next two bytes are the length
        n, raw = int.from_bytes(raw[:2], "little"), raw[2:]
    return raw[:n].decode("utf-8", "replace")


async def read_texts(args: dict) -> str:
    who = str(args.get("contact", "")).strip()
    limit = max(1, min(int(args.get("limit") or 10), 30))
    return await asyncio.to_thread(_read_blocking, who, limit)


def _read_blocking(who: str, limit: int) -> str:
    try:
        con = sqlite3.connect(f"file:{CHAT_DB}?mode=ro", uri=True)
        con.execute("SELECT 1 FROM message LIMIT 1")
    except sqlite3.Error:
        return NO_ACCESS
    book = _contacts()
    where, params = "", []
    if who:
        handle, name = _resolve(who)
        if handle is None:
            return name
        where = "WHERE h.id LIKE ?"
        params = [f"%{_digits(handle) or handle}%"]
    rows = con.execute(
        f"SELECT m.date, m.is_from_me, m.text, m.attributedBody, h.id FROM message m "
        f"LEFT JOIN handle h ON h.ROWID = m.handle_id {where} ORDER BY m.date DESC LIMIT ?",
        params + [limit]).fetchall()
    con.close()
    if not rows:
        return f"No texts with {who}, sir." if who else "No texts at all, sir."
    lines = []
    for date, mine, text, body, handle in reversed(rows):
        words = _text_of(text, body).strip() or "(a photo or attachment)"
        ago = int((time.time() - (date / 1e9 + APPLE_EPOCH)) / 60)
        when = f"{ago} min ago" if ago < 90 else f"{ago // 60} h ago" if ago < 48 * 60 else f"{ago // 1440} days ago"
        sender = "You" if mine else _who(handle or "", book)
        lines.append(f"[{when}] {sender}: {words[:300]}")
    return "\n".join(lines)


async def send_text(args: dict) -> str:
    global _staged
    to, message = str(args.get("to", "")).strip(), str(args.get("message", "")).strip()
    if not to or not message:
        return "I need who it's to and what it says, sir."
    if len(message) > MAX_TEXT:
        return "That's too long for one text, sir."
    same = _staged and _staged["to"] == to and _staged["message"] == message
    if not same or _heard <= _staged["at"]:
        handle, name = await asyncio.to_thread(_resolve, to)
        if handle is None:
            return name
        if not _HANDLE.fullmatch(handle.strip()):
            return "That doesn't look like a phone number or email, sir."
        _staged = {"to": to, "handle": handle, "name": name, "message": message, "at": _heard}
        return (f"STAGED, not sent. Read it back to Drey in one sentence: the text to {name} "
                f"saying \"{message}\". Send it only by calling send_text again with the same "
                f"to and message after he says yes.")
    handle, name = _staged["handle"], _staged["name"]
    _staged = None
    # The words travel as an argument, never inside the script, so nothing in
    # them can change what AppleScript does.
    script = ['on run argv', 'tell application "Messages"',
              'set svc to 1st account whose service type = iMessage',
              'send (item 2 of argv) to participant (item 1 of argv) of svc',
              'end tell', 'end run']
    # "--" ends osascript's own options: without it a text starting with "-"
    # (say "-l ...") is read as a flag, not as words to send.
    cmd = ["osascript"] + sum([["-e", s] for s in script], []) + ["--", handle, message]
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        _out, err = await asyncio.wait_for(proc.communicate(), 30)
    except asyncio.TimeoutError:
        proc.kill()
        return "Messages didn't answer, sir, so I can't say it sent."
    if proc.returncode != 0:
        e = err.decode(errors="replace")
        if "-1743" in e or "not allowed" in e.lower():
            return ("macOS hasn't let me control Messages yet, sir. Allow it in System Settings, "
                    "Privacy and Security, Automation.")
        return f"Messages refused it, sir: {e.strip()[:160]}"
    return f"Passed to Messages for {name}."


if __name__ == "__main__":
    # ponytail: one self-check for the guard that matters, staging without a new turn never sends.
    import unittest.mock as um

    async def check():
        global _heard
        with um.patch(__name__ + "._resolve", return_value=("+15551234567", "Test")), \
             um.patch("asyncio.create_subprocess_exec") as spawn:
            r1 = await send_text({"to": "Test", "message": "hi"})
            r2 = await send_text({"to": "Test", "message": "hi"})          # same turn: must not send
            assert r1.startswith("STAGED") and r2.startswith("STAGED") and not spawn.called, (r1, r2)
            heard()
            r3 = await send_text({"to": "Test", "message": "hello"})       # different words: re-stage
            assert r3.startswith("STAGED") and not spawn.called
        with um.patch(__name__ + "._resolve", return_value=("-l JavaScript", "-l JavaScript")):
            assert (await send_text({"to": "x", "message": "hi"})).startswith("That doesn't look")
        assert _HANDLE.fullmatch("+1 (555) 123-4567") and _HANDLE.fullmatch("sam@example.com")
        assert not _HANDLE.fullmatch("-e") and not _HANDLE.fullmatch("-x@y.com")
        assert _text_of(None, b"xxNSString\x01\x94\x84\x01+\x05hello rest") == "hello"
        print("messages self-check: ok")
    asyncio.run(check())
