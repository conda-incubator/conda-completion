# Setting up PowerShell completion

This guide walks through setting up conda tab completion in PowerShell.

## Prerequisites

- conda 25.1 or later
- PowerShell 5.1 or later (PowerShell 7+ recommended)

## Install conda-completion

```powershell
conda install -c conda-forge conda-completion
```

## Activate completion

### Option A: automatic install

```powershell
conda completion install
```

This detects PowerShell automatically and adds a delimited block to
your profile. Preview with:

```powershell
conda completion install --dry-run
```

### Option B: manual setup

Add this line to your PowerShell profile (`$PROFILE`):

```powershell
conda completion init powershell | Invoke-Expression
```

## Verify

Open a new PowerShell session and try:

```text
PS> conda install -<TAB>
--channel     --dry-run     --name        --prefix      ...
```

:::{tip}
PowerShell renders completions using `CompletionResult` objects, which
support descriptions and different completion types (parameter values,
commands, etc.).
:::

## Profile locations

conda-completion checks these paths for your PowerShell profile:

| Platform | Path |
| --- | --- |
| Windows | `~/Documents/PowerShell/Microsoft.PowerShell_profile.ps1` |
| Windows (5.1) | `~/Documents/WindowsPowerShell/Microsoft.PowerShell_profile.ps1` |
| macOS/Linux | `~/.config/powershell/Microsoft.PowerShell_profile.ps1` |

## Uninstall

```powershell
conda completion uninstall
```
