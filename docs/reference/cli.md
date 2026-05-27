# CLI reference

`conda completion` has six subcommands.

## `conda completion generate`

Introspect conda's argparse tree and write the completion manifest.

```text
conda completion generate [--no-repodata]
```

Writes to the platform's cache directory (e.g.,
`~/.cache/conda/completion/completion.msgpack` on Linux). See
{doc}`manifest` for paths on all platforms.

`--no-repodata`
: Generate command, flag, and plugin completion data without package
  names or package versions. Runtime contextual completions from project
  files still work.

Runs automatically via `conda_post_commands` when the plugin set
changes after `conda install/remove/update`. Only needed manually
after installing a plugin via pip.

## `conda completion refresh`

Force-refresh package names and versions from conda repodata.

```text
conda completion refresh
```

Use this when a newly published package or version is missing from
completion results. It rewrites `completion.msgpack`, `versions.index`,
and `versions.store`.

## `conda completion install`

Generate the manifest and add the completion hook to your shell's RC
file.

```text
conda completion install [shell] [--yes] [--dry-run] [--no-repodata]
```

shell
: Shell to install for. Auto-detected from `$SHELL` if omitted
  (defaults to PowerShell on Windows).

`--yes`
: Skip the confirmation prompt.

`--dry-run`
: Show what would be written without modifying files. Does not generate
  completion data and does not fetch repodata.

`--no-repodata`
: Generate command completions without package metadata during the
  delegated generation step. Runtime contextual completions from project
  files still work.

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
plugin hash, package-version cache files, and completer binary path.

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
Package versions index: /home/user/.cache/conda/completion/versions.index
  Size: 1048576 bytes
Package versions store: /home/user/.cache/conda/completion/versions.store
  Size: 2621440 bytes
Current plugin hash: a1b2c3d4e5f67890
Completer binary: /home/user/.conda/envs/base/bin/_conda_completer
```

If `Current plugin hash` differs from the manifest's `Plugin hash`,
the manifest is stale and will regenerate on the next
`conda install/remove/update`.
