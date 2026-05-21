"""``conda completion generate`` -- introspect and write the manifest."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ..introspect import generate_manifest
from ..manifest import write_manifest
from ..paths import manifest_path
from ..plugin import plugin_entry_point_hash

if TYPE_CHECKING:
    import argparse

log = logging.getLogger(__name__)


def execute_generate(args: argparse.Namespace) -> int:
    """Generate the completion manifest from conda's argparse tree."""
    path = manifest_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    phash = plugin_entry_point_hash()
    manifest = generate_manifest(plugin_hash=phash)
    write_manifest(manifest, path)

    log.info("Completion manifest written to %s", path)
    return 0
