"""
jax_service.py — keeps Jax running on the Windows PC.

A Windows scheduled task named "Jax" starts this at logon (and re-checks every
few minutes). It runs server.py on 127.0.0.1 only, restarts it if it stops, and
writes logs to JAX_LOG_DIR. Standard library only.

  Turn Jax off:  create the file JAX_OFF in JAX_LOG_DIR. Delete it to turn back on.
  Logs:          JAX_LOG_DIR\\server.log (current) and server.log.1 (previous).

Run by hand to test: python jax_service.py --once  (starts the server, waits for
it to answer, prints the result, stops it).
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOST, PORT = "127.0.0.1", int(os.environ.get("JAX_PORT", "8340"))
LOG_DIR = Path(os.environ.get("JAX_LOG_DIR", HERE / "logs"))
LOG_MAX = 20 * 1024 * 1024
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def server_exe() -> str:
    """jax-server.exe beside us (a renamed python.exe, so Task Manager says jax), else this Python."""
    named = Path(sys.executable).with_name("jax-server.exe")
    return str(named) if named.exists() else sys.executable


def port_busy() -> bool:
    with socket.socket() as s:
        s.settimeout(1)
        return s.connect_ex((HOST, PORT)) == 0


def off() -> bool:
    return (LOG_DIR / "JAX_OFF").exists()


def note(msg: str) -> None:
    with open(LOG_DIR / "service.log", "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")


def start() -> subprocess.Popen:
    log = LOG_DIR / "server.log"
    if log.exists() and log.stat().st_size > LOG_MAX:
        log.replace(LOG_DIR / "server.log.1")
    f = open(log, "ab")
    return subprocess.Popen(
        [server_exe(), str(HERE / "server.py"), "--host", HOST, "--port", str(PORT)],
        cwd=HERE, stdout=f, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
        creationflags=NO_WINDOW,
    )


def single_instance():
    """Hold a lock file for our whole life; a second copy exits at once."""
    fh = open(LOG_DIR / "service.lock", "a+")
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return None
    return fh


def wait_until_up(seconds: float) -> bool:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if port_busy():
            return True
        time.sleep(1)
    return False


def run_forever() -> None:
    backoff = 5
    child = None
    while True:
        if off():
            if child and child.poll() is None:
                note("JAX_OFF found: stopping server")
                child.terminate()
                child.wait(30)
            child = None
            time.sleep(10)
            continue
        if child is None:
            if port_busy():          # an older copy still holds the port; let it be
                time.sleep(30)
                continue
            child, started = start(), time.monotonic()
            note(f"server started pid={child.pid}")
        code = child.poll()
        if code is None:
            time.sleep(5)
            continue
        ran = time.monotonic() - started
        note(f"server stopped code={code} after {ran:.0f}s")
        child = None
        backoff = 5 if ran > 600 else min(backoff * 2, 300)
        time.sleep(backoff)


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if "--once" in sys.argv:
        if port_busy():
            print(f"port {PORT} already in use")
            return 1
        child = start()
        up = wait_until_up(120)
        print("server answered" if up else "server did not answer in 120s")
        child.terminate()
        child.wait(30)
        return 0 if up else 1
    lock = single_instance()
    if lock is None:
        return 0                     # already running
    note("service started")
    run_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
