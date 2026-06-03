"""PowerShell completion script generator."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from . import DEFAULT_COMMAND_NAME, Shell


class PowerShellShell(Shell):
    name = "powershell"
    rc_files = []

    def script(
        self,
        completer_path: Path,
        manifest_path: Path,
        command_name: str = DEFAULT_COMMAND_NAME,
    ) -> str:
        command_name = self.parse_command_name(command_name)
        cp = self.powershell_quote(completer_path)
        mp = self.powershell_quote(manifest_path)
        cn = self.powershell_quote(command_name)
        return f"""\
$CondaCompletionCompleter = {cp}
$CondaCompletionManifest = {mp}
$CondaCompletionCommands = @({cn})
$CondaCompletionCommands += & $CondaCompletionCompleter --aliases --manifest $CondaCompletionManifest 2>$null
Register-ArgumentCompleter -Native -CommandName $CondaCompletionCommands -ScriptBlock {{
    param($wordToComplete, $commandAst, $cursorPosition)
    $completer = $CondaCompletionCompleter
    $manifest = $CondaCompletionManifest
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

    def hook_line(
        self,
        cache_dir: Path | None = None,
        command_name: str = DEFAULT_COMMAND_NAME,
    ) -> str:
        command_name = self.parse_command_name(command_name)
        command = f"{command_name} completion init powershell --command-name {command_name}"
        if cache_dir is not None:
            command = (
                f"{command_name} completion --cache-dir {self.powershell_quote(cache_dir)}"
                f" init powershell --command-name {command_name}"
            )
        return (
            f"if (Get-Command {command_name} -ErrorAction SilentlyContinue)"
            f" {{ {command} | Invoke-Expression }}"
        )

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
