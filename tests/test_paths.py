"""Tests for path helper functions."""

from __future__ import annotations

import pytest

from conda_completion.paths import (
    completion_cache_dir,
    context_cache_path,
    manifest_path,
    set_cache_dir_override,
    versions_index_path,
    versions_store_path,
)


@pytest.fixture(autouse=True)
def clear_cache_dir_override(monkeypatch):
    monkeypatch.delenv("CONDA_COMPLETION_CACHE_DIR", raising=False)
    set_cache_dir_override(None)


def test_completion_cache_dir():
    result = completion_cache_dir()
    assert result.name == "completion"
    assert "conda" in str(result)


def test_completion_cache_dir_env_override(monkeypatch, tmp_path):
    custom_dir = tmp_path / "completion-cache"
    monkeypatch.setenv("CONDA_COMPLETION_CACHE_DIR", str(custom_dir))

    assert completion_cache_dir() == custom_dir
    assert manifest_path() == custom_dir / "completion.msgpack"
    assert context_cache_path() == custom_dir / "context_cache.msgpack"
    assert versions_index_path() == custom_dir / "versions.index"
    assert versions_store_path() == custom_dir / "versions.store"


def test_completion_cache_dir_cli_override_precedes_env(monkeypatch, tmp_path):
    env_dir = tmp_path / "env-cache"
    cli_dir = tmp_path / "cli-cache"
    monkeypatch.setenv("CONDA_COMPLETION_CACHE_DIR", str(env_dir))

    set_cache_dir_override(cli_dir)

    assert completion_cache_dir() == cli_dir
    assert manifest_path() == cli_dir / "completion.msgpack"


def test_manifest_path():
    result = manifest_path()
    assert result.name == "completion.msgpack"
    assert result.parent == completion_cache_dir()


def test_context_cache_path():
    result = context_cache_path()
    assert result.name == "context_cache.msgpack"
    assert result.parent == completion_cache_dir()


def test_versions_index_path():
    result = versions_index_path()
    assert result.name == "versions.index"
    assert result.parent == completion_cache_dir()


def test_versions_store_path():
    result = versions_store_path()
    assert result.name == "versions.store"
    assert result.parent == completion_cache_dir()
