"""Tests for the status CLI subcommand."""

from __future__ import annotations

import argparse
import os
import time

import msgpack
import pytest

from conda_completion.cli.status import execute_status


@pytest.fixture()
def status_env(tmp_path, monkeypatch):
    """Stub out path helpers and return a helper to create manifests."""
    monkeypatch.setattr("conda_completion.cli.status.completion_cache_dir", lambda: tmp_path)
    monkeypatch.setattr(
        "conda_completion.cli.status.manifest_path",
        lambda: tmp_path / "completion.msgpack",
    )
    monkeypatch.setattr(
        "conda_completion.cli.status.versions_index_path",
        lambda: tmp_path / "versions.index",
    )
    monkeypatch.setattr(
        "conda_completion.cli.status.versions_store_path",
        lambda: tmp_path / "versions.store",
    )
    monkeypatch.setattr("conda_completion.cli.status.plugin_entry_point_hash", lambda: "current")

    class Env:
        root = tmp_path

        @staticmethod
        def write_manifest(data=None):
            path = tmp_path / "completion.msgpack"
            path.write_bytes(msgpack.packb(data or {"version": 1, "commands": {}}))
            return path

    return Env()


def test_status_no_manifest(status_env, capsys):
    result = execute_status(argparse.Namespace())

    assert result == 0
    out = capsys.readouterr().out
    assert "Not found" in out
    assert str(status_env.root) in out


def test_status_with_manifest(status_env, capsys):
    status_env.write_manifest(
        {
            "version": 1,
            "generated_at": "2025-01-01T00:00:00Z",
            "plugin_hash": "abc123",
            "commands": {"install": {"summary": "Install"}},
            "package_names": ["numpy", "pandas"],
        }
    )

    result = execute_status(argparse.Namespace())

    assert result == 0
    out = capsys.readouterr().out
    assert "Commands: 1" in out
    assert "Packages: 2" in out
    assert "abc123" in out
    assert "Last generated:" in out


def test_status_with_corrupt_manifest(status_env, capsys):
    path = status_env.root / "completion.msgpack"
    path.write_bytes(b"\xff\xfe invalid")

    result = execute_status(argparse.Namespace())

    assert result == 0
    assert "Error reading manifest" in capsys.readouterr().out


@pytest.mark.parametrize(
    "age_seconds,expected_label",
    [
        (30, "minutes ago"),
        (7200, "hours ago"),
        (259200, "days ago"),
    ],
    ids=["minutes", "hours", "days"],
)
def test_status_manifest_age(status_env, capsys, age_seconds, expected_label):
    path = status_env.write_manifest()
    mtime = time.time() - age_seconds
    os.utime(path, (mtime, mtime))

    result = execute_status(argparse.Namespace())

    assert result == 0
    assert expected_label in capsys.readouterr().out


def test_status_with_versions(status_env, capsys):
    status_env.write_manifest()
    record = msgpack.packb(["1.0"])
    (status_env.root / "versions.index").write_bytes(msgpack.packb({"numpy": (0, len(record))}))
    (status_env.root / "versions.store").write_bytes(record)

    result = execute_status(argparse.Namespace())

    assert result == 0
    out = capsys.readouterr().out
    assert "Package versions index:" in out
    assert "Package versions store:" in out
    assert "Size:" in out


def test_status_no_versions(status_env, capsys):
    status_env.write_manifest()

    result = execute_status(argparse.Namespace())

    assert result == 0
    out = capsys.readouterr().out
    assert "Package versions index:" in out
    assert "Package versions store:" in out
    assert "Not found" in out


def test_status_completer_binary_shown(status_env, tmp_path, monkeypatch, capsys):
    status_env.write_manifest()
    binary = tmp_path / "_conda_completer"
    monkeypatch.setattr("conda_completion.cli.status.find_completer_binary", lambda: binary)

    result = execute_status(argparse.Namespace())

    assert result == 0
    out = capsys.readouterr().out
    assert f"Completer binary: {binary}" in out


def test_status_completer_binary_missing(status_env, monkeypatch, capsys):
    status_env.write_manifest()

    def raise_not_found():
        raise FileNotFoundError

    monkeypatch.setattr("conda_completion.cli.status.find_completer_binary", raise_not_found)

    result = execute_status(argparse.Namespace())

    assert result == 0
    assert "Completer binary: not found" in capsys.readouterr().out
