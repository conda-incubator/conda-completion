"""Tests for the main CLI parser and dispatch."""

from __future__ import annotations

import pytest

from conda_completion.cli.main import configure_parser, execute


@pytest.mark.parametrize(
    "subcmd",
    ["generate", "install", "uninstall", "init"],
)
def test_configure_parser_accepts_subcommand(subcmd):
    parser = configure_parser()
    args = parser.parse_args([subcmd] if subcmd != "init" else [subcmd, "bash"])
    assert args.subcmd == subcmd


def test_configure_parser_install_flags():
    parser = configure_parser()
    args = parser.parse_args(["install", "--yes", "--dry-run", "zsh"])
    assert args.subcmd == "install"
    assert args.yes is True
    assert args.dry_run is True
    assert args.shell == "zsh"


def test_configure_parser_json_flag_is_suppressed():
    parser = configure_parser()
    args = parser.parse_args(["--json", "generate"])
    assert args.json is True


def test_execute_no_subcommand(capsys):
    args = configure_parser().parse_args([])
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

    args = configure_parser().parse_args(["generate"])
    result = execute(args)
    assert result == 0
    assert (tmp_path / "completion.msgpack").exists()


def test_execute_handles_completion_error(monkeypatch):
    from conda_completion.exceptions import ShellNotSupportedError

    def raise_error(args):
        raise ShellNotSupportedError("nushell", ["bash", "zsh"])

    monkeypatch.setattr("conda_completion.cli.init.execute_init", raise_error)

    args = configure_parser().parse_args(["init", "nushell"])
    result = execute(args)
    assert result == 1


def test_execute_dispatches_status(tmp_path, monkeypatch, capsys):
    import msgpack

    manifest = tmp_path / "completion.msgpack"
    manifest.write_bytes(msgpack.packb({"version": 1, "commands": {}}))
    monkeypatch.setattr("conda_completion.paths.manifest_path", lambda: manifest)
    monkeypatch.setattr("conda_completion.paths.versions_path", lambda: tmp_path / "v.msgpack")
    monkeypatch.setattr("conda_completion.paths.completion_cache_dir", lambda: tmp_path)

    args = configure_parser().parse_args(["status"])
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

    args = configure_parser().parse_args(["install", "--yes"])
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

    args = configure_parser().parse_args(["uninstall", "--yes"])
    result = execute(args)
    assert result == 0


def test_main_entry_point(monkeypatch):
    monkeypatch.setattr(
        "conda_completion.paths.manifest_path",
        lambda: pytest.importorskip("pathlib").Path("/tmp/cc-test-main/completion.msgpack"),
    )
    monkeypatch.setattr(
        "conda_completion.paths.completion_cache_dir",
        lambda: pytest.importorskip("pathlib").Path("/tmp/cc-test-main"),
    )

    from conda_completion.__main__ import main

    with pytest.raises(SystemExit) as exc_info:
        main(["generate"])
    assert exc_info.value.code == 0
