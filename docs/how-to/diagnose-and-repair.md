# Diagnose and repair completion problems

Use this guide when completion is installed but the behavior does not
match what you expect.

## Start with status

Run status in the same terminal where completion is failing:

```bash
conda completion status
```

Save the output while debugging. It shows the cache directory, manifest
path, manifest age, package metadata files, plugin hash, current plugin
hash, and completer binary path.

## Check whether the shell hook is loaded

If pressing TAB behaves exactly like ordinary file completion, the shell
probably did not load the conda-completion hook.

Preview where the hook would be installed:

```bash
conda completion install --dry-run
```

Then install for the shell you are actually using. For example:

```bash
conda completion install zsh
```

Use `bash`, `zsh`, `powershell`, or `fish` as the shell argument.

Restart the terminal after installation. If you cannot restart it, source
the file named by the installer.

For custom startup layouts, use {doc}`nonstandard-shell-startup`.

## Confirm that conda is available at shell startup

The installed hook is guarded so it only runs when `conda` is available
on `PATH`. If completions work after activating an environment but not in
a fresh terminal, initialize conda for that shell first:

```bash
conda init
```

Restart the shell, then run:

```bash
conda completion install
```

Place any manual conda-completion hook after the block created by
{external+conda:doc}`conda init <commands/init>`.

## Regenerate stale command data

Run:

```bash
conda completion generate
```

This refreshes command, flag, plugin, and argparse metadata. It reuses
package metadata when the package cache is still fresh.

If `conda completion status` shows different `Plugin hash` and `Current
plugin hash` values, command data was generated with a different plugin
set. `generate` rewrites the manifest with the current plugin hash.

## Refresh stale package data

If command completions work but a package or version is missing, refresh
repodata:

```bash
conda completion refresh
```

If the cache was created with `--no-repodata`, package name and version
candidates are absent by design. Run `conda completion generate` without
`--no-repodata` to add them.

## Remove corrupt cache files

If status or completion reports that it cannot read completion data,
remove the generated files and regenerate them.

:::::{tab-set}

::::{tab-item} Linux

```bash
rm -f ~/.cache/conda/completion/completion.msgpack
rm -f ~/.cache/conda/completion/versions.index
rm -f ~/.cache/conda/completion/versions.store
conda completion generate
```

::::

::::{tab-item} macOS

```bash
rm -f ~/Library/Caches/conda/completion/completion.msgpack
rm -f ~/Library/Caches/conda/completion/versions.index
rm -f ~/Library/Caches/conda/completion/versions.store
conda completion generate
```

::::

::::{tab-item} Windows PowerShell

```powershell
Remove-Item "$env:LOCALAPPDATA\conda\cache\completion\completion.msgpack" -ErrorAction SilentlyContinue
Remove-Item "$env:LOCALAPPDATA\conda\cache\completion\versions.index" -ErrorAction SilentlyContinue
Remove-Item "$env:LOCALAPPDATA\conda\cache\completion\versions.store" -ErrorAction SilentlyContinue
conda completion generate
```

::::

:::::

The context cache file can also be removed safely. It is rebuilt on the
next TAB press:

```bash
rm -f ~/.cache/conda/completion/context_cache.msgpack
```

Use the cache directory printed by `conda completion status` when it
differs from these defaults.

## Fix a missing completer binary

If status says the completion engine binary is missing, install the
runtime package into the environment that provides `conda completion`:

```bash
conda install -c conda-forge conda-completer
```

Then regenerate:

```bash
conda completion generate
```

If you pasted the full output of `conda completion init` into a startup
file, it may contain an old binary path. Replace it with the shorter eval
hook from {doc}`nonstandard-shell-startup`, or regenerate the pasted
script from the environment you use now.

## Investigate slow TAB presses

Tab completion should normally complete quickly after the first run in a
directory. If it remains slow:

- Run `conda completion status` and confirm the manifest exists.
- Remove `context_cache.msgpack` so project file context is rebuilt.
- Check whether the current directory is on NFS, SSHFS, FUSE, or a slow
  cloud-synced filesystem.
- Try from a shallow directory. The completer walks upward looking for
  project files and stops at VCS roots.
- Use `conda completion generate --no-repodata` in constrained CI or
  container builds where package candidates are not needed.

## Collect useful issue details

When opening an issue, include:

- Output from `conda completion status`.
- Shell name and version.
- Operating system.
- The exact command line where TAB behaves incorrectly.
- Whether the manifest was generated with `--no-repodata`.
- Any project files involved, with private names redacted if needed.
