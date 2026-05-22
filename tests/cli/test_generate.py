"""Tests for the generate CLI subcommand."""

from __future__ import annotations

import argparse

from conda_completion.cli.generate import execute_generate
from conda_completion.manifest import read_manifest


def test_generate_creates_manifest(tmp_path, monkeypatch):
    manifest_path = tmp_path / "completion.msgpack"
    monkeypatch.setattr(
        "conda_completion.paths.completion_cache_dir",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "conda_completion.paths.manifest_path",
        lambda: manifest_path,
    )

    args = argparse.Namespace()
    result = execute_generate(args)

    assert result == 0
    assert manifest_path.exists()

    manifest = read_manifest(manifest_path)
    assert manifest.version == 1
    assert manifest.plugin_hash != ""
    assert len(manifest.commands) > 0
    assert "install" in manifest.commands
    assert "create" in manifest.commands
