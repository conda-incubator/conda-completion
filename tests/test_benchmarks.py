"""Performance benchmarks for conda-completion.

Focuses on operations that run on the hot path (manifest I/O,
introspection, version lookups) and could regress as the project
evolves.
"""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING

import pytest

from conda_completion.introspect import walk_parser
from conda_completion.manifest import (
    CommandSpec,
    CompletionManifest,
    OptionSpec,
    PositionalSpec,
    read_manifest,
    read_versions,
    write_manifest,
    write_versions,
)

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_benchmark.fixture import BenchmarkFixture

pytestmark = pytest.mark.benchmark


def build_realistic_manifest() -> CompletionManifest:
    """Build a manifest with size similar to a real conda installation."""
    commands: dict[str, CommandSpec] = {}
    for name in ("install", "remove", "update", "create", "list", "info", "search"):
        commands[name] = CommandSpec(
            summary=f"{name.title()} packages in an environment",
            options={
                "--name": OptionSpec(
                    short="-n",
                    completion_type="env_name",
                    description="Name of environment",
                    metavar="NAME",
                ),
                "--channel": OptionSpec(
                    short="-c",
                    completion_type="channel",
                    description="Additional channel to search",
                ),
                "--dry-run": OptionSpec(description="Only display what would have been done"),
                "--json": OptionSpec(description="Report all output as json"),
                "--verbose": OptionSpec(short="-v", description="Increase verbosity"),
                "--quiet": OptionSpec(short="-q", description="Decrease verbosity"),
            },
            positionals=[
                PositionalSpec(
                    name="packages",
                    nargs="+",
                    completion_type="package_spec",
                    description="Packages to install",
                ),
            ],
        )

    for plugin in ("workspace", "global", "spawn", "completion", "pypi"):
        sub = {}
        for action in ("install", "list", "remove", "status"):
            sub[action] = CommandSpec(
                summary=f"{action.title()} {plugin} items",
                options={
                    "--verbose": OptionSpec(short="-v", description="Increase verbosity"),
                },
            )
        commands[plugin] = CommandSpec(
            summary=f"Manage {plugin}",
            subcommands=sub,
        )

    package_names = [f"package-{i}" for i in range(5000)]

    return CompletionManifest(
        version=1,
        generated_at="2025-01-01T00:00:00Z",
        plugin_hash="benchmark-hash",
        commands=commands,
        package_names=package_names,
    )


def build_realistic_parser() -> argparse.ArgumentParser:
    """Build an argparse tree similar to a real conda subcommand."""
    parser = argparse.ArgumentParser(prog="conda", description="conda package manager")
    parser.add_argument("--verbose", "-v", action="count", default=0, help="Increase verbosity")
    parser.add_argument("--json", action="store_true", help="Report all output as json")

    sub = parser.add_subparsers(dest="command")

    for cmd_name in ("install", "remove", "update", "create"):
        p = sub.add_parser(cmd_name, help=f"{cmd_name.title()} packages")
        p.add_argument("--name", "-n", metavar="ENVIRONMENT", help="Name of environment")
        p.add_argument("--channel", "-c", action="append", help="Additional channel")
        p.add_argument("--dry-run", action="store_true", help="Only display what would be done")
        p.add_argument("--yes", "-y", action="store_true", help="Do not ask for confirmation")
        p.add_argument("--quiet", "-q", action="count", default=0, help="Decrease verbosity")
        p.add_argument("packages", nargs="*", help="Packages to install")

    p_config = sub.add_parser("config", help="Modify configuration values")
    p_config.add_argument("--show", nargs="*", help="Show config values")
    p_config.add_argument("--set", nargs=2, action="append", help="Set a config key")

    return parser


def test_bench_manifest_write(benchmark: BenchmarkFixture, tmp_path: Path) -> None:
    """Serialize a realistic manifest to msgpack."""
    manifest = build_realistic_manifest()
    path = tmp_path / "completion.msgpack"

    benchmark(write_manifest, manifest, path)


def test_bench_manifest_read(benchmark: BenchmarkFixture, tmp_path: Path) -> None:
    """Deserialize a realistic manifest from msgpack."""
    manifest = build_realistic_manifest()
    path = tmp_path / "completion.msgpack"
    write_manifest(manifest, path)

    benchmark(read_manifest, path)


def test_bench_manifest_round_trip(benchmark: BenchmarkFixture, tmp_path: Path) -> None:
    """Full write-then-read cycle for a realistic manifest."""
    manifest = build_realistic_manifest()
    path = tmp_path / "completion.msgpack"

    def round_trip():
        write_manifest(manifest, path)
        return read_manifest(path)

    benchmark(round_trip)


def build_realistic_versions(
    n_packages: int = 28000, n_versions: int = 20
) -> dict[str, list[str]]:
    """Build version data at conda-forge scale."""
    return {
        f"package-{i}": [f"{j}.{i % 10}.0" for j in range(n_versions)] for i in range(n_packages)
    }


def test_bench_versions_write(benchmark: BenchmarkFixture, tmp_path: Path) -> None:
    """Write version data for 28000 packages (conda-forge scale)."""
    versions = build_realistic_versions()
    path = tmp_path / "versions.msgpack"

    benchmark(write_versions, versions, path)


def test_bench_versions_read_full(benchmark: BenchmarkFixture, tmp_path: Path) -> None:
    """Deserialize the full versions file (single-file legacy path)."""
    versions = build_realistic_versions()
    path = tmp_path / "versions.msgpack"
    write_versions(versions, path)

    benchmark(read_versions, path)


def test_bench_walk_parser(benchmark: BenchmarkFixture) -> None:
    """Introspect a realistic argparse tree into CommandSpec."""
    parser = build_realistic_parser()

    benchmark(walk_parser, parser)


def test_bench_plugin_import(benchmark: BenchmarkFixture) -> None:
    """Full plugin module import chain."""
    import importlib

    import conda_completion.plugin

    def reimport():
        importlib.reload(conda_completion.plugin)

    benchmark(reimport)


def test_bench_manifest_to_dict(benchmark: BenchmarkFixture) -> None:
    """Convert manifest dataclasses to dict (pre-serialization step)."""
    manifest = build_realistic_manifest()

    benchmark(manifest.to_dict)


def test_bench_manifest_from_dict(benchmark: BenchmarkFixture) -> None:
    """Reconstruct manifest dataclasses from dict (post-deserialization step)."""
    manifest = build_realistic_manifest()
    data = manifest.to_dict()

    benchmark(CompletionManifest.from_dict, data)
