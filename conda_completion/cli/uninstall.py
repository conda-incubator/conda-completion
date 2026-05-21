"""``conda completion uninstall`` -- remove the shell RC hook."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from ..exceptions import ShellNotSupportedError
from ..shell import Shell, get_shell_registry

if TYPE_CHECKING:
    import argparse

_BLOCK_PATTERN = re.compile(
    r"\n?# >>> conda-completion >>>\n(?:[^\n]*\n)*?# <<< conda-completion <<<\n?",
)


def execute_uninstall(args: argparse.Namespace) -> int:
    """Remove the conda-completion hook from a shell RC file."""
    registry = get_shell_registry()
    shell_name = args.shell or Shell.detect_shell()

    if shell_name not in registry:
        raise ShellNotSupportedError(shell_name, list(registry))

    shell = registry[shell_name]
    rc_path = shell.default_rc_path()
    if rc_path is None or not rc_path.exists():
        print(f"No RC file found for {shell_name}")
        return 0

    content = rc_path.read_text(encoding="utf-8")
    new_content = _BLOCK_PATTERN.sub("", content)

    if new_content == content:
        print(f"No conda-completion hook found in {rc_path}")
        return 0

    dry_run = getattr(args, "dry_run", False)
    yes = getattr(args, "yes", False)

    if dry_run:
        print(f"Would remove conda-completion hook from {rc_path}")
        return 0

    if not yes:
        response = input(f"Remove completion hook from {rc_path}? [y/N] ")
        if response.lower() not in ("y", "yes"):
            print("Aborted.")
            return 1

    rc_path.write_text(new_content, encoding="utf-8")
    print(f"Completion hook removed from {rc_path}")
    return 0
