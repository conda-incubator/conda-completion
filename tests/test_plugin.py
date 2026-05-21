"""Tests for plugin registration and manifest regeneration."""

from __future__ import annotations

import pytest

from conda_completion.plugin import (
    _maybe_regenerate,
    _read_manifest_plugin_hash,
    plugin_entry_point_hash,
)


def test_plugin_entry_point_hash_is_deterministic():
    h1 = plugin_entry_point_hash()
    h2 = plugin_entry_point_hash()
    assert h1 == h2
    assert len(h1) == 16


def test_plugin_entry_point_hash_is_hex():
    h = plugin_entry_point_hash()
    int(h, 16)


def test_read_manifest_plugin_hash_double_quoted(tmp_path):
    manifest = tmp_path / "completion.toml"
    manifest.write_text('plugin_hash = "abc123"\n', encoding="utf-8")
    assert _read_manifest_plugin_hash(manifest) == "abc123"


def test_read_manifest_plugin_hash_single_quoted(tmp_path):
    manifest = tmp_path / "completion.toml"
    manifest.write_text("plugin_hash = 'def456'\n", encoding="utf-8")
    assert _read_manifest_plugin_hash(manifest) == "def456"


def test_read_manifest_plugin_hash_missing_field(tmp_path):
    manifest = tmp_path / "completion.toml"
    manifest.write_text("version = 1\n", encoding="utf-8")
    assert _read_manifest_plugin_hash(manifest) is None


def test_read_manifest_plugin_hash_missing_file(tmp_path):
    manifest = tmp_path / "nonexistent.toml"
    assert _read_manifest_plugin_hash(manifest) is None


def test_maybe_regenerate_no_manifest(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "conda_completion.paths.manifest_path",
        lambda: tmp_path / "nope.toml",
    )
    _maybe_regenerate("install")


def test_maybe_regenerate_hash_matches(tmp_path, monkeypatch):
    current_hash = plugin_entry_point_hash()
    manifest = tmp_path / "completion.toml"
    manifest.write_text(f'plugin_hash = "{current_hash}"\n', encoding="utf-8")
    monkeypatch.setattr("conda_completion.paths.manifest_path", lambda: manifest)
    _maybe_regenerate("install")
    assert manifest.read_text(encoding="utf-8").count(current_hash) == 1


def test_maybe_regenerate_hash_differs(tmp_path, monkeypatch):
    manifest = tmp_path / "completion.toml"
    manifest.write_text('plugin_hash = "stale_hash"\n', encoding="utf-8")
    monkeypatch.setattr("conda_completion.paths.manifest_path", lambda: manifest)

    generated = []
    written = []

    def fake_generate(plugin_hash):
        from conda_completion.manifest import CompletionManifest

        generated.append(plugin_hash)
        return CompletionManifest(plugin_hash=plugin_hash)

    def fake_write(m, path):
        written.append(path)

    monkeypatch.setattr("conda_completion.introspect.generate_manifest", fake_generate)
    monkeypatch.setattr("conda_completion.manifest.write_manifest", fake_write)

    _maybe_regenerate("install")

    assert len(generated) == 1
    assert len(written) == 1


def test_maybe_regenerate_permission_error(tmp_path, monkeypatch):
    manifest = tmp_path / "completion.toml"
    manifest.write_text('plugin_hash = "x"\n', encoding="utf-8")
    monkeypatch.setattr("conda_completion.paths.manifest_path", lambda: manifest)

    def raise_permission_error():
        raise PermissionError("denied")

    monkeypatch.setattr(
        "conda_completion.plugin.plugin_entry_point_hash",
        raise_permission_error,
    )
    _maybe_regenerate("install")


def test_maybe_regenerate_os_error(monkeypatch):
    def raise_os_error():
        raise OSError("disk full")

    monkeypatch.setattr(
        "conda_completion.paths.manifest_path",
        raise_os_error,
    )
    _maybe_regenerate("install")


def test_maybe_regenerate_generic_error(monkeypatch):
    def raise_runtime_error():
        raise RuntimeError("oops")

    monkeypatch.setattr(
        "conda_completion.paths.manifest_path",
        raise_runtime_error,
    )
    _maybe_regenerate("install")


@pytest.mark.parametrize("command", ["install", "remove", "update"])
def test_post_command_hook_yields_correct_run_for(command):
    from conda_completion.plugin import conda_post_commands

    hooks = list(conda_post_commands())
    assert len(hooks) == 1
    assert command in hooks[0].run_for


def test_subcommands_hook_yields_completion():
    from conda_completion.plugin import conda_subcommands

    cmds = list(conda_subcommands())
    assert len(cmds) == 1
    assert cmds[0].name == "completion"
