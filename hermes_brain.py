"""
hermes_brain.py: the orb's brain when it is Hermes Jax instead of the claude CLI.

Set JAX_BRAIN=hermes and the orb sends each turn to the Hermes gateway's
OpenAI-style door (default http://127.0.0.1:8642), so the voice you talk to is
the same Jax that answers texts: same memory, same tools.

  HERMES_API_URL       default http://127.0.0.1:8642
  HERMES_API_KEY       the gateway's API_SERVER_KEY (or HERMES_API_KEY_FILE, a file holding it)
  HERMES_SESSION_ID    the voice chat thread, default "jax-desktop-voice"
  HERMES_VOICE_HINT    one line put in front of every spoken turn

  HERMES_VOICE_THREAD      "single" (default) keeps one endless chat thread. "rolling" starts a
                           new thread when the voice chat has been quiet or the thread has grown
                           big, so every turn sends a small prompt and Jax answers sooner. The
                           last few exchanges are carried across as a short recap.
  HERMES_VOICE_IDLE_MIN    quiet minutes before a new thread (rolling only), default 30
  HERMES_VOICE_MAX_TOKENS  prompt size that forces a new thread (rolling only), default 60000

Hermes keeps its own context, so the orb never compacts it. "Start fresh" opens a new thread.
"""
import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

import httpx

import data_paths
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


def sse_usage(line: str) -> Optional[int]:
    """Prompt tokens from the closing `usage` line of the stream, else None.
    It is the SUM over every model call in the turn, not the size of one prompt."""
    if not line.startswith("data:") or '"usage"' not in line:
        return None
    try:
        usage = json.loads(line[5:].strip()).get("usage") or {}
        return int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0) or None
    except (ValueError, AttributeError, TypeError):
        return None


def sse_tool_started(line: str) -> bool:
    """True for the `hermes.tool.progress` data line that says a tool began."""
    return line.startswith("data:") and '"toolCallId"' in line and '"running"' in line


def sse_failure(line: str) -> Optional[str]:
    """Why the turn failed, from the stream's closing line, else None.
    Hermes answers 200 and only says so at the end: a finish_reason that is not
    "stop", with an `error` beside it. Unread, that was a turn that ended in silence."""
    if not line.startswith("data:") or '"finish_reason"' not in line:
        return None
    try:
        d = json.loads(line[5:].strip())
        reason = ((d.get("choices") or [{}])[0]).get("finish_reason")
    except (ValueError, AttributeError, IndexError):
        return None
    if reason in (None, "stop"):
        return None
    err = d.get("error") if isinstance(d.get("error"), dict) else {}
    return str(err.get("message") or f"Hermes ended the turn with {reason}")[:300]


def sse_tool_name(line: str) -> str:
    """The tool named on a `hermes.tool.progress` line, or "" if it cannot be read."""
    try:
        return str(json.loads(line[5:].strip()).get("tool") or "")
    except (ValueError, AttributeError):
        return ""


def lookup_label(tool: str) -> str:
    """A few plain words for what Jax is doing, for the apps to show while he looks."""
    t = (tool or "").lower()
    if any(k in t for k in ("session_search", "memory", "recall", "hindsight")):
        return "Searching memory"
    if any(k in t for k in ("web", "browser", "search", "crawl", "scrape")):
        return "Searching the web"
    if any(k in t for k in ("terminal", "execute", "process")):
        return "Running a command"
    if any(k in t for k in ("file", "read", "patch")):
        return "Reading files"
    if any(k in t for k in ("calendar", "gmail", "mail", "message")):
        return "Checking your accounts"
    return "Looking it up"


RECAP_TURNS = 6          # exchanges carried into a new thread
RECAP_CHARS = 300        # per side, per exchange


class VoiceThread:
    """Which Hermes chat thread the orb talks in.

    One endless thread made every turn send the whole voice history: 125,000
    tokens on 2026-11-21, which cost about 1.5 seconds a turn before the first
    word. Rolling keeps the prompt small. State lives in a small JSON file so a
    server restart does not lose the place. `clock` is wall time (it is saved).
    """

    def __init__(self, base: str, path: Optional[Path], *, rolling: bool, idle_sec: float,
                 max_tokens: int, name: str = "Drey", clock=time.time):
        self.base, self.path, self.rolling = base, path, rolling
        self.idle_sec, self.max_tokens, self.name, self._clock = idle_sec, max_tokens, name, clock
        self.session = base
        self.last_turn = 0.0
        self.prompt_tokens = 0
        self.recap = ""
        self.tail: list[list[str]] = []
        if rolling:
            self._load()

    def _load(self) -> None:
        try:
            d = json.loads(self.path.read_text(encoding="utf-8")) if self.path else {}
        except (OSError, ValueError):
            d = {}
        if isinstance(d, dict) and str(d.get("session", "")).startswith(self.base + "-"):
            self.session = d["session"]
            self.last_turn = float(d.get("last_turn") or 0)
            self.prompt_tokens = int(d.get("prompt_tokens") or 0)
            self.recap = str(d.get("recap") or "")
            self.tail = [list(map(str, x)) for x in d.get("tail") or [] if len(x) == 2][-RECAP_TURNS:]

    def _save(self) -> None:
        if not (self.rolling and self.path):
            return
        try:
            self.path.write_text(json.dumps({
                "session": self.session, "last_turn": self.last_turn,
                "prompt_tokens": self.prompt_tokens, "recap": self.recap, "tail": self.tail}),
                encoding="utf-8")
        except OSError as e:
            log.warning(f"hermes brain: cannot save the voice thread: {e}")

    def fresh(self, *, carry: bool = True, why: str = "") -> None:
        """Start a new thread. `carry` takes the last few exchanges along as a recap."""
        if not self.rolling:
            return
        if not carry:
            self.tail = []
        self.recap = "\n".join(f"{self.name}: {u}\nJax: {r}" for u, r in self.tail)
        self.session = f"{self.base}-{time.strftime('%Y%m%d-%H%M%S', time.localtime(self._clock()))}"
        self.prompt_tokens = 0
        log.info("hermes brain: new voice thread %s (%s), recap of %d exchange(s)",
                 self.session, why or "asked", len(self.tail))
        self._save()

    def before_turn(self) -> None:
        if not self.rolling:
            return
        if self.session == self.base:
            self.fresh(why="first rolling turn")
        elif self.last_turn and self._clock() - self.last_turn >= self.idle_sec:
            self.fresh(why=f"quiet for {(self._clock() - self.last_turn) / 60:.0f} min")
        elif self.prompt_tokens >= self.max_tokens:
            self.fresh(why=f"thread reached {self.prompt_tokens} tokens")

    def system_message(self) -> Optional[dict]:
        """The same words for the whole life of a thread, so the model's cache holds."""
        if not (self.rolling and self.recap):
            return None
        return {"role": "system", "content":
                "Earlier in this voice chat, oldest first. For continuity only: anything "
                "older is in your memory and session search.\n" + self.recap}

    def after_turn(self, user: str, reply: str, prompt_tokens: Optional[int], tools: int) -> None:
        if not self.rolling:
            return
        self.last_turn = self._clock()
        if prompt_tokens:
            # One model call per tool round plus the last, at least: so this is
            # exact for a plain turn and a floor for a turn that used tools.
            per_call = prompt_tokens // (tools + 1)
            self.prompt_tokens = per_call if tools == 0 else max(self.prompt_tokens, per_call)
        if reply.strip():
            self.tail = (self.tail + [[user.strip()[:RECAP_CHARS], reply.strip()[:RECAP_CHARS]]])[-RECAP_TURNS:]
        self._save()


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
        self.hint = os.getenv("HERMES_VOICE_HINT", VOICE_HINT)
        self.model_in_use = os.getenv("HERMES_MODEL", "Jax")
        self.thread = VoiceThread(
            os.getenv("HERMES_SESSION_ID", "jax-desktop-voice"),
            data_paths.data_dir() / "hermes_voice_thread.json",
            rolling=os.getenv("HERMES_VOICE_THREAD", "single").strip().lower() == "rolling",
            idle_sec=float(os.getenv("HERMES_VOICE_IDLE_MIN", "30")) * 60,
            max_tokens=int(os.getenv("HERMES_VOICE_MAX_TOKENS", "60000")),
            name=os.getenv("USER_NAME", "Drey") or "Drey")
        # One client for the life of the brain: a new one per turn rebuilt its
        # connection pool every time the user spoke.
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def session(self) -> str:
        return self.thread.session

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
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()

    async def rotate(self, handover: Optional[str] = None) -> bool:
        """The user said "start fresh": a new thread with nothing carried across.
        (With one endless thread there is nothing to do, as before.)"""
        self._rotation_pending = False
        self.thread.fresh(carry=False, why="start fresh")
        return True

    def _http(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient()
        return self._client

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
        self.thread.before_turn()
        messages = [{"role": "user", "content": f"{self.hint}\n{text}" if self.hint else text}]
        recap = self.thread.system_message()
        if recap:
            messages.insert(0, recap)
        body = {"model": self.model_in_use, "stream": True, "messages": messages}
        prompt_tokens: Optional[int] = None
        failure: Optional[str] = None
        tools = 0
        try:
            async with self._http().stream("POST", f"{self.url}/v1/chat/completions",
                                           headers=self._headers(), json=body,
                                           timeout=httpx.Timeout(timeout, connect=10)) as r:
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
                        elif sse_tool_started(line):
                            tools += 1
                            if on_tool:          # the server shows "searching" and may say "one moment"
                                try:
                                    on_tool(sse_tool_name(line))
                                except Exception as e:
                                    log.warning(f"hermes brain: tool callback failed: {e}")
                        else:
                            prompt_tokens = sse_usage(line) or prompt_tokens
                            failure = sse_failure(line) or failure
                    if failure and not "".join(t.parts).strip():
                        # The model provider failed (every retry and fallback
                        # spent) and nothing was said: say so, do not go quiet.
                        t.error = failure
                        t.finish("error")
                        return t.result(None)
                    t.finish("result")
                    self.thread.after_turn(text, "".join(t.parts), prompt_tokens, tools)
                    log.info("hermes turn: thread=%s prompt_tokens=%s tool_calls=%d",
                             self.session, prompt_tokens, tools)
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
    assert sse_usage('data: {"choices":[{"delta":{}}],"usage":{"prompt_tokens":53918}}') == 53918
    assert sse_usage('data: {"choices":[{"delta":{"content":"usage"}}]}') is None
    assert sse_tool_started('data: {"tool": "terminal", "toolCallId": "c1", "status": "running"}')
    assert not sse_tool_started('data: {"tool": "terminal", "toolCallId": "c1", "status": "completed"}')
    assert sse_failure('data: {"choices":[{"delta":{},"finish_reason":"stop"}]}') is None
    assert sse_failure('data: {"choices":[{"delta":{},"finish_reason":"error"}],"error":{"message":"HTTP 502"}}') == "HTTP 502"
    assert sse_failure('data: {"choices":[{"delta":{"content":"x"},"finish_reason":null}]}') is None
    assert sse_tool_name('data: {"tool": "session_search", "toolCallId": "c1", "status": "running"}') == "session_search"
    assert lookup_label("session_search") == "Searching memory" and lookup_label("") == "Looking it up"
    print("hermes_brain ok")


if __name__ == "__main__":
    demo()
