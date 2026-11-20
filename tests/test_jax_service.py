"""The PC pieces: the keep-alive service's switches and the whisper.cpp ears' audio handling."""
import array
import importlib
import socket
import wave

import ears_worker_cpp


def test_off_switch_and_port_check(tmp_path, monkeypatch):
    monkeypatch.setenv("JAX_LOG_DIR", str(tmp_path))
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        s.listen()
        monkeypatch.setenv("JAX_PORT", str(s.getsockname()[1]))
        import jax_service
        svc = importlib.reload(jax_service)
        assert svc.port_busy()
    assert not svc.off()
    (tmp_path / "JAX_OFF").touch()
    assert svc.off()
    first = svc.single_instance()
    assert first is not None


def test_ears_wav_and_cleanup(tmp_path):
    pcm = array.array("f", [0.0, 0.5, -0.5, 2.0]).tobytes()
    path = tmp_path / "a.wav"
    ears_worker_cpp.to_wav(pcm, str(path))
    with wave.open(str(path)) as w:
        assert (w.getframerate(), w.getnchannels(), w.getnframes()) == (16000, 1, 4)
        assert array.array("h", w.readframes(4)).tolist() == [0, 16383, -16383, 32767]
    assert ears_worker_cpp.clean("  Thank you.  ") == ""
    assert ears_worker_cpp.clean("[BLANK_AUDIO]") == ""
    assert ears_worker_cpp.clean(" Open the  dashboard ") == "Open the dashboard"
