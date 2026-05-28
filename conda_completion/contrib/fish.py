"""Fish completion script generator."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..shell import Shell

if TYPE_CHECKING:
    from pathlib import Path


class FishShell(Shell):
    name = "fish"
    rc_files = [".config/fish/completions/conda.fish"]

    def script(self, completer_path: Path, manifest_path: Path) -> str:
        cp = self.posix_quote(completer_path)
        mp = self.posix_quote(manifest_path)
        return f"""\
function __conda_complete
    set -l completer {cp}
    set -l manifest {mp}
    set -l tokens (commandline -cop)
    set -l cword (count $tokens)
    $completer --shell fish --manifest $manifest -- $tokens (commandline -t) $cword 2>/dev/null
end
complete -c conda -a '(__conda_complete)' -k
"""

    def hook_line(self, cache_dir: Path | None = None) -> str:
        command = "conda completion init fish"
        if cache_dir is not None:
            command = f"conda completion --cache-dir {self.posix_quote(cache_dir)} init fish"
        return f"command -q conda; and {command} | source"
