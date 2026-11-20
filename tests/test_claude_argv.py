"""claude_argv: the Claude Code path as the start of a command, on Mac and Windows."""

from claude_env import claude_argv


def test_unix_still_splits_like_a_shell():
    assert claude_argv("node /opt/x/cli.js", windows=False) == ["node", "/opt/x/cli.js"]


def test_windows_keeps_backslashes():
    # Regression, 2026-11-20: shlex.split turned this into "C:UsersPC..." and
    # the brain could not start on the closet PC (WinError 2).
    path = r"C:\Users\PC\Tools\claude.exe"
    assert claude_argv(path, windows=True) == [path]


def test_windows_npm_shim_runs_the_real_exe(tmp_path):
    shim = tmp_path / "claude.CMD"
    shim.write_text("@ECHO off\n")
    exe = tmp_path / "node_modules" / "@anthropic-ai" / "claude-code" / "bin" / "claude.exe"
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"MZ")
    assert claude_argv(str(shim), windows=True) == [str(exe)]


def test_windows_shim_without_exe_is_left_alone(tmp_path):
    shim = tmp_path / "claude.cmd"
    shim.write_text("@ECHO off\n")
    assert claude_argv(str(shim), windows=True) == [str(shim)]
