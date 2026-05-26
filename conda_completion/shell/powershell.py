"""PowerShell completion script generator."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from . import Shell


class PowerShellShell(Shell):
    name = "powershell"
    rc_files = []

    def script(self, completer_path: Path, manifest_path: Path) -> str:
        cp = self.powershell_quote(completer_path)
        mp = self.powershell_quote(manifest_path)
        return f"""\
Register-ArgumentCompleter -Native -CommandName conda -ScriptBlock {{
    param($wordToComplete, $commandAst, $cursorPosition)
    $completer = {cp}
    $manifest = {mp}
    $words = @($commandAst.CommandElements | ForEach-Object {{ $_.Extent.Text }})
    $cword = $words.Length - 1
    & $completer --shell powershell --manifest $manifest -- $words $cword |
        ForEach-Object {{
            $parts = $_ -split "`t", 2
            if ($parts.Length -eq 2) {{
                [System.Management.Automation.CompletionResult]::new(
                    $parts[0], $parts[0], 'ParameterValue', $parts[1])
            }} else {{
                [System.Management.Automation.CompletionResult]::new(
                    $_, $_, 'ParameterValue', $_)
            }}
        }}
}}
"""

    def hook_line(self) -> str:
        return "if (Get-Command conda -ErrorAction SilentlyContinue) { conda completion init powershell | Invoke-Expression }"

    def default_rc_path(self) -> Path | None:
        home = Path.home()

        if sys.platform == "win32":
            docs = Path(os.environ.get("USERPROFILE") or str(home)) / "Documents"
            candidates = [
                docs / "PowerShell" / "Microsoft.PowerShell_profile.ps1",
                docs / "WindowsPowerShell" / "Microsoft.PowerShell_profile.ps1",
            ]
        else:
            candidates = [
                home / ".config" / "powershell" / "Microsoft.PowerShell_profile.ps1",
            ]

        return next(
            (c for c in candidates if c.exists()),
            candidates[0] if candidates else None,
        )
