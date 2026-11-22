import hermes_brain


def test_sse_parsing():
    hermes_brain.demo()


def test_off_by_default(monkeypatch):
    monkeypatch.delenv("JAX_BRAIN", raising=False)
    assert hermes_brain.use_hermes() is False
    monkeypatch.setenv("JAX_BRAIN", "Hermes")
    assert hermes_brain.use_hermes() is True


def _thread(tmp_path, now, **kw):
    kw.setdefault("rolling", True)
    return hermes_brain.VoiceThread("voice", tmp_path / "t.json", idle_sec=1800, max_tokens=60000,
                                    clock=lambda: now[0], **kw)


def test_single_thread_never_moves(tmp_path):
    now = [1000.0]
    t = _thread(tmp_path, now, rolling=False)
    t.before_turn()
    t.after_turn("hi", "hello", 999999, 0)
    now[0] += 99999
    t.before_turn()
    assert t.session == "voice" and t.system_message() is None
    assert not (tmp_path / "t.json").exists()


def test_rolling_thread_starts_new_when_quiet_or_big(tmp_path):
    now = [1_800_000_000.0]
    t = _thread(tmp_path, now)
    t.before_turn()
    first = t.session
    assert first.startswith("voice-") and t.system_message() is None
    t.after_turn("what is two plus two", "Four.", 27000, 0)
    now[0] += 60
    t.before_turn()
    assert t.session == first                      # still the same conversation
    now[0] += 1801
    t.before_turn()                                # quiet for half an hour
    second = t.session
    assert second != first
    assert "Drey: what is two plus two\nJax: Four." in t.system_message()["content"]
    recap = t.system_message()
    t.after_turn("look it up", "Done.", 180000, 2)  # three model calls of 60k each
    assert t.system_message() == recap             # the recap never changes inside a thread
    now[0] += 5
    t.before_turn()                                # too big: move on at once
    assert t.session not in (first, second)


def test_rolling_thread_survives_a_restart_and_start_fresh_forgets(tmp_path):
    now = [1_800_000_000.0]
    t = _thread(tmp_path, now)
    t.before_turn()
    t.after_turn("remember the word pineapple", "Noted.", 27000, 0)
    again = _thread(tmp_path, now)
    assert again.session == t.session and again.tail == t.tail
    now[0] += 2
    again.fresh(carry=False, why="start fresh")
    assert again.session != t.session and again.system_message() is None


def test_lookup_labels_are_plain_words():
    assert hermes_brain.lookup_label("session_search") == "Searching memory"
    assert hermes_brain.lookup_label("web_search") == "Searching the web"
    assert hermes_brain.lookup_label("terminal") == "Running a command"
    assert hermes_brain.lookup_label("something_new") == "Looking it up"
    line = 'data: {"tool": "terminal", "label": "date", "toolCallId": "c1", "status": "running"}'
    assert hermes_brain.sse_tool_started(line) and hermes_brain.sse_tool_name(line) == "terminal"
    assert hermes_brain.sse_tool_name("data: not json") == ""
