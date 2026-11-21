import hermes_brain


def test_sse_parsing():
    hermes_brain.demo()


def test_off_by_default(monkeypatch):
    monkeypatch.delenv("JAX_BRAIN", raising=False)
    assert hermes_brain.use_hermes() is False
    monkeypatch.setenv("JAX_BRAIN", "Hermes")
    assert hermes_brain.use_hermes() is True
