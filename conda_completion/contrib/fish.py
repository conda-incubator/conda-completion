"""Fish completion script generator (Tier 2)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..shell import Shell

if TYPE_CHECKING:
    from pathlib import Path


class FishShell(Shell):
    name = "fish"
    rc_files = [".config/fish/config.fish"]

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

    def hook_line(self) -> str:
        return "conda completion init fish | source"
