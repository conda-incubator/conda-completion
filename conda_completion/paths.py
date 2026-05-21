"""Path helpers for manifest and cache locations."""

from __future__ import annotations

from pathlib import Path

from platformdirs import user_cache_dir


def completion_cache_dir() -> Path:
    """Return the platform-appropriate cache directory for completion data."""
    return Path(user_cache_dir("conda")) / "completion"


def manifest_path() -> Path:
    """Return the path to the completion manifest TOML file."""
    return completion_cache_dir() / "completion.toml"


def context_cache_path() -> Path:
    """Return the path to the stat-based context cache file."""
    return completion_cache_dir() / "context_cache.toml"
