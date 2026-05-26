"""Tests for argparse introspection."""

from __future__ import annotations

import argparse

import pytest

from conda_completion.exceptions import IntrospectionError
from conda_completion.introspect import generate_manifest, walk_parser


def test_walk_simple_parser():
    parser = argparse.ArgumentParser(description="Test parser")
    parser.add_argument("--verbose", "-v", action="store_true", help="Be verbose")
    parser.add_argument("--name", "-n", help="Environment name")
    parser.add_argument("package", help="Package to install")

    cmd = walk_parser(parser)

    assert "--verbose" in cmd.options
    assert cmd.options["--verbose"].short == "-v"
    assert "--name" in cmd.options
    assert cmd.options["--name"].short == "-n"
    assert cmd.options["--name"].completion_type == "env_name"
    assert len(cmd.positionals) == 1
    assert cmd.positionals[0].name == "package"


def test_walk_parser_with_subcommands():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")

    p_install = sub.add_parser("install", help="Install packages")
    p_install.add_argument("--channel", "-c", help="Channel")

    sub.add_parser("list", help="List packages")

    cmd = walk_parser(parser)

    assert "install" in cmd.subcommands
    assert "list" in cmd.subcommands
    assert cmd.subcommands["install"].summary == "Install packages"
    assert "--channel" in cmd.subcommands["install"].options


def test_walk_parser_with_choices():
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=["json", "yaml", "toml"])

    cmd = walk_parser(parser)

    assert cmd.options["--format"].choices == ["json", "yaml", "toml"]


def test_walk_parser_with_mutual_exclusion():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--from-lockfile", action="store_true")
    group.add_argument("--from-prefix", action="store_true")

    cmd = walk_parser(parser)

    assert len(cmd.exclusive_groups) == 1
    assert set(cmd.exclusive_groups[0]) == {"--from-lockfile", "--from-prefix"}


def test_walk_nested_subcommands():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")

    p_workspace = sub.add_parser("workspace", help="Workspace commands")
    ws_sub = p_workspace.add_subparsers(dest="subcmd")

    p_install = ws_sub.add_parser("install", help="Install workspace")
    p_install.add_argument("-e", "--environment", help="Target environment")

    cmd = walk_parser(parser)

    assert "workspace" in cmd.subcommands
    ws = cmd.subcommands["workspace"]
    assert "install" in ws.subcommands
    assert "--environment" in ws.subcommands["install"].options
    assert ws.subcommands["install"].options["--environment"].completion_type == "env_name"


@pytest.mark.parametrize(
    "flag,expected_type",
    [
        ("--name", "env_name"),
        ("--channel", "channel"),
        ("--prefix", "directory"),
    ],
    ids=["name-env", "channel", "prefix-dir"],
)
def test_completion_type_heuristics(flag, expected_type):
    parser = argparse.ArgumentParser()
    parser.add_argument(flag, help="test")

    cmd = walk_parser(parser)
    assert cmd.options[flag].completion_type == expected_type


@pytest.fixture()
def parser_with_groups():
    parser = argparse.ArgumentParser()
    grp = parser.add_argument_group("Channel Customization")
    grp.add_argument("--channel", "-c", help="Channel to search")
    grp.add_argument("--override-channels", action="store_true", help="Override")

    solver_grp = parser.add_argument_group("Solver Options")
    solver_grp.add_argument("--no-deps", action="store_true", help="No deps")

    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose")
    return walk_parser(parser)


@pytest.mark.parametrize(
    "flag,expected_group",
    [
        ("--channel", "Channel Customization"),
        ("--override-channels", "Channel Customization"),
        ("--no-deps", "Solver Options"),
        ("--verbose", None),
    ],
    ids=["channel-grouped", "override-grouped", "solver-grouped", "ungrouped"],
)
def test_walk_parser_extracts_action_groups(parser_with_groups, flag, expected_group):
    assert parser_with_groups.options[flag].group == expected_group


def test_suppressed_help_excluded():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hidden", help=argparse.SUPPRESS)
    parser.add_argument("--visible", help="Visible flag")

    cmd = walk_parser(parser)

    assert cmd.options["--hidden"].description is None
    assert cmd.options["--visible"].description == "Visible flag"


def test_generate_manifest_includes_plugin_subcommands():
    m = generate_manifest("test")
    assert "workspace" in m.commands
    assert "task" in m.commands


def test_generate_manifest_plugin_subcommand_depth():
    m = generate_manifest("test")
    ws = m.commands["workspace"]
    assert "install" in ws.subcommands
    assert "init" in ws.subcommands

    task = m.commands["task"]
    assert "run" in task.subcommands


def test_generate_manifest_wraps_parser_failure(monkeypatch):
    def raise_failure():
        raise RuntimeError("bad plugin")

    monkeypatch.setattr("conda_completion.introspect.generate_parser", raise_failure)

    with pytest.raises(IntrospectionError, match="bad plugin"):
        generate_manifest("test")


@pytest.mark.parametrize("exc", [KeyboardInterrupt, SystemExit], ids=["interrupt", "exit"])
def test_generate_manifest_preserves_interrupts(monkeypatch, exc):
    def raise_interrupt():
        raise exc

    monkeypatch.setattr("conda_completion.introspect.generate_parser", raise_interrupt)

    with pytest.raises(exc):
        generate_manifest("test")
