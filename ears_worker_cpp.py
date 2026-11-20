"""
ears_worker_cpp.py — Dreyvis's ears on the Windows PC (whisper.cpp, free, offline).

The Mac uses ears_worker.py (mlx-whisper, Apple Silicon only). On the PC, set
EARS_WORKER=ears_worker_cpp.py, WHISPER_CLI to whisper-cli.exe and WHISPER_MODEL
to a ggml model file. Standard library only, so it runs under the main venv.

Protocol (same as ears_worker.py): 4-byte big-endian length + raw float32 mono
PCM at 16 kHz in on stdin, one JSON line {"text": "..."} out on stdout.
"""
import array
import json
import os
import struct
import subprocess
import sys
import tempfile
import wave

CLI = os.environ.get("WHISPER_CLI", "whisper-cli")
MODEL = os.environ.get("WHISPER_MODEL", "")
THREADS = os.environ.get("WHISPER_THREADS", "8")
PROMPT = "Talking to Dreyvis, Drey's assistant."      # spells the name right
# Whisper "hears" these in silence or music. A phrase that is only one of them is dropped.
HALLUCINATIONS = {
    "", "you", "thank you", "thanks", "thank you very much", "thanks for watching",
    "thank you for watching", "bye", "okay", "so", "uh", "um", "hmm", ".",
    "[blank_audio]", "(silence)",
}
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def clean(text: str) -> str:
    t = " ".join(text.split())
    key = t.lower().strip(" .!?,")
    return "" if key in HALLUCINATIONS or t.lower() in HALLUCINATIONS else t


def to_wav(pcm: bytes, path: str) -> None:
    floats = array.array("f")
    floats.frombytes(pcm)
    if sys.byteorder == "big":
        floats.byteswap()
    ints = array.array("h", (max(-32768, min(32767, int(x * 32767))) for x in floats))
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(ints.tobytes())


def transcribe(pcm: bytes) -> str:
    fd, path = tempfile.mkstemp(suffix=".wav", prefix="jax-ears-")
    os.close(fd)
    try:
        to_wav(pcm, path)
        r = subprocess.run(
            [CLI, "-m", MODEL, "-f", path, "-l", "en", "-t", THREADS, "-nt", "-np",
             "--prompt", PROMPT],
            capture_output=True, timeout=120, creationflags=NO_WINDOW,
        )
        if r.returncode != 0:
            print(f"ears_worker_cpp: exit {r.returncode}: {r.stderr[-400:]!r}", file=sys.stderr)
            return ""
        return clean(r.stdout.decode("utf-8", "replace"))
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def main() -> None:
    out, inp = sys.stdout, sys.stdin.buffer
    while True:
        head = inp.read(4)
        if len(head) < 4:
            break
        (n,) = struct.unpack(">I", head)
        try:
            text = transcribe(inp.read(n))
        except Exception as e:     # one bad clip must not kill the ears
            print(f"ears_worker_cpp: {e!r}", file=sys.stderr)
            text = ""
        out.write(json.dumps({"text": text}) + "\n")
        out.flush()


if __name__ == "__main__":
    main()
