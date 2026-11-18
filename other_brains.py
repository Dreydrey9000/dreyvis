"""
other_brains.py — let Dreyvis hand a question to another AI.

  codex     the Codex CLI, on Drey's ChatGPT plan (read-only sandbox, no edits)
  grok      the Grok CLI, on Drey's Grok plan
  deepseek  DeepSeek's API, with the key in ~/.codex/.env (small per-use cost)

Every brain gets the question as an argument, never through a shell, and
answers in plain text that Dreyvis then speaks in his own words.
"""
from __future__ import annotations

import asyncio
import os
import re
import tempfile
from pathlib import Path
from typing import Optional

import httpx

BRAINS = ("codex", "grok", "deepseek")
TIMEOUT_SEC = 180
MAX_ANSWER = 4000
HOME = Path.home()
NOTE = ("Answer for someone who will hear it read aloud: plain sentences, no markdown, "
        "no code blocks, as short as the question allows.\n\n")


def _bin(name: str) -> Optional[str]:
    for d in (HOME / ".local/bin", Path("/opt/homebrew/bin"), Path("/usr/local/bin")):
        if (d / name).exists():
            return str(d / name)
    return None


async def _run(args: list[str], cwd: str) -> tuple[int, str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("ANTHROPIC_", "CLAUDE"))}
    proc = await asyncio.create_subprocess_exec(
        *args, cwd=cwd, env=env, stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        out, err = await asyncio.wait_for(proc.communicate(), TIMEOUT_SEC)
    except asyncio.TimeoutError:
        proc.kill()
        return 124, "", "timed out"
    return proc.returncode, out.decode(errors="replace"), err.decode(errors="replace")


async def _codex(question: str) -> str:
    exe = _bin("codex")
    if not exe:
        return "Codex is not installed."
    with tempfile.TemporaryDirectory() as tmp:
        last = Path(tmp) / "answer.txt"
        code, out, err = await _run([exe, "exec", "--sandbox", "read-only", "--skip-git-repo-check",
                                     "--ephemeral", "-o", str(last), NOTE + question], tmp)
        text = last.read_text(errors="replace").strip() if last.exists() else ""
    return text or f"Codex failed ({code}): {err.strip()[-300:]}"


async def _grok(question: str) -> str:
    exe = _bin("grok")
    if not exe:
        return "Grok is not installed."
    with tempfile.TemporaryDirectory() as tmp:
        code, out, err = await _run([exe, "-p", NOTE + question], tmp)
    return out.strip() or f"Grok failed ({code}): {err.strip()[-300:]}"


def _deepseek_key() -> Optional[str]:
    env_file = HOME / ".codex/.env"
    if not env_file.exists():
        return None
    for line in env_file.read_text(errors="replace").splitlines():
        m = re.match(r"\s*(?:export\s+)?DEEPSEEK_API_KEY\s*=\s*['\"]?([^'\"\s]+)", line)
        if m:
            return m.group(1)
    return None


async def _deepseek(question: str) -> str:
    key = _deepseek_key()
    if not key:
        return "DeepSeek has no key: add DEEPSEEK_API_KEY to ~/.codex/.env."
    async with httpx.AsyncClient(timeout=TIMEOUT_SEC) as client:
        r = await client.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={"model": os.getenv("DREYVIS_DEEPSEEK_MODEL", "deepseek-v4-pro"),
                  "messages": [{"role": "user", "content": NOTE + question}]},
        )
    if r.status_code != 200:
        return f"DeepSeek failed ({r.status_code})."
    return r.json()["choices"][0]["message"]["content"].strip()


async def ask(brain: str, question: str) -> str:
    brain = (brain or "").strip().lower()
    question = (question or "").strip()
    if brain not in BRAINS:
        return f"Unknown brain {brain!r}. Choose one of: {', '.join(BRAINS)}."
    if not question:
        return "No question was given."
    try:
        answer = await {"codex": _codex, "grok": _grok, "deepseek": _deepseek}[brain](question)
    except (httpx.HTTPError, OSError, KeyError, ValueError) as e:
        answer = f"{brain} failed: {e!r}"
    return answer[:MAX_ANSWER]
