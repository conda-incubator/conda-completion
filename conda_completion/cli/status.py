"""``conda completion status`` -- show completion system diagnostics."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from conda_completer import find_completer_binary

from ..manifest import read_manifest
from ..paths import completion_cache_dir, manifest_path, versions_index_path, versions_store_path
from ..plugin import plugin_entry_point_hash

if TYPE_CHECKING:
    import argparse


def execute_status(args: argparse.Namespace) -> int:
    """Print completion system status and diagnostics."""
    manifest = manifest_path()
    versions_index = versions_index_path()
    versions_store = versions_store_path()
    cache_dir = completion_cache_dir()

    print(f"Cache directory: {cache_dir}")
    print(f"Manifest: {manifest}")

    if manifest.exists():
        stat = manifest.stat()
        age = datetime.now(timezone.utc) - datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
        hours = int(age.total_seconds() // 3600)
        if hours < 1:
            age_str = f"{int(age.total_seconds() // 60)} minutes ago"
        elif hours < 24:
            age_str = f"{hours} hours ago"
        else:
            age_str = f"{hours // 24} days ago"
        print(f"  Last generated: {age_str} ({stat.st_size} bytes)")

        try:
            m = read_manifest(manifest)
            print(f"  Commands: {len(m.commands)}")
            print(f"  Packages: {len(m.package_names)}")
            print(f"  Plugin hash: {m.plugin_hash}")
        except Exception as exc:
            print(f"  Error reading manifest: {exc}")
    else:
        print("  Not found. Run: conda completion generate")

    print(f"Package versions index: {versions_index}")
    if versions_index.exists():
        print(f"  Size: {versions_index.stat().st_size} bytes")
    else:
        print("  Not found")

    print(f"Package versions store: {versions_store}")
    if versions_store.exists():
        print(f"  Size: {versions_store.stat().st_size} bytes")
    else:
        print("  Not found")

    current_hash = plugin_entry_point_hash()
    print(f"Current plugin hash: {current_hash}")

    try:
        binary = find_completer_binary()
        print(f"Completer binary: {binary}")
    except Exception:
        print("Completer binary: not found")

    return 0
