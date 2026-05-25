"""Argparse tree introspection for completion manifest generation.

Walks conda's full argparse tree (including all plugin subcommands)
and produces a CompletionManifest suitable for the Rust completer.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from conda.cli.conda_argparse import generate_parser as conda_generate_parser

from .exceptions import IntrospectionError
from .manifest import CommandSpec, CompletionManifest, OptionSpec, PositionalSpec

if TYPE_CHECKING:
    from collections.abc import Sequence

COMPLETION_TYPE_HEURISTICS: dict[str, str] = {
    "--name": "env_name",
    "--environment": "env_name",
    "--channel": "channel",
    "--prefix": "directory",
}

POSITIONAL_TYPE_HEURISTICS: dict[str, str] = {
    "package": "package_spec",
    "packages": "package_spec",
    "task_name": "task_name",
    "environment": "env_name",
}


def generate_manifest(plugin_hash: str = "") -> CompletionManifest:
    """Build a CompletionManifest by introspecting conda's argparse tree."""
    try:
        parser = generate_parser()
    except (KeyboardInterrupt, SystemExit):
        raise
    except BaseException as exc:
        raise IntrospectionError(str(exc)) from exc

    root_cmd = walk_parser(parser)

    return CompletionManifest(
        version=1,
        generated_at=datetime.now(timezone.utc).isoformat(),
        plugin_hash=plugin_hash,
        root_options=root_cmd.options,
        commands=root_cmd.subcommands,
    )


def generate_parser() -> argparse.ArgumentParser:
    return conda_generate_parser()


def walk_parser(parser: argparse.ArgumentParser) -> CommandSpec:
    """Recursively walk an argparse parser tree into a CommandSpec."""
    options: dict[str, OptionSpec] = {}
    positionals: list[PositionalSpec] = []
    subcommands: dict[str, CommandSpec] = {}
    exclusive_groups: list[list[str]] = []

    for group in parser._mutually_exclusive_groups:
        group_names = []
        for action in group._group_actions:
            if action.option_strings:
                group_names.append(action.option_strings[0])
        if len(group_names) > 1:
            exclusive_groups.append(group_names)

    action_groups: dict[int, str] = {}
    for ag in parser._action_groups:
        if not ag.title or ag.title in ("positional arguments", "options"):
            continue
        for action in ag._group_actions:
            action_groups[id(action)] = ag.title

    for action in parser._actions:
        if isinstance(action, argparse._HelpAction):
            continue

        if isinstance(action, argparse._SubParsersAction):
            for name, subparser in action.choices.items():
                sub_help = next(
                    (ca.help for ca in action._choices_actions if ca.dest == name),
                    None,
                )
                sub_cmd = walk_parser(subparser)
                subcommands[name] = CommandSpec(
                    summary=sub_help or sub_cmd.summary,
                    options=sub_cmd.options,
                    positionals=sub_cmd.positionals,
                    subcommands=sub_cmd.subcommands,
                    exclusive_groups=sub_cmd.exclusive_groups,
                )
            continue

        if action.option_strings:
            long_names = [s for s in action.option_strings if s.startswith("--")]
            short_names = [
                s for s in action.option_strings if s.startswith("-") and not s.startswith("--")
            ]
            long_name = long_names[0] if long_names else action.option_strings[-1]
            short_name = short_names[0] if short_names else None

            completion_type = infer_completion_type(action.option_strings)

            description = action.help if action.help != argparse.SUPPRESS else None

            nargs = action.nargs
            if isinstance(nargs, int):
                pass
            elif nargs in ("?", "*", "+"):
                pass
            else:
                nargs = None

            default_str = None
            if action.default is not None and action.default is not argparse.SUPPRESS:
                try:
                    default_str = str(action.default) if action.default != [] else None
                except Exception:
                    default_str = None

            choices = None
            if action.choices:
                choices = [str(c) for c in action.choices]

            options[long_name] = OptionSpec(
                short=short_name,
                choices=choices,
                nargs=nargs,
                completion_type=completion_type,
                description=description,
                metavar=action.metavar if isinstance(action.metavar, str) else None,
                default=default_str,
                required=action.required,
                group=action_groups.get(id(action)),
            )
        else:
            if action.dest in ("cmd", "subcmd", "_plugin_subcommand"):
                continue

            completion_type = POSITIONAL_TYPE_HEURISTICS.get(action.dest)

            description = action.help if action.help != argparse.SUPPRESS else None

            nargs = action.nargs
            if isinstance(nargs, int):
                pass
            elif nargs in ("?", "*", "+"):
                pass
            elif nargs == argparse.REMAINDER:
                nargs = "..."
            else:
                nargs = None

            choices = None
            if action.choices:
                choices = [str(c) for c in action.choices]

            positionals.append(
                PositionalSpec(
                    name=action.dest,
                    choices=choices,
                    nargs=nargs,
                    completion_type=completion_type,
                    description=description,
                    metavar=action.metavar if isinstance(action.metavar, str) else None,
                )
            )

    return CommandSpec(
        summary=parser.description,
        options=options,
        positionals=positionals,
        subcommands=subcommands,
        exclusive_groups=exclusive_groups,
    )


def infer_completion_type(option_strings: Sequence[str]) -> str | None:
    """Infer a dynamic completion type from option flag names.

    Only matches on the long-form flag (e.g., --name) to avoid false
    positives where unrelated flags share the same short form.
    """
    for opt in option_strings:
        if opt in COMPLETION_TYPE_HEURISTICS:
            return COMPLETION_TYPE_HEURISTICS[opt]
    return None
