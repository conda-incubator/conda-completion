"""Tests for argparse introspection."""

from __future__ import annotations

import argparse
import logging

import pytest

from conda_completion.exceptions import IntrospectionError
from conda_completion.introspect import StaticChoiceResolver, generate_manifest, walk_parser


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


@pytest.mark.parametrize(
    ("option_strings", "kwargs"),
    [
        (("--show",), {"nargs": "*", "help": "Display configuration values"}),
        (("--describe",), {"nargs": "*", "help": "Describe configuration parameters"}),
        (("--get",), {"nargs": "*", "metavar": "KEY"}),
        (("--append",), {"nargs": 2, "metavar": ("KEY", "VALUE")}),
        (("--prepend",), {"nargs": 2, "metavar": ("KEY", "VALUE")}),
        (("--set",), {"nargs": 2, "metavar": ("KEY", "VALUE")}),
        (("--remove",), {"nargs": 2, "metavar": ("KEY", "VALUE")}),
        (("--remove-key",), {"metavar": "KEY"}),
        (("-K",), {"metavar": "KEY"}),
        (("--future-key",), {"metavar": "KEY"}),
        (("--future-show",), {"nargs": "*", "help": "Show configuration parameters"}),
    ],
)
def test_walk_parser_adds_conda_config_parameter_choices(option_strings, kwargs):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    p_config = sub.add_parser("config")
    p_config.add_argument(*option_strings, **kwargs)

    cmd = walk_parser(
        parser,
        choice_resolver=StaticChoiceResolver(
            {"config_parameters": ["channels", "envs_dirs"]},
        ),
    )

    assert cmd.subcommands["config"].options[option_strings[0]].choices == [
        "channels",
        "envs_dirs",
    ]


def test_walk_parser_adds_conda_config_parameter_choices_to_aliases():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    p_config = sub.add_parser("config")
    p_config.add_argument("--prepend", "--add", nargs=2, metavar=("KEY", "VALUE"))

    cmd = walk_parser(
        parser,
        choice_resolver=StaticChoiceResolver(
            {"config_parameters": ["channels", "envs_dirs"]},
        ),
    )
    options = cmd.subcommands["config"].options

    assert options["--prepend"].choices == ["channels", "envs_dirs"]
    assert options["--add"].choices == ["channels", "envs_dirs"]


@pytest.mark.parametrize(
    ("option_strings", "kwargs"),
    [
        (("--file",), {"metavar": "FILE", "help": "Write to the given file"}),
        (("--prefix",), {"metavar": "PATH", "help": "Full path to environment location"}),
        (("--validate",), {"action": "store_true", "help": "Validate configuration sources"}),
        (("--future",), {"nargs": "*", "help": "List matching environment names"}),
        (("--unknown",), {"nargs": "*"}),
    ],
)
def test_walk_parser_does_not_add_config_parameter_choices_to_other_values(
    option_strings,
    kwargs,
):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    p_config = sub.add_parser("config")
    p_config.add_argument(*option_strings, **kwargs)

    cmd = walk_parser(
        parser,
        choice_resolver=StaticChoiceResolver(
            {"config_parameters": ["channels", "envs_dirs"]},
        ),
    )

    assert cmd.subcommands["config"].options[option_strings[0]].choices is None


@pytest.mark.parametrize("subcommand", ["check", "doctor"])
def test_walk_parser_adds_health_check_choices(subcommand):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    p_check = sub.add_parser(subcommand)
    p_check.add_argument("checks", nargs="*", metavar="NAME")

    cmd = walk_parser(
        parser,
        choice_resolver=StaticChoiceResolver(
            {"health_checks": ["altered-files", "pinned"]},
        ),
    )

    assert cmd.subcommands[subcommand].positionals[0].choices == [
        "altered-files",
        "pinned",
    ]


def test_generate_manifest_adds_static_choices(monkeypatch):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    p_config = sub.add_parser("config")
    p_config.add_argument("--show", nargs="*", help="Show configuration values")
    p_doctor = sub.add_parser("doctor")
    p_doctor.add_argument("checks", nargs="*", metavar="NAME")

    monkeypatch.setattr("conda_completion.introspect.generate_parser", lambda: parser)
    monkeypatch.setattr(
        StaticChoiceResolver,
        "from_conda",
        classmethod(
            lambda cls: cls(
                {
                    "config_parameters": ["channels", "pkgs_dirs"],
                    "health_checks": ["altered-files", "pinned"],
                },
            ),
        ),
    )

    manifest = generate_manifest("test")

    assert manifest.commands["config"].options["--show"].choices == [
        "channels",
        "pkgs_dirs",
    ]
    assert manifest.commands["doctor"].positionals[0].choices == [
        "altered-files",
        "pinned",
    ]


def test_static_choice_resolver_preserves_other_providers(monkeypatch, caplog):
    def raise_failure():
        raise AttributeError("missing conda API")

    monkeypatch.setattr(
        StaticChoiceResolver,
        "providers",
        {
            "config_parameters": raise_failure,
            "health_checks": lambda: ["pinned"],
        },
    )
    caplog.set_level(logging.WARNING)

    resolver = StaticChoiceResolver.from_conda()

    assert resolver.choices_by_source == {"health_checks": ["pinned"]}
    assert "Failed to collect config_parameters completion choices" in caplog.text


def test_static_choice_resolver_skips_empty_provider_results(monkeypatch):
    monkeypatch.setattr(
        StaticChoiceResolver,
        "providers",
        {
            "config_parameters": lambda: [],
            "health_checks": lambda: ["pinned"],
        },
    )

    resolver = StaticChoiceResolver.from_conda()

    assert resolver.choices_by_source == {"health_checks": ["pinned"]}


def test_generate_manifest_preserves_static_choice_provider_failure(monkeypatch):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    p_config = sub.add_parser("config")
    p_config.add_argument("--show", nargs="*", help="Show configuration values")

    def raise_failure():
        raise AttributeError("missing conda API")

    monkeypatch.setattr("conda_completion.introspect.generate_parser", lambda: parser)
    monkeypatch.setattr(
        StaticChoiceResolver,
        "providers",
        {"config_parameters": raise_failure},
    )

    manifest = generate_manifest("test")

    assert manifest.commands["config"].options["--show"].choices is None


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


def test_explicit_completion_type_beats_heuristics():
    parser = argparse.ArgumentParser()
    action = parser.add_argument("--channel", help="test")
    action.completion_type = "package_spec"

    cmd = walk_parser(parser)

    assert cmd.options["--channel"].completion_type == "package_spec"


def test_walk_parser_extracts_completion_rules():
    parser = argparse.ArgumentParser()
    action = parser.add_argument("tool")
    action.completion = {
        "sources": ["cached_tool", "package_spec"],
        "rules": [
            {"when_options": ["--clean"], "sources": ["cached_tool"]},
            {"when_options": ["--lock"], "sources": ["file"]},
        ],
    }

    cmd = walk_parser(parser)
    completion = cmd.positionals[0].completion

    assert completion is not None
    assert completion.sources == ["cached_tool", "package_spec"]
    assert completion.rules[0].when_options == ["--clean"]
    assert completion.rules[0].sources == ["cached_tool"]
    assert completion.rules[1].when_options == ["--lock"]
    assert completion.rules[1].sources == ["file"]


def test_walk_parser_extracts_runtime_sources_from_actions():
    parser = argparse.ArgumentParser()
    action = parser.add_argument("tool")
    action.completion_runtime_sources = {
        "cached_tool": {
            "kind": "directory_entries",
            "description": "cached tool",
            "group": "tool",
            "env_var": "TOOL_HOME",
            "env_suffix": ["envs"],
            "home_suffix": [".tools", "envs"],
            "entry_type": "directory",
            "strip_suffix": "--",
            "max_entries": 10_000,
        },
    }
    runtime_sources = {}

    walk_parser(parser, runtime_sources=runtime_sources)

    assert runtime_sources["cached_tool"].kind == "directory_entries"
    assert runtime_sources["cached_tool"].group == "tool"
    assert runtime_sources["cached_tool"].strip_suffix == "--"


def test_walk_parser_extracts_command_aliases():
    parser = argparse.ArgumentParser()
    aliases = {}
    sub = parser.add_subparsers(dest="cmd")
    p_exec = sub.add_parser("exec", help="Run a tool")
    p_exec.completion_aliases = ["ce"]

    walk_parser(parser, aliases=aliases)

    assert aliases["ce"].target == ["exec"]


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
