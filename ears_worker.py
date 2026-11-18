"""
ears_worker.py — Dreyvis's local ears (Whisper on Apple Silicon, free, offline).

Runs under .venv-ears (mlx-whisper), not the main venv. ears.py starts one and
keeps it alive so the model loads once.

Protocol: 4-byte big-endian length + raw float32 mono PCM at 16 kHz in on stdin,
          one JSON line {"text": "..."} out on stdout.
"""
import json
import struct
import sys

import mlx_whisper
import numpy as np

MODEL = "mlx-community/whisper-large-v3-turbo"
# Whisper "hears" these in silence or music. A phrase that is only one of them is dropped.
HALLUCINATIONS = {
    "", "you", "thank you", "thanks", "thank you very much", "thanks for watching",
    "thank you for watching", "bye", "okay", "so", "uh", "um", "hmm", ".",
}

out = sys.stdout
sys.stdout = sys.stderr            # model logs must not corrupt the reply pipe
inp = sys.stdin.buffer


def clean(text: str) -> str:
    t = text.strip()
    key = t.lower().strip(" .!?,")
    return "" if key in HALLUCINATIONS else t


while True:
    head = inp.read(4)
    if len(head) < 4:
        break
    (n,) = struct.unpack(">I", head)
    audio = np.frombuffer(inp.read(n), dtype=np.float32)
    try:
        r = mlx_whisper.transcribe(
            audio, path_or_hf_repo=MODEL, language="en",
            condition_on_previous_text=False, no_speech_threshold=0.6,
            initial_prompt="Talking to Dreyvis, Drey's assistant.",   # spells the name right
        )
        text = clean(r.get("text", ""))
    except Exception as e:         # one bad clip must not kill the ears
        print(f"ears_worker: {e!r}", file=sys.stderr)
        text = ""
    out.write(json.dumps({"text": text}) + "\n")
    out.flush()
