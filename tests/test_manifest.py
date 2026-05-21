"""Tests for manifest data model and TOML I/O."""

from __future__ import annotations

import pytest

from conda_completion.manifest import (
    CommandSpec,
    CompletionManifest,
    OptionSpec,
    PositionalSpec,
    read_manifest,
    write_manifest,
)


def test_round_trip_empty_manifest(tmp_path):
    path = tmp_path / "completion.toml"
    manifest = CompletionManifest(
        version=1,
        generated_at="2025-01-01T00:00:00Z",
        plugin_hash="abc123",
    )
    write_manifest(manifest, path)
    loaded = read_manifest(path)

    assert loaded.version == 1
    assert loaded.generated_at == "2025-01-01T00:00:00Z"
    assert loaded.plugin_hash == "abc123"
    assert loaded.commands == {}
    assert loaded.root_options == {}


def test_round_trip_with_commands(tmp_path):
    path = tmp_path / "completion.toml"
    manifest = CompletionManifest(
        version=1,
        generated_at="2025-01-01T00:00:00Z",
        plugin_hash="abc123",
        commands={
            "install": CommandSpec(
                summary="Install packages into an environment",
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
                    "--dry-run": OptionSpec(
                        description="Only display what would have been done",
                    ),
                },
                positionals=[
                    PositionalSpec(
                        name="packages",
                        nargs="+",
                        completion_type="package_spec",
                        description="Packages to install",
                    ),
                ],
            ),
            "workspace": CommandSpec(
                summary="Manage workspaces",
                subcommands={
                    "install": CommandSpec(summary="Install workspace environments"),
                    "list": CommandSpec(summary="List workspace environments"),
                },
            ),
        },
    )
    write_manifest(manifest, path)
    loaded = read_manifest(path)

    assert "install" in loaded.commands
    assert "workspace" in loaded.commands

    install = loaded.commands["install"]
    assert install.summary == "Install packages into an environment"
    assert "--name" in install.options
    assert install.options["--name"].short == "-n"
    assert install.options["--name"].completion_type == "env_name"
    assert len(install.positionals) == 1
    assert install.positionals[0].name == "packages"

    workspace = loaded.commands["workspace"]
    assert "install" in workspace.subcommands
    assert "list" in workspace.subcommands


def test_round_trip_with_root_options(tmp_path):
    path = tmp_path / "completion.toml"
    manifest = CompletionManifest(
        version=1,
        root_options={
            "--verbose": OptionSpec(
                short="-v",
                description="Use once for info, twice for debug",
            ),
            "--json": OptionSpec(
                description="Report all output as json",
            ),
        },
        commands={
            "install": CommandSpec(summary="Install packages"),
        },
    )
    write_manifest(manifest, path)
    loaded = read_manifest(path)

    assert "--verbose" in loaded.root_options
    assert loaded.root_options["--verbose"].short == "-v"
    assert loaded.root_options["--verbose"].description == "Use once for info, twice for debug"
    assert "--json" in loaded.root_options
    assert loaded.root_options["--json"].description == "Report all output as json"


def test_round_trip_with_choices(tmp_path):
    path = tmp_path / "completion.toml"
    manifest = CompletionManifest(
        version=1,
        commands={
            "config": CommandSpec(
                options={
                    "--show": OptionSpec(
                        choices=["channels", "envs_dirs", "pkgs_dirs"],
                        description="Show config value",
                    ),
                },
            ),
        },
    )
    write_manifest(manifest, path)
    loaded = read_manifest(path)

    assert loaded.commands["config"].options["--show"].choices == [
        "channels",
        "envs_dirs",
        "pkgs_dirs",
    ]


def test_round_trip_exclusive_groups(tmp_path):
    path = tmp_path / "completion.toml"
    manifest = CompletionManifest(
        version=1,
        commands={
            "install": CommandSpec(
                exclusive_groups=[["--from-lockfile", "--from-prefix"]],
            ),
        },
    )
    write_manifest(manifest, path)
    loaded = read_manifest(path)

    assert loaded.commands["install"].exclusive_groups == [
        ["--from-lockfile", "--from-prefix"],
    ]


@pytest.mark.parametrize(
    "nargs_in,nargs_out",
    [
        ("?", "?"),
        ("*", "*"),
        ("+", "+"),
        ("2", "2"),
    ],
    ids=["optional", "zero-or-more", "one-or-more", "exactly-two"],
)
def test_nargs_round_trip(tmp_path, nargs_in, nargs_out):
    path = tmp_path / "completion.toml"
    manifest = CompletionManifest(
        version=1,
        commands={
            "test": CommandSpec(
                options={"--flag": OptionSpec(nargs=nargs_in)},
            ),
        },
    )
    write_manifest(manifest, path)
    loaded = read_manifest(path)

    assert loaded.commands["test"].options["--flag"].nargs == nargs_out


def test_read_invalid_toml_raises_manifest_error(tmp_path):
    from conda_completion.exceptions import ManifestError

    path = tmp_path / "bad.toml"
    path.write_text("this is not valid toml [[[", encoding="utf-8")

    with pytest.raises(ManifestError):
        read_manifest(path)
