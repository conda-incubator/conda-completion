"""Tests for the main CLI parser and dispatch."""

from __future__ import annotations

import argparse

import msgpack
import pytest

from conda_completion.cli.main import build_parser, execute
from conda_completion.exceptions import ShellNotSupportedError


@pytest.mark.parametrize(
    "subcmd",
    ["generate", "refresh", "install", "uninstall", "init"],
)
def test_configure_parser_accepts_subcommand(subcmd):
    parser = build_parser()
    args = parser.parse_args([subcmd] if subcmd != "init" else [subcmd, "bash"])
    assert args.subcmd == subcmd


def test_configure_parser_install_flags():
    parser = build_parser()
    args = parser.parse_args(["install", "--yes", "--dry-run", "--no-repodata", "zsh"])
    assert args.subcmd == "install"
    assert args.yes is True
    assert args.dry_run is True
    assert args.no_repodata is True
    assert args.shell == "zsh"


def test_configure_parser_cache_dir_option():
    parser = build_parser()
    args = parser.parse_args(["--cache-dir", "/tmp/conda-completion-cache", "generate"])
    assert args.cache_dir == "/tmp/conda-completion-cache"
    assert args.subcmd == "generate"


def test_configure_parser_generate_no_repodata_flag():
    parser = build_parser()
    args = parser.parse_args(["generate", "--no-repodata"])
    assert args.subcmd == "generate"
    assert args.no_repodata is True


def test_configure_parser_json_flag_is_suppressed():
    parser = build_parser()
    args = parser.parse_args(["--json", "generate"])
    assert args.json is True


@pytest.mark.parametrize("quiet_flag", ["--quiet", "-q"])
def test_configure_parser_quiet_flag_is_suppressed(quiet_flag):
    parser = build_parser()
    args = parser.parse_args([quiet_flag, "generate"])
    assert args.quiet is True


def test_execute_no_subcommand(capsys):
    args = build_parser().parse_args([])
    result = execute(args)
    assert result == 0
    captured = capsys.readouterr()
    assert "usage" in captured.out.lower() or "conda completion" in captured.out.lower()


def test_execute_dispatches_generate(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "conda_completion.paths.manifest_path",
        lambda: tmp_path / "completion.msgpack",
    )
    monkeypatch.setattr(
        "conda_completion.paths.completion_cache_dir",
        lambda: tmp_path,
    )

    args = build_parser().parse_args(["generate"])
    result = execute(args)
    assert result == 0
    assert (tmp_path / "completion.msgpack").exists()


def test_execute_dispatches_refresh(monkeypatch):
    calls = []

    def record_refresh(args):
        calls.append(args)
        return 0

    monkeypatch.setattr(
        "conda_completion.cli.refresh.execute_refresh",
        record_refresh,
    )

    args = build_parser().parse_args(["refresh"])
    result = execute(args)
    assert result == 0
    assert calls == [args]


def test_execute_handles_completion_error(monkeypatch):
    def raise_error(args):
        raise ShellNotSupportedError("nushell", ["bash", "zsh"])

    monkeypatch.setattr("conda_completion.cli.init.execute_init", raise_error)

    args = build_parser().parse_args(["init", "nushell"])
    result = execute(args)
    assert result == 1


def test_execute_dispatches_status(tmp_path, capsys):
    manifest = tmp_path / "completion.msgpack"
    manifest.write_bytes(msgpack.packb({"version": 1, "commands": {}}))

    args = build_parser().parse_args(["--cache-dir", str(tmp_path), "status"])
    result = execute(args)
    assert result == 0
    assert "Manifest:" in capsys.readouterr().out


def test_execute_applies_cache_dir_override(tmp_path, capsys):
    cache_dir = tmp_path / "custom-cache"
    args = build_parser().parse_args(["--cache-dir", str(cache_dir), "status"])

    result = execute(args)

    assert result == 0
    assert f"Cache directory: {cache_dir}" in capsys.readouterr().out


def test_execute_dispatches_install(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "conda_completion.cli.generate.execute_generate",
        lambda args: 0,
    )
    monkeypatch.setattr("conda_completion.cli.install.Shell.detect_shell", lambda: "bash")
    rc_file = tmp_path / ".bashrc"
    monkeypatch.setattr(
        "conda_completion.shell.bash.BashShell.default_rc_path",
        lambda self: rc_file,
    )

    args = build_parser().parse_args(["install", "--yes"])
    result = execute(args)
    assert result == 0


def test_execute_dispatches_uninstall(tmp_path, monkeypatch):
    monkeypatch.setattr("conda_completion.cli.uninstall.Shell.detect_shell", lambda: "bash")
    rc_file = tmp_path / ".bashrc"
    rc_file.write_text("nothing here\n", encoding="utf-8")
    monkeypatch.setattr(
        "conda_completion.shell.bash.BashShell.default_rc_path",
        lambda self: rc_file,
    )

    args = build_parser().parse_args(["uninstall", "--yes"])
    result = execute(args)
    assert result == 0


def test_execute_unknown_subcommand(capsys):
    result = execute(argparse.Namespace(subcmd="bogus"))
    assert result == 1
    assert "usage" in capsys.readouterr().out.lower()
