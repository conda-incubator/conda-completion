"""Zsh completion script generator."""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import DEFAULT_COMMAND_NAME, Shell

if TYPE_CHECKING:
    from pathlib import Path


class ZshShell(Shell):
    name = "zsh"
    rc_files = [".zshrc"]

    def script(
        self,
        completer_path: Path,
        manifest_path: Path,
        command_name: str = DEFAULT_COMMAND_NAME,
    ) -> str:
        command_name = self.parse_command_name(command_name)
        cp = self.posix_quote(completer_path)
        mp = self.posix_quote(manifest_path)
        cn = self.posix_quote(command_name)
        return f"""\
_conda_completion_completer={cp}
_conda_completion_manifest={mp}
_conda_completion_command={cn}
_conda() {{
    local completer=$_conda_completion_completer
    local manifest=$_conda_completion_manifest
    local -a items descriptions displays expl
    local has_dir=0
    local has_file=0
    local group name description
    local -i display_width=0 index

    while IFS=$'\\t' read -r group name description || [[ -n "$group" ]]; do
        if [[ "$group" == "__dir__" ]]; then
            has_dir=1
        elif [[ "$group" == "__file__" ]]; then
            has_file=1
        else
            items+=("$name")
            descriptions+=("$description")
            (( ${{#name}} > display_width )) && display_width=${{#name}}
        fi
    done < <("$completer" --shell zsh --manifest "$manifest" -- "${{words[@]}}" $((CURRENT - 1)) 2>/dev/null)

    if (( ${{#items}} )); then
        for (( index = 1; index <= ${{#items}}; index++ )); do
            name=${{items[$index]}}
            description=${{descriptions[$index]}}
            if [[ -n "$description" ]]; then
                displays+=("${{(r:${{display_width}}:: :)name}} -- $description")
            else
                displays+=("$name")
            fi
        done
        _description values expl "$_conda_completion_command"
        compadd -l -d displays "$expl[@]" -- "$items[@]"
    fi
    (( has_dir )) && _path_files -/
    (( has_file )) && _path_files
}}
typeset -ga _conda_completion_aliases
_conda_completion_aliases=($("$_conda_completion_completer" --aliases --manifest "$_conda_completion_manifest" 2>/dev/null))
compdef _conda $_conda_completion_command $_conda_completion_aliases
"""

    def hook_line(
        self,
        cache_dir: Path | None = None,
        command_name: str = DEFAULT_COMMAND_NAME,
    ) -> str:
        command_name = self.parse_command_name(command_name)
        command = f"{command_name} completion init zsh --command-name {command_name}"
        if cache_dir is not None:
            command = (
                f"{command_name} completion --cache-dir {self.posix_quote(cache_dir)}"
                f" init zsh --command-name {command_name}"
            )
        return f'command -v {command_name} &>/dev/null && eval "$({command})"'
