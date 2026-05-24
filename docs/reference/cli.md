# CLI reference

`conda completion` has five subcommands.

## `conda completion generate`

Introspect conda's argparse tree and write the completion manifest.

```text
conda completion generate
```

Writes to the platform's cache directory (e.g.,
`~/.cache/conda/completion/completion.msgpack` on Linux). See
{doc}`manifest` for paths on all platforms.

Runs automatically via `conda_post_commands` when the plugin set
changes after `conda install/remove/update`. Only needed manually
after installing a plugin via pip.

## `conda completion install`

Generate the manifest (if needed) and add the completion hook to your
shell's RC file.

```text
conda completion install [shell] [--yes] [--dry-run]
```

shell
: Shell to install for. Auto-detected from `$SHELL` if omitted
  (defaults to PowerShell on Windows).

`--yes`
: Skip the confirmation prompt.

`--dry-run`
: Show what would be written without modifying files.

Idempotent: running it twice does not duplicate the hook.

## `conda completion uninstall`

Remove the completion hook from your shell's RC file.

```text
conda completion uninstall [shell]
```

shell
: Shell to uninstall for. Auto-detected from `$SHELL` if omitted.

## `conda completion init`

Print the shell completion script to stdout, for use in eval statements.

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

## `conda completion status`

Show diagnostics: manifest location, age, size, command/package counts,
plugin hash, and completer binary path.

```text
conda completion status
```

Example output:

```text
Cache directory: /home/user/.cache/conda/completion
Manifest: /home/user/.cache/conda/completion/completion.msgpack
  Last generated: 3 minutes ago (245760 bytes)
  Commands: 42
  Packages: 28540
  Plugin hash: a1b2c3d4e5f67890
Versions: /home/user/.cache/conda/completion/versions.msgpack
  Size: 2621440 bytes
Current plugin hash: a1b2c3d4e5f67890
Completer binary: /home/user/.conda/envs/base/bin/_conda_completer
```

If `Current plugin hash` differs from the manifest's `Plugin hash`,
the manifest is stale and will regenerate on the next
`conda install/remove/update`.
