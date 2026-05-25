"""Shell integration scripts for conda-completion.

Tier 1 (``shell/``): bash, zsh, PowerShell -- fully tested in CI.
Tier 2 (``contrib/``): fish -- community-tested, best-effort.

Each shell module provides a Shell subclass with ``script()``,
``hook_line()``, and path quoting appropriate for that shell.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

SHELL_NAMES = frozenset({"bash", "zsh", "fish", "powershell", "pwsh", "cmd"})


class Shell:
    """Base class for shell completion script generators."""

    name: str = ""
    rc_files: list[str] = []

    def script(self, completer_path: Path, manifest_path: Path) -> str:
        raise NotImplementedError

    def hook_line(self) -> str:
        raise NotImplementedError

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
    def posix_quote(path: Path) -> str:
        """Quote a path for safe use in POSIX shells (bash, zsh, fish)."""
        return "'" + path.as_posix().replace("'", "'\\''") + "'"

    @staticmethod
    def powershell_quote(path: Path) -> str:
        """Quote a path for safe use in PowerShell."""
        return "'" + str(path).replace("'", "''") + "'"

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
            processes[pid] = (ppid, os.path.basename(comm).lower())

        pid = str(os.getpid())
        for _ in range(10):
            info = processes.get(pid)
            if info is None:
                break
            ppid, name = info
            # Login shells show as "-zsh", "-bash", etc.
            if name.startswith("-"):
                name = name[1:]
            if name in SHELL_NAMES:
                return name
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
            return Path(override).stem

        shell = Shell.detect_parent_shell()
        if shell:
            return shell

        shell_path = os.environ.get("SHELL", "")
        if shell_path:
            return Path(shell_path).name
        if sys.platform == "win32":
            return "powershell"
        return "bash"


def get_shell_registry() -> dict[str, Shell]:
    """Return a mapping of shell name to Shell instance (Tier 1 + Tier 2)."""
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
