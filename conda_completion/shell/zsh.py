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
    local -a subcmds options packages environments channels tasks tools versions choices
    local has_dir=0
    local group rest
    while IFS=$'\\t' read -r group rest || [[ -n "$group" ]]; do
        case "$group" in
            subcommand) subcmds+=("$rest") ;;
            option) options+=("$rest") ;;
            package) packages+=("$rest") ;;
            environment) environments+=("$rest") ;;
            channel) channels+=("$rest") ;;
            task) tasks+=("$rest") ;;
            tool) tools+=("$rest") ;;
            version) versions+=("$rest") ;;
            choice) choices+=("$rest") ;;
            __dir__) has_dir=1 ;;
        esac
    done < <("$completer" --shell zsh --manifest "$manifest" -- "${{words[@]}}" $((CURRENT - 1)) 2>/dev/null)
    (( ${{#subcmds}} )) && _describe -V -t commands 'command' subcmds
    (( ${{#options}} )) && _describe -V -t options 'option' options
    (( ${{#packages}} )) && _describe -V -t packages 'package' packages
    (( ${{#environments}} )) && _describe -V -t environments 'environment' environments
    (( ${{#channels}} )) && _describe -V -t channels 'channel' channels
    (( ${{#tasks}} )) && _describe -V -t tasks 'task' tasks
    (( ${{#tools}} )) && _describe -V -t tools 'tool' tools
    (( ${{#versions}} )) && _describe -V -t versions 'version' versions
    (( ${{#choices}} )) && _describe -V -t choices 'choice' choices
    (( has_dir )) && _path_files -/
}}
compdef _conda conda
"""

    def hook_line(self) -> str:
        return 'command -v conda &>/dev/null && eval "$(conda completion init zsh)"'
