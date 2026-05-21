"""Tests for the init CLI subcommand."""

from __future__ import annotations

import argparse

import pytest

from conda_completion.cli.init import execute_init
from conda_completion.exceptions import (
    CompleterBinaryNotFoundError,
    ManifestNotFoundError,
    ShellNotSupportedError,
)


@pytest.fixture()
def manifest_file(tmp_path, monkeypatch):
    manifest = tmp_path / "completion.toml"
    manifest.write_text("version = 1\n", encoding="utf-8")
    monkeypatch.setattr("conda_completion.cli.init.manifest_path", lambda: manifest)
    return manifest


@pytest.fixture()
def completer_binary(tmp_path, monkeypatch):
    binary = tmp_path / "_conda_completer"
    binary.touch()
    monkeypatch.setattr("conda_completion.cli.init.find_completer_binary", lambda: binary)
    return binary


@pytest.mark.parametrize(
    "shell,expected",
    [
        ("bash", "_conda_completion"),
        ("zsh", "#compdef conda"),
        ("powershell", "Register-ArgumentCompleter"),
        ("fish", "__conda_complete"),
    ],
    ids=["bash", "zsh", "powershell", "fish"],
)
def test_execute_init_prints_script(manifest_file, completer_binary, shell, expected, capsys):
    args = argparse.Namespace(shell=shell)
    result = execute_init(args)

    assert result == 0
    captured = capsys.readouterr()
    assert expected in captured.out
    assert completer_binary.as_posix() in captured.out


def test_execute_init_embeds_manifest_path(manifest_file, completer_binary, capsys):
    args = argparse.Namespace(shell="bash")
    execute_init(args)

    captured = capsys.readouterr()
    assert manifest_file.as_posix() in captured.out


def test_execute_init_unsupported_shell(manifest_file, completer_binary):
    args = argparse.Namespace(shell="nushell")
    with pytest.raises(ShellNotSupportedError):
        execute_init(args)


def test_execute_init_missing_manifest(tmp_path, monkeypatch, completer_binary):
    monkeypatch.setattr(
        "conda_completion.cli.init.manifest_path",
        lambda: tmp_path / "nonexistent.toml",
    )
    args = argparse.Namespace(shell="bash")
    with pytest.raises(ManifestNotFoundError):
        execute_init(args)


def test_execute_init_missing_binary(manifest_file, monkeypatch):
    def raise_fnf():
        raise FileNotFoundError("not found")

    monkeypatch.setattr("conda_completion.cli.init.find_completer_binary", raise_fnf)
    args = argparse.Namespace(shell="bash")
    with pytest.raises(CompleterBinaryNotFoundError):
        execute_init(args)
