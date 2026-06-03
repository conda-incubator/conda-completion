"""Argument parser and dispatch for conda-completion CLI."""

from __future__ import annotations

import argparse

from conda.common.constants import NULL

from ..exceptions import CommandNameError
from ..shell import COMMAND_NAME_ENV_VAR, DEFAULT_COMMAND_NAME, Shell


def command_name_arg(value: str) -> str:
    try:
        return Shell.parse_command_name(value)
    except CommandNameError as exc:
        raise argparse.ArgumentTypeError(exc.error_message) from exc


def add_command_name_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--command-name",
        metavar="NAME",
        type=command_name_arg,
        default=None,
        help=(
            f"Register completions for this executable name "
            f"(default: {DEFAULT_COMMAND_NAME}; env: {COMMAND_NAME_ENV_VAR})"
        ),
    )


def configure_parser(parser: argparse.ArgumentParser) -> None:
    """Configure the parser for ``conda completion``."""
    parser.add_argument("--json", action="store_true", default=NULL, help=argparse.SUPPRESS)
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        default=NULL,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--cache-dir",
        metavar="PATH",
        default=None,
        help="Store completion cache files in this directory",
    )

    sub = parser.add_subparsers(dest="subcmd")

    generate_parser = sub.add_parser(
        "generate",
        help="Introspect conda's parser and write the completion manifest",
    )
    generate_parser.add_argument(
        "--no-repodata",
        action="store_true",
        default=False,
        help="Generate command completions without package metadata from repodata",
    )

    sub.add_parser(
        "refresh",
        help="Refresh package metadata from conda repodata",
    )

    install_parser = sub.add_parser(
        "install",
        help="Generate completions and install a shell RC hook",
    )
    install_parser.add_argument(
        "shell",
        nargs="?",
        help="Shell to install for (auto-detected if omitted)",
    )
    install_parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        default=False,
        help="Skip confirmation prompt",
    )
    install_parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Show what would be written without modifying files",
    )
    install_parser.add_argument(
        "--no-repodata",
        action="store_true",
        default=False,
        help="Generate command completions without package metadata from repodata",
    )
    add_command_name_option(install_parser)

    uninstall_parser = sub.add_parser(
        "uninstall",
        help="Remove the completion hook from a shell RC file",
    )
    uninstall_parser.add_argument(
        "shell",
        nargs="?",
        help="Shell to uninstall from (auto-detected if omitted)",
    )
    uninstall_parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        default=False,
        help="Skip confirmation prompt",
    )
    uninstall_parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Show what would be removed without modifying files",
    )
    add_command_name_option(uninstall_parser)

    init_parser = sub.add_parser(
        "init",
        help="Print the completion script to stdout",
    )
    init_parser.add_argument(
        "shell",
        help="Shell to generate the script for",
    )
    add_command_name_option(init_parser)

    sub.add_parser(
        "status",
        help="Show completion system status and diagnostics",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the standalone parser for ``conda completion``."""
    parser = argparse.ArgumentParser(
        prog="conda completion",
        description="Generate and install shell tab completions for conda.",
    )
    configure_parser(parser)
    return parser


def execute(args: argparse.Namespace) -> int:
    """Dispatch to the appropriate subcommand handler."""
    from ..exceptions import CondaCompletionError
    from ..paths import set_cache_dir_override

    cache_dir = set_cache_dir_override(getattr(args, "cache_dir", None))
    if cache_dir is not None:
        args.cache_dir = cache_dir

    subcmd = getattr(args, "subcmd", None)
    if not subcmd:
        build_parser().print_help()
        return 0

    try:
        if subcmd == "generate":
            from .generate import execute_generate

            return execute_generate(args)
        elif subcmd == "refresh":
            from .refresh import execute_refresh

            return execute_refresh(args)
        elif subcmd == "install":
            from .install import execute_install

            return execute_install(args)
        elif subcmd == "uninstall":
            from .uninstall import execute_uninstall

            return execute_uninstall(args)
        elif subcmd == "init":
            from .init import execute_init

            return execute_init(args)
        elif subcmd == "status":
            from .status import execute_status

            return execute_status(args)
        else:
            build_parser().print_help()
            return 1
    except CondaCompletionError as exc:
        import logging

        log = logging.getLogger(__name__)
        log.error(str(exc))
        for hint in getattr(exc, "hints", []):
            log.info("  hint: %s", hint)
        return 1
