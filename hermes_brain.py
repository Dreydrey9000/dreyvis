"""
hermes_brain.py: the orb's brain when it is Hermes Jax instead of the claude CLI.

Set JAX_BRAIN=hermes and the orb sends each turn to the Hermes gateway's
OpenAI-style door (default http://127.0.0.1:8642), so the voice you talk to is
the same Jax that answers texts: same memory, same tools.

  HERMES_API_URL       default http://127.0.0.1:8642
  HERMES_API_KEY       the gateway's API_SERVER_KEY (or HERMES_API_KEY_FILE, a file holding it)
  HERMES_SESSION_ID    the voice chat thread, default "jax-desktop-voice"
  HERMES_VOICE_HINT    one line put in front of every spoken turn

Hermes keeps its own context, so rotation here is a no-op.
"""
import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

import httpx

from brain import Brain, BrainConfig, TurnResult, _Turn

log = logging.getLogger("jarvis.brain.hermes")

VOICE_HINT = ("[Spoken through the voice orb. Answer out loud in one to three short "
              "sentences. No markdown, no lists, no links.]")


def use_hermes() -> bool:
    return os.getenv("JAX_BRAIN", "").strip().lower() == "hermes"


def _api_key() -> str:
    key = os.getenv("HERMES_API_KEY", "").strip()
    path = os.getenv("HERMES_API_KEY_FILE", "").strip()
    if not key and path:
        try:
            key = Path(path).read_text(encoding="utf-8").strip()
        except OSError as e:
            log.error(f"hermes brain: cannot read key file: {e}")
    return key


def sse_text(line: str) -> Optional[str]:
    """The text carried by one `data: {...}` line of the stream, else None."""
    if not line.startswith("data:"):
        return None
    body = line[5:].strip()
    if not body or body == "[DONE]":
        return None
    try:
        choice = (json.loads(body).get("choices") or [{}])[0]
    except (ValueError, AttributeError, IndexError):
        return None
    return (choice.get("delta") or {}).get("content") or None


class HermesBrain(Brain):
    def __init__(self, config: BrainConfig):
        super().__init__(config)
        self.url = os.getenv("HERMES_API_URL", "http://127.0.0.1:8642").rstrip("/")
        self.session = os.getenv("HERMES_SESSION_ID", "jax-desktop-voice")
        self.hint = os.getenv("HERMES_VOICE_HINT", VOICE_HINT)
        self.model_in_use = os.getenv("HERMES_MODEL", "Jax")

    @property
    def running(self) -> bool:
        return self._ready

    @property
    def ready(self) -> bool:
        return self._ready

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {_api_key()}", "X-Hermes-Session-Id": self.session}

    async def start(self) -> bool:
        self._stopping = False
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(f"{self.url}/health")
                ok = r.status_code == 200
                if ok:   # the key is the usual thing that is wrong, so prove it now
                    ok = (await c.get(f"{self.url}/v1/models", headers=self._headers())).status_code == 200
        except httpx.HTTPError as e:
            log.error(f"hermes brain: not reachable at {self.url}: {e}")
            ok = False
        self._ready, self._failed = ok, not ok
        self._failure_reason = None if ok else "auth"
        if ok:
            self.generation += 1
            await self._emit("ready", generation=self.generation, model=self.model_in_use)
        else:
            await self._emit("failed", reason=f"Hermes did not answer at {self.url}")
        return ok

    async def stop(self) -> None:
        self._stopping = True
        self._ready = False

    async def rotate(self, handover: Optional[str] = None) -> bool:
        self._rotation_pending = False
        return True

    async def _note_context(self) -> None:
        return None

    async def _turn_locked(self, text, origin, on_delta, timeout,
                           warmup: bool = False, on_tool=None) -> TurnResult:
        if not self._ready:
            # Hermes may simply have been restarting; one cheap retry of the handshake.
            if not await self.start():
                return TurnResult(origin, "", "not_running")
        t = _Turn(origin, on_delta, None)
        self._inflight = t
        body = {"model": self.model_in_use, "stream": True,
                "messages": [{"role": "user", "content": f"{self.hint}\n{text}" if self.hint else text}]}
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=10)) as c:
                async with c.stream("POST", f"{self.url}/v1/chat/completions",
                                    headers=self._headers(), json=body) as r:
                    if r.status_code != 200:
                        t.error = f"Hermes answered {r.status_code}"
                        t.finish("error")
                    else:
                        async for line in r.aiter_lines():
                            piece = sse_text(line)
                            if piece:
                                if t.first_delta is None:
                                    t.first_delta = time.monotonic() - t.started
                                t.parts.append(piece)
                                if on_delta:
                                    on_delta(piece)
                        t.finish("result")
        except httpx.TimeoutException:
            t.finish("timeout")
        except httpx.HTTPError as e:
            t.error = str(e)
            t.finish("died")
            self._ready = False
        finally:
            if self._inflight is t:
                self._inflight = None
        return t.result(None)


def demo() -> None:
    assert sse_text('data: {"choices":[{"delta":{"content":"hi"}}]}') == "hi"
    assert sse_text("data: [DONE]") is None
    assert sse_text(": keep-alive") is None
    assert sse_text('data: {"choices":[{"delta":{}}]}') is None
    assert sse_text("data: not json") is None
    print("hermes_brain ok")


if __name__ == "__main__":
    demo()
