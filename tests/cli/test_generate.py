"""Tests for the generate CLI subcommand."""

from __future__ import annotations

import argparse
import os
import time
from contextlib import nullcontext

import pytest

from conda_completion.cli.generate import (
    execute_generate,
    package_data_is_fresh,
    resolve_package_metadata,
    write_completion_data,
)
from conda_completion.manifest import (
    CompletionManifest,
    read_manifest,
    write_manifest,
    write_versions,
)


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


@pytest.fixture()
def generate_env(tmp_path, monkeypatch):
    manifest_path = tmp_path / "completion.msgpack"
    monkeypatch.setattr(
        "conda_completion.paths.completion_cache_dir",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "conda_completion.paths.manifest_path",
        lambda: manifest_path,
    )

    class Env:
        pass

    env = Env()
    env.root = tmp_path
    env.manifest_path = manifest_path
    env.versions_index_path = tmp_path / "versions.index"
    env.versions_store_path = tmp_path / "versions.store"
    return env


def test_generate_reuses_fresh_package_data(generate_env, monkeypatch):
    write_manifest(CompletionManifest(package_names=["numpy"]), generate_env.manifest_path)
    write_versions(
        {"numpy": ["2.0"]},
        generate_env.versions_index_path,
        generate_env.versions_store_path,
    )

    def fail_extract():
        raise AssertionError("repodata should not be fetched")

    monkeypatch.setattr("conda_completion.cli.generate.extract_package_data", fail_extract)

    result = execute_generate(argparse.Namespace(no_repodata=False))

    assert result == 0
    assert read_manifest(generate_env.manifest_path).package_names == ["numpy"]


def test_write_completion_data_refresh_forces_repodata_fetch(generate_env, monkeypatch):
    write_manifest(CompletionManifest(package_names=["numpy"]), generate_env.manifest_path)
    write_versions(
        {"numpy": ["2.0"]},
        generate_env.versions_index_path,
        generate_env.versions_store_path,
    )
    calls = []

    def fake_extract():
        calls.append(True)
        return ["pandas"], {"pandas": ["2.2"]}

    monkeypatch.setattr("conda_completion.cli.generate.extract_package_data", fake_extract)

    result = write_completion_data(argparse.Namespace(), refresh=True, include=True)

    assert result == 0
    assert calls == [True]
    assert read_manifest(generate_env.manifest_path).package_names == ["pandas"]


def test_generate_shows_repodata_spinner(generate_env, monkeypatch):
    spinner_messages = []

    class ContextStub:
        quiet = False
        json = False

    def fake_extract():
        return ["pandas"], {"pandas": ["2.2"]}

    def fake_spinner(message):
        spinner_messages.append(message)
        return nullcontext()

    monkeypatch.setattr("conda_completion.cli.generate.context", ContextStub())
    monkeypatch.setattr("conda_completion.cli.generate.extract_package_data", fake_extract)
    monkeypatch.setattr("conda_completion.cli.generate.get_spinner", fake_spinner)

    result = resolve_package_metadata(
        CompletionManifest(),
        existing_manifest_path=generate_env.manifest_path,
    )

    assert result.package_names == ["pandas"]
    assert spinner_messages == ["Collecting package metadata for completions"]


@pytest.mark.parametrize(("quiet", "json_enabled"), [(True, False), (False, True)])
def test_generate_suppresses_repodata_spinner_for_quiet_or_json(
    generate_env,
    monkeypatch,
    quiet,
    json_enabled,
):
    class ContextStub:
        json = json_enabled

    ContextStub.quiet = quiet

    def fake_extract():
        return ["pandas"], {"pandas": ["2.2"]}

    def fail_spinner(message):
        raise AssertionError(f"spinner should not be shown: {message}")

    monkeypatch.setattr("conda_completion.cli.generate.context", ContextStub())
    monkeypatch.setattr("conda_completion.cli.generate.extract_package_data", fake_extract)
    monkeypatch.setattr("conda_completion.cli.generate.get_spinner", fail_spinner)

    result = resolve_package_metadata(
        CompletionManifest(),
        existing_manifest_path=generate_env.manifest_path,
    )

    assert result.package_names == ["pandas"]


@pytest.mark.parametrize(("quiet", "json_enabled"), [(True, False), (False, True)])
def test_execute_generate_suppresses_repodata_spinner_for_output_flags(
    generate_env,
    monkeypatch,
    quiet,
    json_enabled,
):
    def fake_extract():
        return ["pandas"], {"pandas": ["2.2"]}

    def fail_spinner(message):
        raise AssertionError(f"spinner should not be shown: {message}")

    monkeypatch.setattr("conda_completion.cli.generate.extract_package_data", fake_extract)
    monkeypatch.setattr("conda_completion.cli.generate.get_spinner", fail_spinner)

    result = execute_generate(
        argparse.Namespace(
            no_repodata=False,
            quiet=quiet,
            json=json_enabled,
        )
    )

    assert result == 0
    assert read_manifest(generate_env.manifest_path).package_names == ["pandas"]


def test_generate_no_repodata_skips_repodata(generate_env, monkeypatch):
    def fail_extract():
        raise AssertionError("repodata should not be fetched")

    monkeypatch.setattr("conda_completion.cli.generate.extract_package_data", fail_extract)

    result = execute_generate(argparse.Namespace(no_repodata=True))

    assert result == 0
    assert read_manifest(generate_env.manifest_path).package_names == []


def test_generate_preserves_existing_package_data_on_repodata_failure(generate_env, monkeypatch):
    write_manifest(CompletionManifest(package_names=["numpy"]), generate_env.manifest_path)
    write_versions(
        {"numpy": ["2.0"]},
        generate_env.versions_index_path,
        generate_env.versions_store_path,
    )
    stale = time.time() - 48 * 60 * 60
    os.utime(generate_env.versions_index_path, (stale, stale))
    os.utime(generate_env.versions_store_path, (stale, stale))

    def fail_extract():
        raise RuntimeError("repodata failed")

    monkeypatch.setattr("conda_completion.cli.generate.extract_package_data", fail_extract)

    result = execute_generate(argparse.Namespace(no_repodata=False))

    assert result == 0
    assert read_manifest(generate_env.manifest_path).package_names == ["numpy"]


def test_generate_without_existing_package_data_handles_repodata_failure(
    generate_env,
    monkeypatch,
):
    def fail_extract():
        raise RuntimeError("repodata failed")

    monkeypatch.setattr("conda_completion.cli.generate.extract_package_data", fail_extract)

    result = execute_generate(argparse.Namespace(no_repodata=False))

    assert result == 0
    assert read_manifest(generate_env.manifest_path).package_names == []


def test_package_data_is_fresh_returns_false_for_missing_files(tmp_path):
    assert not package_data_is_fresh(
        tmp_path / "versions.index",
        tmp_path / "versions.store",
    )
