"""Shell integration scripts for conda-completion.

Each shell module provides a Shell subclass with ``script()``,
``hook_line()``, and path quoting appropriate for that shell.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

from ..exceptions import CommandNameError

COMMAND_NAME_ENV_VAR = "CONDA_COMPLETION_COMMAND_NAME"
DEFAULT_COMMAND_NAME = "conda"
COMMAND_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

SHELL_ALIASES = {
    "bash": "bash",
    "zsh": "zsh",
    "fish": "fish",
    "powershell": "powershell",
    "pwsh": "powershell",
}


class Shell:
    """Base class for shell completion script generators."""

    name: str = ""
    rc_files: list[str] = []

    def script(
        self,
        completer_path: Path,
        manifest_path: Path,
        command_name: str = DEFAULT_COMMAND_NAME,
    ) -> str:
        raise NotImplementedError

    def hook_line(
        self,
        cache_dir: Path | None = None,
        command_name: str = DEFAULT_COMMAND_NAME,
    ) -> str:
        raise NotImplementedError

    def rc_path(self, command_name: str = DEFAULT_COMMAND_NAME) -> Path | None:
        return self.default_rc_path()

    def default_rc_path(self) -> Path | None:
        home = Path.home()
        existing = next(
            (home / rc for rc in self.rc_files if (home / rc).exists()),
            None,
        )
        if existing is not None:
            return existing
        return home / self.rc_files[0] if self.rc_files else None

    @staticmethod
    def posix_quote(value: Path | str) -> str:
        """Quote a path for safe use in POSIX shells (bash, zsh, fish)."""
        text = value.as_posix() if isinstance(value, Path) else value
        return "'" + text.replace("'", "'\\''") + "'"

    @staticmethod
    def powershell_quote(value: Path | str) -> str:
        """Quote a path for safe use in PowerShell."""
        return "'" + str(value).replace("'", "''") + "'"

    @staticmethod
    def parse_command_name(command_name: str) -> str:
        """Validate and normalize the shell command name used for completion."""
        value = command_name.strip()
        if not COMMAND_NAME_PATTERN.fullmatch(value):
            raise CommandNameError(command_name)
        return value

    @staticmethod
    def resolve_command_name(explicit: str | None = None) -> str:
        """Resolve command name precedence: CLI option, env var, then default."""
        if explicit:
            return Shell.parse_command_name(explicit)
        override = os.environ.get(COMMAND_NAME_ENV_VAR, "")
        if override:
            return Shell.parse_command_name(override)
        return DEFAULT_COMMAND_NAME

    @staticmethod
    def normalize_shell_name(name: str) -> str | None:
        """Return the supported shell name for a process name, if any."""
        shell_name = os.path.basename(name).lower()
        if shell_name.startswith("-"):
            shell_name = shell_name[1:]
        if shell_name.endswith(".exe"):
            shell_name = shell_name[:-4]
        return SHELL_ALIASES.get(shell_name)

    @staticmethod
    def detect_parent_shell() -> str | None:
        """Walk the process tree via ``ps`` to find the nearest parent shell.

        Returns the shell name if found, or ``None`` when ``ps`` is
        unavailable (e.g. native Windows without Git Bash).

        Approach inspired by shellingham (ISC license):
        https://github.com/sarugaku/shellingham
        """
        try:
            output = subprocess.check_output(
                ["ps", "-ww", "-o", "pid=", "-o", "ppid=", "-o", "comm="],
                text=True,
                stderr=subprocess.DEVNULL,
            )
        except (OSError, subprocess.CalledProcessError):
            return None

        processes: dict[str, tuple[str, str]] = {}
        for line in output.splitlines():
            parts = line.strip().split(None, 2)
            if len(parts) < 3:
                continue
            pid, ppid, comm = parts
            processes[pid] = (ppid, comm)

        pid = str(os.getpid())
        for _ in range(10):
            info = processes.get(pid)
            if info is None:
                break
            ppid, name = info
            shell_name = Shell.normalize_shell_name(name)
            if shell_name:
                return shell_name
            pid = ppid

        return None

    @staticmethod
    def detect_shell() -> str:
        """Detect the current shell from the environment.

        Priority: ``CONDA_COMPLETION_SHELL`` env var, then process tree
        walking, then ``SHELL`` env var, then platform default.
        """
        override = os.environ.get("CONDA_COMPLETION_SHELL", "")
        if override:
            return Shell.normalize_shell_name(override) or Path(override).stem

        shell = Shell.detect_parent_shell()
        if shell:
            return shell

        shell_path = os.environ.get("SHELL", "")
        if shell_path:
            return Shell.normalize_shell_name(shell_path) or Path(shell_path).name
        if sys.platform == "win32":
            return "powershell"
        return "bash"


def get_shell_registry() -> dict[str, Shell]:
    """Return a mapping of supported shell name to Shell instance."""
    from .bash import BashShell
    from .powershell import PowerShellShell
    from .zsh import ZshShell

    registry: dict[str, Shell] = {
        "bash": BashShell(),
        "zsh": ZshShell(),
        "powershell": PowerShellShell(),
    }

    try:
        from ..contrib.fish import FishShell

        registry["fish"] = FishShell()
    except ImportError:
        pass

    return registry
