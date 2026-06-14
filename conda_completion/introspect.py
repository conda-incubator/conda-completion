"""Argparse tree introspection for completion manifest generation.

Walks conda's full argparse tree (including all plugin subcommands)
and produces a CompletionManifest suitable for the Rust completer.
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from conda.base.context import context
from conda.cli.conda_argparse import generate_parser as conda_generate_parser

from .exceptions import IntrospectionError
from .manifest import (
    AliasSpec,
    CommandSpec,
    CompletionManifest,
    CompletionRule,
    CompletionSpec,
    OptionSpec,
    PositionalSpec,
    RuntimeSourceSpec,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

log = logging.getLogger(__name__)

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

STATIC_POSITIONAL_CHOICE_RULES: dict[tuple[tuple[str, ...], str], str] = {
    (("check",), "checks"): "health_checks",
    (("doctor",), "checks"): "health_checks",
}

STATIC_CHOICE_PROVIDERS: dict[str, Callable[[], list[str]]] = {
    "config_parameters": lambda: [str(name) for name in context.list_parameters()],
    "health_checks": lambda: sorted(list_health_checks()),
}


def generate_manifest(plugin_hash: str = "") -> CompletionManifest:
    """Build a CompletionManifest by introspecting conda's argparse tree."""
    try:
        parser = generate_parser()
        static_choices = collect_static_choices()
    except (KeyboardInterrupt, SystemExit):
        raise
    except BaseException as exc:
        raise IntrospectionError(str(exc)) from exc

    aliases: dict[str, AliasSpec] = {}
    runtime_sources: dict[str, RuntimeSourceSpec] = {}
    root_cmd = walk_parser(
        parser,
        aliases=aliases,
        runtime_sources=runtime_sources,
        static_choices=static_choices,
    )

    return CompletionManifest(
        version=1,
        generated_at=datetime.now(timezone.utc).isoformat(),
        plugin_hash=plugin_hash,
        root_options=root_cmd.options,
        commands=root_cmd.subcommands,
        aliases=aliases,
        runtime_sources=runtime_sources,
    )


def generate_parser() -> argparse.ArgumentParser:
    return conda_generate_parser()


def collect_static_choices() -> dict[str, list[str]]:
    choices_by_name: dict[str, list[str]] = {}
    for name, provider in STATIC_CHOICE_PROVIDERS.items():
        try:
            choices = provider()
        except Exception:
            log.warning("Failed to collect %s completion choices", name, exc_info=True)
            continue
        if choices:
            choices_by_name[name] = choices
    return choices_by_name


def list_health_checks() -> list[str]:
    from conda.plugins.manager import get_plugin_manager

    return list(get_plugin_manager().get_health_checks())


def static_choices_for_action(
    command_path: tuple[str, ...],
    action: argparse.Action,
    static_choices: dict[str, list[str]],
) -> list[str] | None:
    source_name = static_choice_source_for_action(command_path, action)
    if not source_name:
        return None
    if choices := static_choices.get(source_name):
        return list(choices)
    return None


def static_choice_source_for_action(
    command_path: tuple[str, ...],
    action: argparse.Action,
) -> str | None:
    if action.option_strings:
        if is_config_parameter_action(command_path, action):
            return "config_parameters"
        return None
    return STATIC_POSITIONAL_CHOICE_RULES.get((command_path, action.dest))


def is_config_parameter_action(
    command_path: tuple[str, ...],
    action: argparse.Action,
) -> bool:
    if command_path != ("config",) or not action_takes_value(action):
        return False
    if "KEY" in action_metavars(action):
        return True

    help_text = action.help
    if not isinstance(help_text, str):
        return False
    help_lower = help_text.lower()
    if "configuration" not in help_lower:
        return False
    return "parameter" in help_lower or "value" in help_lower


def action_takes_value(action: argparse.Action) -> bool:
    if isinstance(action.nargs, int):
        return action.nargs != 0
    return action.nargs is None or action.nargs in ("?", "*", "+")


def action_metavars(action: argparse.Action) -> set[str]:
    metavar = action.metavar
    if isinstance(metavar, str):
        return {metavar}
    if isinstance(metavar, tuple):
        return {str(value) for value in metavar}
    return set()


def walk_parser(
    parser: argparse.ArgumentParser,
    command_path: tuple[str, ...] = (),
    aliases: dict[str, AliasSpec] | None = None,
    runtime_sources: dict[str, RuntimeSourceSpec] | None = None,
    static_choices: dict[str, list[str]] | None = None,
) -> CommandSpec:
    """Recursively walk an argparse parser tree into a CommandSpec."""
    options: dict[str, OptionSpec] = {}
    positionals: list[PositionalSpec] = []
    subcommands: dict[str, CommandSpec] = {}
    exclusive_groups: list[list[str]] = []

    if aliases is not None:
        collect_parser_aliases(parser, command_path, aliases)
    if runtime_sources is not None:
        collect_runtime_sources(
            getattr(parser, "completion_runtime_sources", None),
            runtime_sources,
        )

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
                sub_cmd = walk_parser(
                    subparser,
                    command_path=(*command_path, name),
                    aliases=aliases,
                    runtime_sources=runtime_sources,
                    static_choices=static_choices,
                )
                subcommands[name] = CommandSpec(
                    summary=sub_help or sub_cmd.summary,
                    options=sub_cmd.options,
                    positionals=sub_cmd.positionals,
                    subcommands=sub_cmd.subcommands,
                    exclusive_groups=sub_cmd.exclusive_groups,
                )
            continue

        if action.option_strings:
            if runtime_sources is not None:
                collect_runtime_sources(
                    getattr(action, "completion_runtime_sources", None),
                    runtime_sources,
                )
            long_names = [s for s in action.option_strings if s.startswith("--")]
            short_names = [
                s for s in action.option_strings if s.startswith("-") and not s.startswith("--")
            ]
            long_name = long_names[0] if long_names else action.option_strings[-1]
            short_name = short_names[0] if short_names else None

            completion_type = explicit_completion_type(action) or infer_completion_type(
                action.option_strings
            )

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
            static_choice_source = None
            if static_choices:
                static_choice_source = static_choice_source_for_action(command_path, action)
                if static_choice_source:
                    choices = static_choices_for_action(command_path, action, static_choices)

            option = OptionSpec(
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
            option_names = [long_name]
            if static_choice_source:
                option_names = long_names or option_names
            for option_name in option_names:
                options[option_name] = option
        else:
            if action.dest in ("cmd", "subcmd", "_plugin_subcommand"):
                continue
            if runtime_sources is not None:
                collect_runtime_sources(
                    getattr(action, "completion_runtime_sources", None),
                    runtime_sources,
                )

            completion_type = explicit_completion_type(action) or POSITIONAL_TYPE_HEURISTICS.get(
                action.dest
            )
            completion = explicit_completion_spec(action)

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
            elif static_choices:
                choices = static_choices_for_action(command_path, action, static_choices)

            positionals.append(
                PositionalSpec(
                    name=action.dest,
                    choices=choices,
                    nargs=nargs,
                    completion_type=completion_type,
                    completion=completion,
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


def explicit_completion_type(action: argparse.Action) -> str | None:
    """Return plugin-provided scalar completion metadata when present."""
    completion_type = getattr(action, "completion_type", None)
    if isinstance(completion_type, str) and completion_type:
        return completion_type
    return None


def explicit_completion_spec(action: argparse.Action) -> CompletionSpec | None:
    """Return plugin-provided compound completion metadata when present."""
    completion = getattr(action, "completion", None)
    if isinstance(completion, CompletionSpec):
        return completion
    if isinstance(completion, dict):
        return CompletionSpec.from_dict(completion)

    sources = string_list(getattr(action, "completion_sources", None))
    rules = [
        CompletionRule.from_dict(rule)
        for rule in getattr(action, "completion_rules", [])
        if isinstance(rule, dict)
    ]
    if sources or rules:
        return CompletionSpec(sources=sources, rules=rules)
    return None


def collect_parser_aliases(
    parser: argparse.ArgumentParser,
    command_path: tuple[str, ...],
    aliases: dict[str, AliasSpec],
) -> None:
    """Collect plugin-provided executable aliases for this parser node."""
    configured = getattr(parser, "completion_aliases", None)
    if isinstance(configured, dict):
        for name, target in configured.items():
            if isinstance(name, str) and name and target:
                aliases[name] = AliasSpec(target=string_list(target))
        return

    for name in string_list(configured):
        if command_path:
            aliases[name] = AliasSpec(target=list(command_path))


def collect_runtime_sources(
    configured: object,
    runtime_sources: dict[str, RuntimeSourceSpec],
) -> None:
    """Collect plugin-provided runtime candidate source definitions."""
    if not isinstance(configured, dict):
        return

    for name, source in configured.items():
        if not isinstance(name, str) or not name:
            continue
        if isinstance(source, RuntimeSourceSpec):
            runtime_sources[name] = source
        elif isinstance(source, dict):
            runtime_sources[name] = RuntimeSourceSpec.from_dict(source)


def string_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Iterable):
        return [str(item) for item in value if str(item)]
    return []
