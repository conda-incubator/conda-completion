# CLI reference

conda-completion adds the `conda completion` subcommand with four
sub-subcommands.

## `conda completion generate`

Introspect conda's argparse tree and write the completion manifest.

```text
conda completion generate
```

The manifest is written to the platform's cache directory (e.g.,
`~/.cache/conda/completion/completion.toml` on Linux). See
{doc}`manifest` for paths on all platforms.

This command runs automatically via the `conda_post_commands` hook when
the set of installed plugins changes after `conda install`, `conda
remove`, or `conda update`. You only need to run it manually after
installing a plugin via pip.

## `conda completion install`

Generate the manifest (if needed) and add the completion hook to your
shell's RC file.

```text
conda completion install [shell] [--yes] [--dry-run]
```

shell
: The shell to install for. If omitted, detected from `$SHELL` (or
  defaults to PowerShell on Windows).

`--yes`
: Skip the confirmation prompt.

`--dry-run`
: Show what would be written without modifying any files.

The command is idempotent: running it twice does not duplicate the hook.

## `conda completion uninstall`

Remove the completion hook from your shell's RC file.

```text
conda completion uninstall [shell]
```

shell
: The shell to uninstall for. If omitted, detected from `$SHELL`.

## `conda completion init`

Print the shell completion script to stdout. This is used inside eval
statements in RC files.

```text
conda completion init <shell>
```

shell (required)
: One of `bash`, `zsh`, `powershell`, `fish`.

### Examples

```bash
# bash / zsh
eval "$(conda completion init bash)"

# PowerShell
conda completion init powershell | Invoke-Expression

# fish
conda completion init fish | source
```

## Standalone entry point

conda-completion also provides a `cc` command for standalone use outside
of conda:

```text
cc generate
cc install [shell] [--yes] [--dry-run]
cc uninstall [shell]
cc init <shell>
```

This is useful in environments where conda is not on `PATH` but the
conda-completion package is installed.
