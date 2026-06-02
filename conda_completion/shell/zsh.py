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
_conda_completion_completer={cp}
_conda_completion_manifest={mp}
_conda() {{
    local completer=$_conda_completion_completer
    local manifest=$_conda_completion_manifest
    local -a items
    local has_dir=0
    local has_file=0
    local group rest

    while IFS=$'\\t' read -r group rest || [[ -n "$group" ]]; do
        if [[ "$group" == "__dir__" ]]; then
            has_dir=1
        elif [[ "$group" == "__file__" ]]; then
            has_file=1
        else
            items+=("$rest")
        fi
    done < <("$completer" --shell zsh --manifest "$manifest" -- "${{words[@]}}" $((CURRENT - 1)) 2>/dev/null)

    (( ${{#items}} )) && _describe 'conda' items
    (( has_dir )) && _path_files -/
    (( has_file )) && _path_files
}}
typeset -ga _conda_completion_aliases
_conda_completion_aliases=($("$_conda_completion_completer" --aliases --manifest "$_conda_completion_manifest" 2>/dev/null))
compdef _conda conda $_conda_completion_aliases
"""

    def hook_line(self, cache_dir: Path | None = None) -> str:
        command = "conda completion init zsh"
        if cache_dir is not None:
            command = f"conda completion --cache-dir {self.posix_quote(cache_dir)} init zsh"
        return f'command -v conda &>/dev/null && eval "$({command})"'
