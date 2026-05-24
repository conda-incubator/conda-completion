"""``conda completion generate`` -- introspect and write the manifest."""

from __future__ import annotations

import logging
from dataclasses import replace
from typing import TYPE_CHECKING

from ..introspect import generate_manifest
from ..manifest import write_manifest, write_versions
from ..paths import manifest_path, versions_path
from ..plugin import plugin_entry_point_hash
from ..repodata import extract_package_data

if TYPE_CHECKING:
    import argparse

log = logging.getLogger(__name__)


def execute_generate(args: argparse.Namespace) -> int:
    """Generate the completion manifest from conda's argparse tree."""
    path = manifest_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    phash = plugin_entry_point_hash()
    manifest = generate_manifest(plugin_hash=phash)

    try:
        package_names, version_map = extract_package_data()
        manifest = replace(manifest, package_names=package_names)
        write_versions(version_map, versions_path())
        log.info("Package versions written to %s", versions_path())
    except Exception:
        log.warning("Failed to extract package data from repodata", exc_info=True)

    write_manifest(manifest, path)
    log.info("Completion manifest written to %s", path)
    return 0
