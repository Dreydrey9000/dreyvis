"""
ears.py — speech-to-text for the Dreyvis desktop app.

Electron's built-in SpeechRecognition refuses to run ("not-allowed" even with
the mic granted), so the desktop app records the mic itself and posts each
spoken phrase here. One long-lived Whisper worker does the transcribing.
Turned on by EARS_PYTHON in .env (the .venv-ears interpreter).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import struct
from pathlib import Path
from typing import Optional

log = logging.getLogger("jarvis.ears")

EARS_PYTHON = os.getenv("EARS_PYTHON", "")
# mlx-whisper on a Mac; ears_worker_cpp.py (whisper.cpp) on the Windows PC.
EARS_WORKER = os.getenv("EARS_WORKER", "ears_worker.py")
MAX_SECONDS = 30
MAX_BYTES = MAX_SECONDS * 16000 * 4      # float32 mono 16 kHz
_proc: Optional[asyncio.subprocess.Process] = None
_lock = asyncio.Lock()


def enabled() -> bool:
    return bool(EARS_PYTHON) and Path(EARS_PYTHON).exists()


async def transcribe(pcm: bytes, timeout: float = 60.0) -> Optional[str]:
    """Raw float32 16 kHz mono PCM in, text out. None on failure."""
    global _proc
    if not enabled() or not pcm or len(pcm) % 4 or len(pcm) > MAX_BYTES:
        return None
    async with _lock:
        try:
            if _proc is None or _proc.returncode is not None:
                _proc = await asyncio.create_subprocess_exec(
                    EARS_PYTHON, str(Path(__file__).parent / EARS_WORKER),
                    stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                )
            _proc.stdin.write(struct.pack(">I", len(pcm)) + pcm)
            await _proc.stdin.drain()
            line = await asyncio.wait_for(_proc.stdout.readline(), timeout)
            return json.loads(line)["text"]
        except (asyncio.TimeoutError, OSError, ValueError, KeyError) as e:
            log.error(f"ears error: {e!r}")
            if _proc and _proc.returncode is None:
                _proc.kill()
            _proc = None
            return None
