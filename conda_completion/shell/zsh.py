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
_conda() {{
    local completer={cp}
    local manifest={mp}
    local -a items
    local has_dir=0
    local group rest

    while IFS=$'\\t' read -r group rest || [[ -n "$group" ]]; do
        if [[ "$group" == "__dir__" ]]; then
            has_dir=1
        else
            items+=("$rest")
        fi
    done < <("$completer" --shell zsh --manifest "$manifest" -- "${{words[@]}}" $((CURRENT - 1)) 2>/dev/null)

    (( ${{#items}} )) && _describe 'conda' items
    (( has_dir )) && _path_files -/
}}
compdef _conda conda
"""

    def hook_line(self) -> str:
        return 'command -v conda &>/dev/null && eval "$(conda completion init zsh)"'
