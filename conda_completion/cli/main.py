"""Argument parser and dispatch for conda-completion CLI."""

from __future__ import annotations

import argparse


def configure_parser(
    parser: argparse.ArgumentParser | None = None,
) -> argparse.ArgumentParser:
    """Build the argument parser for ``conda completion``."""
    if parser is None:
        parser = argparse.ArgumentParser(
            prog="conda completion",
            description="Generate and install shell tab completions for conda.",
        )

    parser.add_argument("--json", action="store_true", default=False, help=argparse.SUPPRESS)

    sub = parser.add_subparsers(dest="subcmd")

    sub.add_parser(
        "generate",
        help="Introspect conda's parser and write the completion manifest",
    )

    p_install = sub.add_parser(
        "install",
        help="Generate completions and install a shell RC hook",
    )
    p_install.add_argument(
        "shell",
        nargs="?",
        help="Shell to install for (auto-detected if omitted)",
    )
    p_install.add_argument(
        "--yes",
        "-y",
        action="store_true",
        default=False,
        help="Skip confirmation prompt",
    )
    p_install.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Show what would be written without modifying files",
    )

    p_uninstall = sub.add_parser(
        "uninstall",
        help="Remove the completion hook from a shell RC file",
    )
    p_uninstall.add_argument(
        "shell",
        nargs="?",
        help="Shell to uninstall from (auto-detected if omitted)",
    )
    p_uninstall.add_argument(
        "--yes",
        "-y",
        action="store_true",
        default=False,
        help="Skip confirmation prompt",
    )
    p_uninstall.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Show what would be removed without modifying files",
    )

    p_init = sub.add_parser(
        "init",
        help="Print the completion script to stdout",
    )
    p_init.add_argument(
        "shell",
        help="Shell to generate the script for",
    )

    sub.add_parser(
        "status",
        help="Show completion system status and diagnostics",
    )

    return parser


def execute(args: argparse.Namespace) -> int:
    """Dispatch to the appropriate subcommand handler."""
    from ..exceptions import CondaCompletionError

    subcmd = getattr(args, "subcmd", None)
    if not subcmd:
        configure_parser().print_help()
        return 0

    try:
        if subcmd == "generate":
            from .generate import execute_generate

            return execute_generate(args)
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
            configure_parser().print_help()
            return 1
    except CondaCompletionError as exc:
        import logging

        log = logging.getLogger(__name__)
        log.error(str(exc))
        for hint in getattr(exc, "hints", []):
            log.info("  hint: %s", hint)
        return 1
