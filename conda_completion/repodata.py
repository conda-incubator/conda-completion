"""Extract package names and versions from conda repodata."""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def extract_package_data() -> tuple[list[str], dict[str, list[str]]]:
    """Extract package names and versions from repodata.

    Uses conda's SubdirData API which handles sharded and monolithic
    repodata transparently, including HTTP caching and credentials.

    Returns a sorted list of unique package names and a dict mapping
    each name to its sorted list of available versions.
    """
    from conda.base.context import context
    from conda.core.subdir_data import SubdirData
    from conda.models.channel import Channel

    names: set[str] = set()
    versions: dict[str, set[str]] = {}

    subdir_channels = []
    for channel_name in context.channels:
        for subdir in context.subdirs:
            subdir_channels.append(Channel(f"{channel_name}/{subdir}"))

    log.info("Fetching repodata from %d channel/subdir combinations", len(subdir_channels))

    for channel in subdir_channels:
        try:
            sd = SubdirData(channel)
            for record in sd.iter_records():
                name = record.name
                names.add(name)
                if name not in versions:
                    versions[name] = set()
                versions[name].add(str(record.version))
        except Exception:
            log.debug(
                "Failed to load repodata for %s",
                channel.canonical_name,
                exc_info=True,
            )

    from conda.models.version import VersionOrder

    sorted_names = sorted(names)
    sorted_versions = {
        name: sorted(vers, key=VersionOrder, reverse=True)
        for name, vers in sorted(versions.items())
    }

    log.info(
        "Found %d packages across %d channel/subdir combinations",
        len(sorted_names),
        len(subdir_channels),
    )
    return sorted_names, sorted_versions
