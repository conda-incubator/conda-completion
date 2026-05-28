"""Path helpers for manifest and cache locations."""

from __future__ import annotations

import os
from pathlib import Path

from platformdirs import user_cache_dir

_cache_dir_override: Path | None = None


def set_cache_dir_override(path: str | Path | None) -> Path | None:
    """Set a process-local cache directory override."""
    global _cache_dir_override
    if path is None:
        _cache_dir_override = None
        return None
    _cache_dir_override = _normalize_cache_dir(path)
    return _cache_dir_override


def _normalize_cache_dir(path: str | Path) -> Path:
    return Path(os.path.expandvars(str(path))).expanduser().resolve()


def completion_cache_dir() -> Path:
    """Return the platform-appropriate cache directory for completion data."""
    if _cache_dir_override is not None:
        return _cache_dir_override
    override = os.environ.get("CONDA_COMPLETION_CACHE_DIR")
    if override:
        return _normalize_cache_dir(override)
    return Path(user_cache_dir("conda")) / "completion"


def manifest_path() -> Path:
    """Return the path to the completion manifest msgpack file."""
    return completion_cache_dir() / "completion.msgpack"


def context_cache_path() -> Path:
    """Return the path to the stat-based context cache msgpack file."""
    return completion_cache_dir() / "context_cache.msgpack"


def versions_index_path() -> Path:
    """Return the path to the package versions offset index."""
    return completion_cache_dir() / "versions.index"


def versions_store_path() -> Path:
    """Return the path to the package versions byte store."""
    return completion_cache_dir() / "versions.store"
