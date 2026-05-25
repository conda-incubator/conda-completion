"""Conda plugin registration for conda-completion.

This module is imported on every conda invocation via the entry point
system.  Only ``hookimpl`` and type imports are used at module level;
everything else is lazily imported inside the hooks to keep the
overhead under 1 ms.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from conda.plugins import hookimpl

if TYPE_CHECKING:
    from collections.abc import Iterable

    from conda.plugins.types import CondaPostCommand, CondaSubcommand


@hookimpl
def conda_subcommands() -> Iterable[CondaSubcommand]:
    from conda.plugins.types import CondaSubcommand

    from .cli.main import configure_parser, execute

    yield CondaSubcommand(
        name="completion",
        summary="Generate and install shell tab completions for conda.",
        action=execute,
        configure_parser=configure_parser,
    )


@hookimpl
def conda_post_commands() -> Iterable[CondaPostCommand]:
    from conda.plugins.types import CondaPostCommand

    yield CondaPostCommand(
        name="conda-completion-regen",
        action=maybe_regenerate,
        run_for={"install", "remove", "update"},
    )


def maybe_regenerate(command: str) -> None:
    """Regenerate the completion manifest if the plugin set has changed.

    Compares a hash of currently registered plugin entry point names
    against the hash stored in the manifest.  If they differ, the
    manifest is stale and gets regenerated.

    This hook must never crash conda, so all exceptions are caught.
    Permission and I/O errors are logged at warning level so users
    can diagnose problems; other errors are logged at debug level.
    """
    import logging

    log = logging.getLogger(__name__)

    try:
        from .paths import manifest_path

        path = manifest_path()
        if not path.exists():
            import sys

            print(
                "Run 'conda completion install' to enable tab completions.",
                file=sys.stderr,
            )
            return

        current_hash = plugin_entry_point_hash()
        stored_hash = read_manifest_plugin_hash(path)

        if current_hash != stored_hash:
            log.info("Plugin set changed, regenerating completion manifest")
            from dataclasses import replace

            from .introspect import generate_manifest
            from .manifest import write_manifest, write_versions
            from .paths import versions_index_path, versions_store_path
            from .repodata import extract_package_data

            manifest = generate_manifest(plugin_hash=current_hash)
            try:
                package_names, version_map = extract_package_data()
                manifest = replace(manifest, package_names=package_names)
                write_versions(version_map, versions_index_path(), versions_store_path())
            except Exception:
                log.debug("Failed to refresh package data", exc_info=True)
            write_manifest(manifest, path)
    except PermissionError:
        log.warning("Cannot update completion manifest: permission denied")
    except OSError as exc:
        log.warning("Cannot update completion manifest: %s", exc)
    except (KeyboardInterrupt, SystemExit):
        raise
    except BaseException:
        log.debug("Failed to check/regenerate completion manifest", exc_info=True)


def plugin_entry_point_hash() -> str:
    """Hash the names of all registered conda plugin entry points."""
    import hashlib
    from importlib.metadata import entry_points

    eps = sorted(ep.name for ep in entry_points(group="conda"))
    return hashlib.sha256("|".join(eps).encode()).hexdigest()[:16]


def read_manifest_plugin_hash(path) -> str | None:
    """Read the plugin_hash field from an existing msgpack manifest."""
    try:
        from .manifest import read_manifest

        return read_manifest(path).plugin_hash or None
    except Exception:
        return None
