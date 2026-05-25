"""Tests for path helper functions."""

from __future__ import annotations

from conda_completion.paths import (
    completion_cache_dir,
    context_cache_path,
    manifest_path,
    versions_index_path,
    versions_store_path,
)


def test_completion_cache_dir():
    result = completion_cache_dir()
    assert result.name == "completion"
    assert "conda" in str(result)


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
