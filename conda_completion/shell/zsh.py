"""Zsh completion script generator."""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import Shell

if TYPE_CHECKING:
    from pathlib import Path


class ZshShell(Shell):
    name = "zsh"
    rc_files = [".zshrc"]

    def script(self, completer_path: Path, manifest_path: Path) -> str:
        cp = self.posix_quote(completer_path)
        mp = self.posix_quote(manifest_path)
        return f"""\
#compdef conda
_conda() {{
    local completer={cp}
    local manifest={mp}
    local -a completions
    completions=("${{(@f)$("$completer" --shell zsh --manifest "$manifest" -- "${{words[@]}}" $CURRENT 2>/dev/null)}}")
    _describe -V 'conda' completions
}}
"""

    def hook_line(self) -> str:
        return 'command -v conda &>/dev/null && eval "$(conda completion init zsh)"'
