# Install in nonstandard shell startup files

Use this guide when `conda completion install` writes to the wrong file,
your editor launches a different shell startup mode, or you keep shell
configuration in a framework-managed file.

## Know what the installer does

`conda completion install` detects a shell, generates completion data,
and appends a delimited block to that shell's default startup file.

The installed block runs `conda completion init <shell>` at shell startup.
The `init` command prints the shell-specific completion function with the
current manifest and Rust binary paths baked in for that shell session.

Prefer the short `init` eval line over pasting the full generated script.
If you paste the full generated script, replace it after moving the
environment that provides `conda-completion`.

## Pick the shell explicitly

When auto-detection is wrong, pass the shell:

```bash
conda completion install zsh
```

Use `bash`, `zsh`, `powershell`, or `fish` as the shell argument.

In scripts, you can also set:

```bash
CONDA_COMPLETION_SHELL=zsh conda completion install --yes
```

## Add the hook manually

Add the relevant line to the startup file that your terminal actually
loads.

:::::{tab-set}

::::{tab-item} bash

```bash
eval "$(conda completion init bash)"
```

::::

::::{tab-item} zsh

```zsh
eval "$(conda completion init zsh)"
```

::::

::::{tab-item} PowerShell

```powershell
conda completion init powershell | Invoke-Expression
```

::::

::::{tab-item} fish

```fish
conda completion init fish | source
```

::::

:::::

Put the hook after any {external+conda:doc}`conda init <commands/init>`
block or custom PATH setup so the `conda` command exists before the hook
runs.

## Bash login shells on macOS

macOS Terminal may start bash as a login shell. Login bash reads
`~/.bash_profile`, while interactive non-login bash reads `~/.bashrc`.

A common pattern is to keep interactive setup in `~/.bashrc` and source
it from `~/.bash_profile`:

```bash
if [ -f ~/.bashrc ]; then
    . ~/.bashrc
fi
```

Then put the conda-completion hook in `~/.bashrc`.

## Zsh frameworks

For Oh My Zsh, Prezto, Antidote, or Zinit setups, put the hook in the
file that runs after plugins and after the conda initialization block.
That is commonly `~/.zshrc`.

If another plugin defines a completion for the same command, load
conda-completion after it so the final `compdef _conda ...` registration
wins for the configured command name and any manifest-provided aliases.

## PowerShell profiles

PowerShell has several profile paths. `conda completion install
powershell` writes to the first relevant user profile path for the
platform.

To see the profile loaded by the current host:

```powershell
$PROFILE
```

Create the file if needed:

```powershell
New-Item -ItemType File -Force $PROFILE
```

Then add:

```powershell
conda completion init powershell | Invoke-Expression
```

## Fish completions

The installer writes a conda-completion block to:

```text
~/.config/fish/completions/conda.fish
```

You can use `~/.config/fish/config.fish` instead if you prefer a single
startup file:

```fish
conda completion init fish | source
```

If fish's built-in conda completions are also installed, conda-completion
should be loaded last.

## IDE and remote shells

Run installation inside the environment where the terminal executes:

- Remote SSH: install on the remote host.
- WSL: install inside WSL.
- Dev containers and Codespaces: install inside the container.
- JetBrains Gateway: install on the remote backend.

If the IDE config points to a custom shell path, install for that shell
or add the manual hook to the file that shell reads.
