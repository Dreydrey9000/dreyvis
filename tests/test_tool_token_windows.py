"""The tool token's Windows path: adopt a plain file, refuse a link."""

import os

import pytest

import data_paths


def test_adopts_existing_token(tmp_path):
    p = tmp_path / "tool-token"
    p.write_text("kept-token\n")
    assert data_paths._adopt_tool_token_windows(p, "new") == "kept-token"


def test_fills_an_empty_file(tmp_path):
    p = tmp_path / "tool-token"
    p.write_text("")
    assert data_paths._adopt_tool_token_windows(p, "fresh") == "fresh"
    assert p.read_text() == "fresh"


def test_refuses_a_link(tmp_path):
    target = tmp_path / "someone-elses-file"
    target.write_text("not yours")
    link = tmp_path / "tool-token"
    try:
        os.symlink(target, link)
    except (OSError, NotImplementedError):
        pytest.skip("this account cannot make symlinks")
    with pytest.raises(OSError):
        data_paths._adopt_tool_token_windows(link, "new")
    assert target.read_text() == "not yours"
