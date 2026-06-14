"""Fish completion script generator."""

from __future__ import annotations

from pathlib import Path

from ..shell import DEFAULT_COMMAND_NAME, Shell


class FishShell(Shell):
    name = "fish"
    rc_files = [".config/fish/completions/conda.fish"]

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
set -g __conda_completion_completer {cp}
set -g __conda_completion_manifest {mp}
set -g __conda_completion_command {cn}
function __conda_complete
    set -l completer $__conda_completion_completer
    set -l manifest $__conda_completion_manifest
    set -l tokens (commandline -cop)
    set -l cword (count $tokens)
    $completer --shell fish --manifest $manifest -- $tokens (commandline -t) $cword 2>/dev/null
end
complete -c $__conda_completion_command -a '(__conda_complete)' -k
for alias_name in ($__conda_completion_completer --aliases --manifest $__conda_completion_manifest 2>/dev/null)
    complete -c $alias_name -a '(__conda_complete)' -k
end
"""

    def hook_line(
        self,
        cache_dir: Path | None = None,
        command_name: str = DEFAULT_COMMAND_NAME,
    ) -> str:
        command_name = self.parse_command_name(command_name)
        command = f"{command_name} completion init fish --command-name {command_name}"
        if cache_dir is not None:
            command = (
                f"{command_name} completion --cache-dir {self.posix_quote(cache_dir)}"
                f" init fish --command-name {command_name}"
            )
        return f"command -q {command_name}; and {command} | source"

    def rc_path(self, command_name: str = DEFAULT_COMMAND_NAME) -> Path | None:
        command_name = self.parse_command_name(command_name)
        return Path.home() / ".config" / "fish" / "completions" / f"{command_name}.fish"
