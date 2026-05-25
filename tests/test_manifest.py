"""Tests for manifest data model and msgpack I/O."""

from __future__ import annotations

import msgpack
import pytest

from conda_completion.exceptions import ManifestError
from conda_completion.manifest import (
    CommandSpec,
    CompletionManifest,
    OptionSpec,
    PositionalSpec,
    atomic_write,
    read_manifest,
    read_versions,
    write_manifest,
    write_versions,
)


def write_empty_manifest(path):
    write_manifest(CompletionManifest(), path)


def write_numpy_versions(path):
    write_versions({"numpy": ["2.0"]}, path)


def test_round_trip_empty_manifest(tmp_path):
    path = tmp_path / "completion.msgpack"
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
    path = tmp_path / "completion.msgpack"
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
    path = tmp_path / "completion.msgpack"
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
    path = tmp_path / "completion.msgpack"
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
    path = tmp_path / "completion.msgpack"
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
    path = tmp_path / "completion.msgpack"
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


def test_read_invalid_msgpack_raises_manifest_error(tmp_path):
    path = tmp_path / "bad.msgpack"
    path.write_bytes(b"\xff\xfe invalid msgpack bytes")

    with pytest.raises(ManifestError):
        read_manifest(path)


def test_read_manifest_non_dict_raises(tmp_path):
    path = tmp_path / "list.msgpack"

    path.write_bytes(msgpack.packb([1, 2, 3]))

    with pytest.raises(ManifestError, match="not a mapping"):
        read_manifest(path)


@pytest.mark.parametrize(
    "target_name,link_name,write_data,read_data",
    [
        pytest.param(
            "real.msgpack",
            "completion.msgpack",
            write_empty_manifest,
            read_manifest,
            id="manifest",
        ),
        pytest.param(
            "real_versions.msgpack",
            "versions.msgpack",
            write_numpy_versions,
            read_versions,
            id="versions",
        ),
    ],
)
def test_read_completion_data_rejects_symlink(
    tmp_path,
    target_name,
    link_name,
    write_data,
    read_data,
):
    target = tmp_path / target_name
    link = tmp_path / link_name
    write_data(target)
    link.symlink_to(target)

    with pytest.raises(ManifestError, match="symlink"):
        read_data(link)


def test_read_versions_round_trip(tmp_path):
    versions = {"numpy": ["2.0", "1.26"], "scipy": ["1.13"]}
    path = tmp_path / "versions.msgpack"
    write_versions(versions, path)

    loaded = read_versions(path)
    assert loaded == versions


@pytest.mark.parametrize(
    "setup",
    [
        pytest.param("invalid", id="corrupt-data"),
        pytest.param("missing", id="missing-file"),
    ],
)
def test_read_versions_error_cases(tmp_path, setup):
    if setup == "invalid":
        path = tmp_path / "bad_versions.msgpack"
        path.write_bytes(b"\xff\xfe bad")
    else:
        path = tmp_path / "nonexistent.msgpack"

    with pytest.raises(ManifestError):
        read_versions(path)


def test_atomic_write_rejects_symlink(tmp_path):
    target = tmp_path / "real_file"
    target.write_bytes(b"original")
    link = tmp_path / "link_file"
    link.symlink_to(target)

    with pytest.raises(OSError, match="symlink"):
        atomic_write(link, b"injected")

    assert target.read_bytes() == b"original"


def test_option_spec_group_round_trip(tmp_path):
    manifest = CompletionManifest(
        version=1,
        commands={
            "install": CommandSpec(
                options={
                    "--channel": OptionSpec(
                        short="-c",
                        description="Channel",
                        group="Channel Customization",
                    ),
                    "--verbose": OptionSpec(
                        description="Verbose",
                    ),
                },
            ),
        },
    )
    path = tmp_path / "test.msgpack"
    write_manifest(manifest, path)
    loaded = read_manifest(path)

    assert loaded.commands["install"].options["--channel"].group == "Channel Customization"
    assert loaded.commands["install"].options["--verbose"].group is None


def test_option_spec_default_and_required_round_trip(tmp_path):
    manifest = CompletionManifest(
        version=1,
        commands={
            "test": CommandSpec(
                options={
                    "--output": OptionSpec(
                        default="/tmp",
                        required=True,
                        metavar="PATH",
                    ),
                },
            ),
        },
    )
    path = tmp_path / "test.msgpack"
    write_manifest(manifest, path)
    loaded = read_manifest(path)

    opt = loaded.commands["test"].options["--output"]
    assert opt.default == "/tmp"
    assert opt.required is True
    assert opt.metavar == "PATH"
