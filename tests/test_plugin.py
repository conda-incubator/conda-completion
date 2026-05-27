"""Tests for plugin registration and manifest regeneration."""

from __future__ import annotations

import argparse

import msgpack
import pytest

from conda_completion.manifest import CompletionManifest
from conda_completion.plugin import (
    conda_post_commands,
    conda_subcommands,
    maybe_regenerate,
    plugin_entry_point_hash,
    read_manifest_plugin_hash,
)


def write_msgpack_manifest(path, plugin_hash):
    """Write a minimal msgpack manifest with the given plugin_hash."""
    data = {"version": 1, "plugin_hash": plugin_hash, "commands": {}}
    path.write_bytes(msgpack.packb(data))


def test_plugin_entry_point_hash_is_deterministic():
    h1 = plugin_entry_point_hash()
    h2 = plugin_entry_point_hash()
    assert h1 == h2
    assert len(h1) == 16


def test_plugin_entry_point_hash_is_hex():
    h = plugin_entry_point_hash()
    int(h, 16)


def test_read_manifest_plugin_hash(tmp_path):
    manifest = tmp_path / "completion.msgpack"
    write_msgpack_manifest(manifest, "abc123")
    assert read_manifest_plugin_hash(manifest) == "abc123"


def test_read_manifest_plugin_hash_missing_field(tmp_path):
    manifest = tmp_path / "completion.msgpack"
    manifest.write_bytes(msgpack.packb({"version": 1}))
    assert read_manifest_plugin_hash(manifest) is None


def test_read_manifest_plugin_hash_missing_file(tmp_path):
    manifest = tmp_path / "nonexistent.msgpack"
    assert read_manifest_plugin_hash(manifest) is None


def test_maybe_regenerate_no_manifest(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "conda_completion.paths.manifest_path",
        lambda: tmp_path / "nope.msgpack",
    )
    maybe_regenerate("install")


def test_maybe_regenerate_hash_matches(tmp_path, monkeypatch):
    current_hash = plugin_entry_point_hash()
    manifest = tmp_path / "completion.msgpack"
    write_msgpack_manifest(manifest, current_hash)
    monkeypatch.setattr("conda_completion.paths.manifest_path", lambda: manifest)
    maybe_regenerate("install")
    data = msgpack.unpackb(manifest.read_bytes())
    assert data["plugin_hash"] == current_hash


def test_maybe_regenerate_hash_differs(tmp_path, monkeypatch):
    manifest = tmp_path / "completion.msgpack"
    write_msgpack_manifest(manifest, "stale_hash")
    monkeypatch.setattr("conda_completion.paths.manifest_path", lambda: manifest)

    generated = []
    written = []

    def fake_generate(plugin_hash):
        generated.append(plugin_hash)
        return CompletionManifest(plugin_hash=plugin_hash)

    def fake_write(m, path):
        written.append(path)

    def fake_resolve_package_metadata(manifest, **kwargs):
        return manifest

    monkeypatch.setattr("conda_completion.introspect.generate_manifest", fake_generate)
    monkeypatch.setattr("conda_completion.manifest.write_manifest", fake_write)
    monkeypatch.setattr(
        "conda_completion.cli.generate.resolve_package_metadata",
        fake_resolve_package_metadata,
    )

    maybe_regenerate("install")

    assert len(generated) == 1
    assert len(written) == 1


@pytest.mark.parametrize(
    "target,exc_class,exc_msg",
    [
        ("conda_completion.plugin.plugin_entry_point_hash", PermissionError, "denied"),
        ("conda_completion.paths.manifest_path", OSError, "disk full"),
        ("conda_completion.paths.manifest_path", RuntimeError, "oops"),
        ("conda_completion.paths.manifest_path", BaseException, "panic"),
    ],
    ids=["permission-error", "os-error", "generic-error", "base-exception"],
)
def test_maybe_regenerate_swallows_errors(tmp_path, monkeypatch, target, exc_class, exc_msg):
    if target == "conda_completion.plugin.plugin_entry_point_hash":
        manifest = tmp_path / "completion.msgpack"
        write_msgpack_manifest(manifest, "x")
        monkeypatch.setattr("conda_completion.paths.manifest_path", lambda: manifest)

    def raiser():
        raise exc_class(exc_msg)

    monkeypatch.setattr(target, raiser)
    maybe_regenerate("install")


@pytest.mark.parametrize("exc_class", [KeyboardInterrupt, SystemExit], ids=["interrupt", "exit"])
def test_maybe_regenerate_preserves_interrupts(monkeypatch, exc_class):
    def raiser():
        raise exc_class

    monkeypatch.setattr("conda_completion.paths.manifest_path", raiser)

    with pytest.raises(exc_class):
        maybe_regenerate("install")


@pytest.mark.parametrize("command", ["install", "remove", "update"])
def test_post_command_hook_yields_correct_run_for(command):
    hooks = list(conda_post_commands())
    assert len(hooks) == 1
    assert command in hooks[0].run_for


def test_subcommands_hook_yields_completion():
    cmds = list(conda_subcommands())
    assert len(cmds) == 1
    assert cmds[0].name == "completion"


def test_subcommands_hook_configures_parser():
    cmd = next(iter(conda_subcommands()))
    parser = argparse.ArgumentParser()

    assert cmd.configure_parser is not None
    assert cmd.configure_parser(parser) is None
    assert parser.parse_args(["generate"]).subcmd == "generate"
    assert parser.parse_args(["refresh"]).subcmd == "refresh"
    assert parser.parse_args(["install", "bash"]).subcmd == "install"
