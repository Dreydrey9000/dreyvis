"""The timer line: "Still thinking, sir." (JAX_STILL_THINKING=1).

A voice turn that has said nothing after the threshold gets one short
pre-rendered line. These tests drive the real speech scheduler with a fake
voice and a fake brain, so no model and no TTS run.
"""

import asyncio
import importlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from test_speech import Harness  # noqa: E402

STILL = "Still thinking, sir."
HOLD = "One moment, sir."


@pytest_asyncio.fixture
async def wired(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("JARVIS_BRAIN_AUTOSTART", "0")
    monkeypatch.setenv("JAX_STILL_THINKING", "1")
    import server as server_module
    importlib.reload(server_module)
    h = Harness()
    await h.sched.start()
    statuses = []

    async def voice_emit(msg):
        statuses.append(msg)

    monkeypatch.setattr(server_module, "speech", h.sched)
    monkeypatch.setattr(server_module, "_voice_emit", voice_emit)
    monkeypatch.setattr(server_module, "_still_audio", [(STILL, b"STILL")])
    monkeypatch.setattr(server_module, "_holding_audio", [(HOLD, b"HOLD")])
    yield server_module, h, statuses
    await h.sched.stop()


def _said(h):
    return [t for _, _, t in h.audio()]


async def _current_turn(h):
    u = h.sched.begin_turn()
    await asyncio.sleep(0.05)              # the pump makes it the one at the mouth
    return u


@pytest.mark.asyncio
async def test_fires_after_the_threshold_and_not_before(wired):
    server, h, statuses = wired
    u = await _current_turn(h)
    task = asyncio.create_task(server._still_thinking_timer(u, 0.3))
    await asyncio.sleep(0.15)
    assert _said(h) == [] and statuses == []          # not yet
    await asyncio.sleep(0.3)
    await task
    assert _said(h) == [STILL]
    assert {"type": "status", "state": "searching", "label": "Still thinking"} in statuses
    assert u.first_sent_at is None and u.filler_sent_at is not None   # not counted as the answer


@pytest.mark.asyncio
async def test_never_twice_and_no_holding_line_after_it(wired):
    server, h, _ = wired
    u = await _current_turn(h)
    assert server._still_thinking(u) is True
    assert server._still_thinking(u) is False         # one per turn
    server._lookup_started(u, "terminal")             # a tool starts later: no "One moment"
    await asyncio.sleep(0.05)
    assert _said(h) == [STILL]


@pytest.mark.asyncio
async def test_not_after_a_holding_line(wired):
    server, h, statuses = wired
    u = await _current_turn(h)
    server._lookup_started(u, "terminal")
    await asyncio.sleep(0.05)
    assert server._still_thinking(u) is False
    await asyncio.sleep(0.05)
    assert _said(h) == [HOLD]
    assert not any(m.get("label") == "Still thinking" for m in statuses)


@pytest.mark.asyncio
async def test_not_once_words_have_started(wired):
    server, h, _ = wired
    u = await _current_turn(h)
    h.sched.feed(u, "Four. ")
    assert server._still_thinking(u) is False


@pytest.mark.asyncio
async def test_a_hush_before_the_timer_stops_it(wired):
    server, h, statuses = wired
    u = await _current_turn(h)
    task = asyncio.create_task(server._still_thinking_timer(u, 0.2))
    await h.sched.barge_in(keep_unread=False, reason="hush (key)")
    await task
    await asyncio.sleep(0.05)
    assert _said(h) == [] and statuses == []


@pytest.mark.asyncio
async def test_a_hush_right_after_it_is_queued_stops_it(wired):
    server, h, _ = wired
    u = h.sched.begin_turn()
    h.sched._current = u                               # at the mouth, before the pump sends anything
    assert server._still_thinking(u) is True
    await h.sched.barge_in(keep_unread=False, reason="hush (key)")
    await asyncio.sleep(0.05)
    assert STILL not in _said(h)


@pytest.mark.asyncio
async def test_a_turn_queued_behind_another_stays_quiet(wired):
    server, h, _ = wired
    first = await _current_turn(h)
    h.sched.feed(first, "A long answer is playing. ")
    second = h.sched.begin_turn()
    await asyncio.sleep(0.05)
    assert server._still_thinking(second) is False     # it would play late


# -- the whole voice turn, with a fake brain ----------------------------------

class SlowBrain:
    ready = True
    failed = False

    def __init__(self, wait, answer="Two plus two is four.", stop_reason="result"):
        self.wait, self.answer, self.stop_reason = wait, answer, stop_reason

    async def turn(self, text, origin="user", on_delta=None, on_tool=None):
        await asyncio.sleep(self.wait)
        if self.stop_reason == "result" and on_delta:
            on_delta(self.answer + " ")
        return SimpleNamespace(stop_reason=self.stop_reason, text=self.answer if self.stop_reason == "result" else "",
                               error="HTTP 502" if self.stop_reason == "error" else None,
                               rate_limit=None, first_delta_sec=self.wait, duration_sec=self.wait,
                               context_tokens=0, output_tokens=0, tools=[])


async def _run_turn(server, h, monkeypatch, brain, after=0.3):
    monkeypatch.setattr(server, "brain_instance", brain)
    monkeypatch.setattr(server, "still_thinking_after", lambda: after)
    monkeypatch.setattr(server.hermes_brain, "use_hermes", lambda: True)

    async def no_rotate():
        return None
    monkeypatch.setattr(server, "_maybe_rotate", no_rotate)
    acker = asyncio.create_task(h.ack_all(rounds=60))
    await asyncio.wait_for(server._handle_utterance("Jax, what is two plus two?"), timeout=10)
    acker.cancel()


@pytest.mark.asyncio
async def test_a_slow_plain_turn_gets_the_line_then_the_answer(wired, monkeypatch):
    server, h, _ = wired
    await _run_turn(server, h, monkeypatch, SlowBrain(wait=0.6))
    assert _said(h) == [STILL, "Two plus two is four."]


@pytest.mark.asyncio
async def test_a_quick_plain_turn_gets_no_line(wired, monkeypatch):
    server, h, statuses = wired
    await _run_turn(server, h, monkeypatch, SlowBrain(wait=0.05))
    await asyncio.sleep(0.4)                           # past the threshold: the timer was cancelled
    assert _said(h) == ["Two plus two is four."]
    assert not any(m.get("label") == "Still thinking" for m in statuses)


@pytest.mark.asyncio
async def test_switch_off_means_no_line(wired, monkeypatch):
    server, h, _ = wired
    monkeypatch.setenv("JAX_STILL_THINKING", "0")
    await _run_turn(server, h, monkeypatch, SlowBrain(wait=0.6))
    assert _said(h) == ["Two plus two is four."]


@pytest.mark.asyncio
async def test_a_failed_brain_says_so_in_plain_words(wired, monkeypatch):
    server, h, _ = wired
    await _run_turn(server, h, monkeypatch, SlowBrain(wait=0.05, stop_reason="error"))
    await h.ack_all()
    assert _said(h) == ["Sorry, sir, I can't reach my brain right now."]


def test_threshold_default_and_floor(monkeypatch):
    import server
    monkeypatch.delenv("JAX_STILL_THINKING_SEC", raising=False)
    assert server.still_thinking_after() == 8.0
    monkeypatch.setenv("JAX_STILL_THINKING_SEC", "0.1")
    assert server.still_thinking_after() == 1.0
    monkeypatch.setenv("JAX_STILL_THINKING_SEC", "junk")
    assert server.still_thinking_after() == 8.0
    monkeypatch.delenv("JAX_STILL_THINKING", raising=False)
    assert server.still_thinking_enabled() is False     # off unless switched on


def test_test_delay_needs_the_phrase_and_the_file(monkeypatch, tmp_path):
    import server
    f = tmp_path / "delay"
    monkeypatch.setattr(server, "_TEST_BRAIN_DELAY_FILE", f)
    assert server._test_brain_delay("slow brain test, what is two plus two") == 0.0   # no file
    f.write_text("12")
    assert server._test_brain_delay("what is two plus two") == 0.0                     # no phrase
    assert server._test_brain_delay("Jax, slow brain test. Two plus two?") == 12.0
