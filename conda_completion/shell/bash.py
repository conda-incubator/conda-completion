"""Bash completion script generator."""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import Shell

if TYPE_CHECKING:
    from pathlib import Path


class BashShell(Shell):
    name = "bash"
    rc_files = [".bashrc", ".bash_profile"]

    def script(self, completer_path: Path, manifest_path: Path) -> str:
        cp = self.posix_quote(completer_path)
        mp = self.posix_quote(manifest_path)
        return f"""\
_conda_completion() {{
    local completer={cp}
    local manifest={mp}
    COMPREPLY=( $("$completer" --shell bash --manifest "$manifest" -- "${{COMP_WORDS[@]}}" "$COMP_CWORD" 2>/dev/null) )
}}
complete -o default -F _conda_completion conda
"""

    def hook_line(self) -> str:
        return 'eval "$(conda completion init bash)"'
