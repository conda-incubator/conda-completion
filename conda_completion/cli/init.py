"""``conda completion init`` -- print the completion script to stdout."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from conda_completer import find_completer_binary

from ..exceptions import (
    CompleterBinaryNotFoundError,
    ManifestNotFoundError,
    ShellNotSupportedError,
)
from ..paths import manifest_path
from ..shell import Shell, get_shell_registry

if TYPE_CHECKING:
    import argparse


def execute_init(args: argparse.Namespace) -> int:
    """Print the shell completion script to stdout."""
    registry = get_shell_registry()
    shell_name = args.shell
    command_name = Shell.resolve_command_name(getattr(args, "command_name", None))

    if shell_name not in registry:
        raise ShellNotSupportedError(shell_name, list(registry))

    mpath = manifest_path()
    if not mpath.exists():
        raise ManifestNotFoundError()

    try:
        completer_path = find_completer_binary()
    except FileNotFoundError:
        raise CompleterBinaryNotFoundError()

    shell = registry[shell_name]
    script = shell.script(completer_path, mpath, command_name)
    sys.stdout.write(script)
    return 0
