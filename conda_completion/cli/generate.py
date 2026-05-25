"""``conda completion generate`` -- introspect and write the manifest."""

from __future__ import annotations

import logging
from contextlib import nullcontext
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from conda.base.context import context
from conda.reporters import get_spinner

from ..introspect import generate_manifest
from ..manifest import read_manifest, write_manifest, write_versions
from ..paths import manifest_path, versions_index_path, versions_store_path
from ..plugin import plugin_entry_point_hash
from ..repodata import extract_package_data

if TYPE_CHECKING:
    import argparse
    from pathlib import Path

    from ..manifest import CompletionManifest

log = logging.getLogger(__name__)
PACKAGE_DATA_MAX_AGE = timedelta(hours=24)


def execute_generate(args: argparse.Namespace) -> int:
    """Generate the completion manifest from conda's argparse tree."""
    path = manifest_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    phash = plugin_entry_point_hash()
    manifest = generate_manifest(plugin_hash=phash)
    manifest = resolve_package_metadata(
        manifest,
        existing_manifest_path=path,
        refresh=getattr(args, "refresh_repodata", False),
        include=not getattr(args, "no_repodata", False),
        failure_log_level=logging.WARNING,
        show_spinner=not (getattr(args, "quiet", False) or getattr(args, "json", False)),
    )

    write_manifest(manifest, path)
    log.info("Completion manifest written to %s", path)
    return 0


def resolve_package_metadata(
    manifest: CompletionManifest,
    *,
    existing_manifest_path: Path,
    refresh: bool = False,
    include: bool = True,
    failure_log_level: int = logging.WARNING,
    show_spinner: bool = True,
) -> CompletionManifest:
    """Attach package names and write package versions when needed."""
    if not include:
        return manifest

    index_path = versions_index_path()
    store_path = versions_store_path()
    existing_package_names = read_existing_package_names(existing_manifest_path)
    if not refresh and existing_package_names and package_data_is_fresh(index_path, store_path):
        log.info("Reusing fresh package data")
        return replace(manifest, package_names=existing_package_names)

    try:
        spinner = (
            get_spinner("Collecting package metadata for completions")
            if should_show_repodata_spinner(show_spinner)
            else nullcontext()
        )
        with spinner:
            package_names, version_map = extract_package_data()
        write_versions(version_map, index_path, store_path)
        log.info(
            "Package versions written to %s and %s",
            index_path,
            store_path,
        )
        return replace(manifest, package_names=package_names)
    except Exception:
        if existing_package_names and package_data_files_exist(index_path, store_path):
            log.log(
                failure_log_level,
                "Failed to refresh package data; preserving existing package data",
                exc_info=True,
            )
            return replace(manifest, package_names=existing_package_names)
        log.log(
            failure_log_level,
            "Failed to extract package data from repodata",
            exc_info=True,
        )
        return manifest


def read_existing_package_names(path: Path) -> list[str]:
    try:
        return read_manifest(path).package_names
    except Exception:
        return []


def should_show_repodata_spinner(show_spinner: bool) -> bool:
    return show_spinner and not context.quiet and not context.json


def package_data_is_fresh(index_path: Path, store_path: Path) -> bool:
    if not package_data_files_exist(index_path, store_path):
        return False
    oldest_mtime = min(index_path.stat().st_mtime, store_path.stat().st_mtime)
    oldest = datetime.fromtimestamp(oldest_mtime, tz=timezone.utc)
    return datetime.now(timezone.utc) - oldest <= PACKAGE_DATA_MAX_AGE


def package_data_files_exist(index_path: Path, store_path: Path) -> bool:
    return all(
        path.exists() and not path.is_symlink() and path.is_file()
        for path in (index_path, store_path)
    )
