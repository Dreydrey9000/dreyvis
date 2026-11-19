"""
kokoro_worker.py — local Kokoro voice for JARVIS (Drey's swap for Fish Audio).

Runs under the Kokoro venv, NOT the JARVIS venv (Kokoro needs torch). tts.py
starts one of these and keeps it alive so the model loads once.

Protocol: one JSON line in on stdin  {"text": "...", "voice": "bm_george"}
          4-byte big-endian length + MP3 bytes out on stdout (length 0 = failed).
MP3 because speech.py reads the clip length from MP3 frames (ack_floor_seconds).
"""
# Show up as "dreyvis-voice" in Activity Monitor instead of "Python" (~/.local/bin/pyname). Safe to delete.
try:
    import os as _os, runpy as _runpy
    _runpy.run_path(_os.path.expanduser("~/.local/bin/pyname"))["name_me"]("dreyvis-voice")
except Exception:
    pass

import io
import json
import os
import struct
import subprocess
import sys

import numpy as np
import soundfile as sf
from kokoro import KPipeline

out = sys.stdout.buffer
sys.stdout = sys.stderr            # anything Kokoro prints must not corrupt the audio pipe
pipelines = {}


def synth(text: str, voice: str) -> bytes:
    lang = voice[0]                # voice prefix is the language: b = British, a = American
    if lang not in pipelines:
        pipelines[lang] = KPipeline(lang_code=lang)
    chunks = [audio for _g, _p, audio in pipelines[lang](text, voice=voice)]
    if not chunks:
        return b""
    wav = io.BytesIO()
    sf.write(wav, np.concatenate(chunks), 24000, format="WAV")
    mp3 = subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-i", "pipe:0", "-f", "mp3", "-b:a", "128k", "pipe:1"],
        input=wav.getvalue(), capture_output=True,
    )
    return mp3.stdout if mp3.returncode == 0 else b""


# Load the model now, run one tiny warm-up sentence, then tell tts.py we're ready.
# Loading is the slow part; doing it before any real sentence keeps replies quick.
try:
    synth("Ready.", os.environ.get("KOKORO_VOICE") or "bm_george")
except Exception as e:
    print(f"kokoro_worker warm-up: {e!r}", file=sys.stderr)
out.write(struct.pack(">I", 0xFFFFFFFF))
out.flush()

for line in sys.stdin:
    try:
        req = json.loads(line)
        data = synth(req["text"], req.get("voice") or "bm_george")
    except Exception as e:         # one bad sentence must not kill the voice
        print(f"kokoro_worker: {e!r}", file=sys.stderr)
        data = b""
    out.write(struct.pack(">I", len(data)) + data)
    out.flush()
