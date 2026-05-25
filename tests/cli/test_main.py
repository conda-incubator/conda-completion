"""Tests for the main CLI parser and dispatch."""

from __future__ import annotations

import msgpack
import pytest

from conda_completion.cli.main import build_parser, execute
from conda_completion.exceptions import ShellNotSupportedError


@pytest.mark.parametrize(
    "subcmd",
    ["generate", "install", "uninstall", "init"],
)
def test_configure_parser_accepts_subcommand(subcmd):
    parser = build_parser()
    args = parser.parse_args([subcmd] if subcmd != "init" else [subcmd, "bash"])
    assert args.subcmd == subcmd


def test_configure_parser_install_flags():
    parser = build_parser()
    args = parser.parse_args(["install", "--yes", "--dry-run", "zsh"])
    assert args.subcmd == "install"
    assert args.yes is True
    assert args.dry_run is True
    assert args.shell == "zsh"


def test_configure_parser_json_flag_is_suppressed():
    parser = build_parser()
    args = parser.parse_args(["--json", "generate"])
    assert args.json is True


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


def test_execute_handles_completion_error(monkeypatch):
    def raise_error(args):
        raise ShellNotSupportedError("nushell", ["bash", "zsh"])

    monkeypatch.setattr("conda_completion.cli.init.execute_init", raise_error)

    args = build_parser().parse_args(["init", "nushell"])
    result = execute(args)
    assert result == 1


def test_execute_dispatches_status(tmp_path, monkeypatch, capsys):
    manifest = tmp_path / "completion.msgpack"
    manifest.write_bytes(msgpack.packb({"version": 1, "commands": {}}))
    monkeypatch.setattr("conda_completion.paths.manifest_path", lambda: manifest)
    monkeypatch.setattr("conda_completion.paths.versions_index_path", lambda: tmp_path / "v.index")
    monkeypatch.setattr("conda_completion.paths.versions_store_path", lambda: tmp_path / "v.store")
    monkeypatch.setattr("conda_completion.paths.completion_cache_dir", lambda: tmp_path)

    args = build_parser().parse_args(["status"])
    result = execute(args)
    assert result == 0
    assert "Manifest:" in capsys.readouterr().out


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
