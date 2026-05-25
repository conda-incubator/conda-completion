"""``conda completion install`` -- generate + install shell RC hook."""

from __future__ import annotations

import logging
import shutil
from typing import TYPE_CHECKING

from ..exceptions import ShellNotSupportedError
from ..shell import Shell, get_shell_registry

if TYPE_CHECKING:
    import argparse

log = logging.getLogger(__name__)

_BLOCK_START = "# >>> conda-completion >>>"
_BLOCK_END = "# <<< conda-completion <<<"


def execute_install(args: argparse.Namespace) -> int:
    """Generate completions and install a shell RC hook."""
    registry = get_shell_registry()
    shell_name = args.shell or Shell.detect_shell()

    if shell_name not in registry:
        raise ShellNotSupportedError(shell_name, list(registry))

    shell = registry[shell_name]
    rc_path = shell.default_rc_path()
    if rc_path is None:
        log.error("Cannot determine RC file for %s", shell_name)
        return 1

    hook_line = shell.hook_line()
    block = f"{_BLOCK_START}\n{hook_line}\n{_BLOCK_END}\n"

    if rc_path.exists():
        content = rc_path.read_text(encoding="utf-8")
        if _BLOCK_START in content:
            print(f"conda-completion hook already present in {rc_path}")
            return 0
    else:
        content = ""

    if args.dry_run:
        print(f"Would append to {rc_path}:\n\n  {hook_line}\n")
        return 0

    if not args.yes:
        print(f"Will append to {rc_path}:\n\n  {hook_line}\n")
        response = input("Proceed? [y/N] ")
        if response.lower() not in ("y", "yes"):
            print("Aborted.")
            return 1

    from .generate import execute_generate

    execute_generate(args)

    rc_path.parent.mkdir(parents=True, exist_ok=True)
    with open(rc_path, "a", encoding="utf-8") as f:
        f.write(f"\n{block}")

    print(f"Completion hook installed in {rc_path}")
    source_cmd = source_command(shell_name, rc_path)
    print(f"To activate, restart your shell or run:\n  {source_cmd}")

    if not shutil.which("conda"):
        print(
            "\nNote: conda is not on PATH."
            " The completion hook requires conda to be available at shell startup."
            "\nEither run 'conda init' or add conda to your PATH in"
            f" {rc_path} before the completion hook."
        )

    return 0


def source_command(shell_name: str, rc_path) -> str:
    if shell_name == "powershell":
        return ". $PROFILE"
    return f"source {rc_path}"
