"""Tests for the uninstall CLI subcommand."""

from __future__ import annotations

import argparse

import pytest

from conda_completion.cli.install import _BLOCK_END, _BLOCK_START
from conda_completion.cli.uninstall import _BLOCK_PATTERN, execute_uninstall
from conda_completion.exceptions import ShellNotSupportedError


def test_uninstall_removes_block(tmp_path):
    rc_file = tmp_path / ".bashrc"
    rc_file.write_text(
        'export PATH="/usr/bin:$PATH"\n'
        f"\n{_BLOCK_START}\n"
        'command -v conda &>/dev/null && eval "$(conda completion init bash)"\n'
        f"{_BLOCK_END}\n"
        "\nalias ll='ls -la'\n",
        encoding="utf-8",
    )

    content = rc_file.read_text(encoding="utf-8")
    new_content = _BLOCK_PATTERN.sub("", content)
    rc_file.write_text(new_content, encoding="utf-8")

    result = rc_file.read_text(encoding="utf-8")
    assert _BLOCK_START not in result
    assert _BLOCK_END not in result
    assert 'export PATH="/usr/bin:$PATH"' in result
    assert "alias ll='ls -la'" in result


def test_execute_uninstall_unsupported_shell(monkeypatch):
    monkeypatch.setattr("conda_completion.cli.uninstall.Shell.detect_shell", lambda: "nushell")
    args = argparse.Namespace(shell=None, yes=True, dry_run=False)
    with pytest.raises(ShellNotSupportedError):
        execute_uninstall(args)


def test_execute_uninstall_no_rc_file(monkeypatch):
    monkeypatch.setattr("conda_completion.cli.uninstall.Shell.detect_shell", lambda: "bash")
    monkeypatch.setattr(
        "conda_completion.shell.bash.BashShell.default_rc_path",
        lambda self: None,
    )

    args = argparse.Namespace(shell=None, yes=True, dry_run=False)
    result = execute_uninstall(args)
    assert result == 0


def test_execute_uninstall_no_hook_in_file(tmp_path, monkeypatch):
    rc_file = tmp_path / ".bashrc"
    rc_file.write_text("alias ll='ls -la'\n", encoding="utf-8")
    monkeypatch.setattr("conda_completion.cli.uninstall.Shell.detect_shell", lambda: "bash")
    monkeypatch.setattr(
        "conda_completion.shell.bash.BashShell.default_rc_path",
        lambda self: rc_file,
    )

    args = argparse.Namespace(shell=None, yes=True, dry_run=False)
    result = execute_uninstall(args)
    assert result == 0
    assert rc_file.read_text(encoding="utf-8") == "alias ll='ls -la'\n"


def test_execute_uninstall_dry_run(tmp_path, monkeypatch):
    rc_file = tmp_path / ".bashrc"
    original = f"# before\n\n{_BLOCK_START}\nhook line\n{_BLOCK_END}\n\n# after\n"
    rc_file.write_text(original, encoding="utf-8")
    monkeypatch.setattr("conda_completion.cli.uninstall.Shell.detect_shell", lambda: "bash")
    monkeypatch.setattr(
        "conda_completion.shell.bash.BashShell.default_rc_path",
        lambda self: rc_file,
    )

    args = argparse.Namespace(shell=None, yes=False, dry_run=True)
    result = execute_uninstall(args)
    assert result == 0
    assert rc_file.read_text(encoding="utf-8") == original


def test_execute_uninstall_prompt_declined(tmp_path, monkeypatch):
    rc_file = tmp_path / ".bashrc"
    original = f"# before\n\n{_BLOCK_START}\nhook line\n{_BLOCK_END}\n\n# after\n"
    rc_file.write_text(original, encoding="utf-8")
    monkeypatch.setattr("conda_completion.cli.uninstall.Shell.detect_shell", lambda: "bash")
    monkeypatch.setattr(
        "conda_completion.shell.bash.BashShell.default_rc_path",
        lambda self: rc_file,
    )
    monkeypatch.setattr("builtins.input", lambda _: "n")

    args = argparse.Namespace(shell=None, yes=False, dry_run=False)
    result = execute_uninstall(args)
    assert result == 1
    assert rc_file.read_text(encoding="utf-8") == original


def test_execute_uninstall_removes_hook(tmp_path, monkeypatch):
    rc_file = tmp_path / ".bashrc"
    rc_file.write_text(
        f"# before\n\n{_BLOCK_START}\nhook line\n{_BLOCK_END}\n\n# after\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("conda_completion.cli.uninstall.Shell.detect_shell", lambda: "bash")
    monkeypatch.setattr(
        "conda_completion.shell.bash.BashShell.default_rc_path",
        lambda self: rc_file,
    )

    args = argparse.Namespace(shell=None, yes=True, dry_run=False)
    result = execute_uninstall(args)
    assert result == 0
    content = rc_file.read_text(encoding="utf-8")
    assert _BLOCK_START not in content
    assert _BLOCK_END not in content
    assert "# before" in content
    assert "# after" in content
