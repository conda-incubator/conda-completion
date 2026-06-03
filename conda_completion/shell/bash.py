"""Bash completion script generator."""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import DEFAULT_COMMAND_NAME, Shell

if TYPE_CHECKING:
    from pathlib import Path


class BashShell(Shell):
    name = "bash"
    rc_files = [".bashrc", ".bash_profile"]

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
_conda_completion() {{
    local completer=$_conda_completion_completer
    local manifest=$_conda_completion_manifest
    mapfile -t COMPREPLY < <("$completer" --shell bash --manifest "$manifest" -- "${{COMP_WORDS[@]}}" "$COMP_CWORD" 2>/dev/null)
    compopt -o nosort 2>/dev/null
}}
COMP_WORDBREAKS="${{COMP_WORDBREAKS//=/}}"
complete -o default -F _conda_completion "$_conda_completion_command"
while IFS= read -r alias_name; do
    [[ -n "$alias_name" ]] && complete -o default -F _conda_completion "$alias_name"
done < <("$_conda_completion_completer" --aliases --manifest "$_conda_completion_manifest" 2>/dev/null)
"""

    def hook_line(
        self,
        cache_dir: Path | None = None,
        command_name: str = DEFAULT_COMMAND_NAME,
    ) -> str:
        command_name = self.parse_command_name(command_name)
        command = f"{command_name} completion init bash --command-name {command_name}"
        if cache_dir is not None:
            command = (
                f"{command_name} completion --cache-dir {self.posix_quote(cache_dir)}"
                f" init bash --command-name {command_name}"
            )
        return f'command -v {command_name} &>/dev/null && eval "$({command})"'
