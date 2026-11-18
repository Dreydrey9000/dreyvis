"""
tts.py — Fish Audio synthesis, one request per sentence chunk.

The response is streamed so time-to-first-byte can be measured; the chunk is
returned whole because the browser decodes one complete MP3 per chunk.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import struct
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx

log = logging.getLogger("jarvis.tts")

FISH_TTS_URL = "https://api.fish.audio/v1/tts"


@dataclass
class SynthResult:
    audio: bytes
    first_byte_sec: float
    total_sec: float


# --- Local Kokoro voice (Drey's swap: free, no Fish Audio key) ---------------
# Turned on with JARVIS_TTS=kokoro in .env. One worker process is kept alive so
# the model loads once; a lock makes it one sentence at a time.
KOKORO_PYTHON = os.getenv("KOKORO_PYTHON", "")
KOKORO_VOICE = os.getenv("KOKORO_VOICE", "bm_george")
_kokoro_proc: Optional[asyncio.subprocess.Process] = None
_kokoro_lock = asyncio.Lock()


def kokoro_enabled() -> bool:
    return os.getenv("JARVIS_TTS", "").lower() == "kokoro" and bool(KOKORO_PYTHON)


async def _kokoro_chunk(text: str, timeout: float = 60.0) -> Optional[SynthResult]:
    global _kokoro_proc
    t0 = time.monotonic()
    async with _kokoro_lock:
        try:
            if _kokoro_proc is None or _kokoro_proc.returncode is not None:
                _kokoro_proc = await asyncio.create_subprocess_exec(
                    KOKORO_PYTHON, str(Path(__file__).parent / "kokoro_worker.py"),
                    stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                    env={**os.environ, "VIRTUAL_ENV": str(Path(KOKORO_PYTHON).parent.parent),
                         "PATH": f"{Path(KOKORO_PYTHON).parent}:{os.environ.get('PATH', '')}"},
                )
            p = _kokoro_proc
            p.stdin.write((json.dumps({"text": text, "voice": KOKORO_VOICE}) + "\n").encode())
            await p.stdin.drain()
            (n,) = struct.unpack(">I", await asyncio.wait_for(p.stdout.readexactly(4), timeout))
            audio = await asyncio.wait_for(p.stdout.readexactly(n), timeout)
        except (asyncio.TimeoutError, asyncio.IncompleteReadError, OSError) as e:
            log.error(f"Kokoro TTS error: {e!r}")
            if _kokoro_proc and _kokoro_proc.returncode is None:
                _kokoro_proc.kill()      # the pipe is out of step now; start fresh next time
            _kokoro_proc = None
            return None
    if not audio:
        return None
    total = time.monotonic() - t0
    return SynthResult(audio, total, total)


async def synthesize_chunk(text: str, *, api_key: str, voice_id: str,
                           client: Optional[httpx.AsyncClient] = None,
                           latency: str = "balanced", timeout: float = 15.0) -> Optional[SynthResult]:
    text = (text or "").strip()
    if text and kokoro_enabled():
        return await _kokoro_chunk(text)
    if not text or not api_key:
        return None
    own = client is None
    client = client or httpx.AsyncClient(timeout=timeout)
    t0 = time.monotonic()
    first: Optional[float] = None
    buf = bytearray()
    try:
        async with client.stream(
            "POST", FISH_TTS_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"text": text, "reference_id": voice_id, "format": "mp3", "mp3_bitrate": 128, "latency": latency},
            timeout=timeout,
        ) as resp:
            if resp.status_code != 200:
                log.error(f"TTS {resp.status_code} for {text[:40]!r}")
                return None
            async for part in resp.aiter_bytes():
                if first is None:
                    first = time.monotonic() - t0
                buf.extend(part)
    except (httpx.HTTPError, OSError) as e:
        log.error(f"TTS error: {e}")
        return None
    finally:
        if own:
            try:
                await client.aclose()
            except Exception as e:      # never turn a clean None into an exception
                log.debug(f"TTS client close failed: {e}")
    if not buf:
        return None
    return SynthResult(bytes(buf), first if first is not None else 0.0, time.monotonic() - t0)
