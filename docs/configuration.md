# Configuration

conda-completion works out of the box with sensible defaults. The settings
below are available for advanced use cases.

## Shell detection

By default, `conda completion install` (without a shell argument) detects
your shell from the `SHELL` environment variable. On Windows, it falls
back to PowerShell.

To override:

```bash
conda completion install zsh
```

## Manifest location

The completion manifest is stored in your platform's cache directory:

| Platform | Path |
|---|---|
| Linux | `~/.cache/conda/completion/completion.msgpack` |
| macOS | `~/Library/Caches/conda/completion/completion.msgpack` |
| Windows | `%LOCALAPPDATA%\conda\cache\completion\completion.msgpack` |

Package version data lives in `versions.index` and `versions.store` in
the same directory. These files are only loaded when `=` is detected in
the current word (e.g., `numpy=<TAB>`).

This follows the same pattern as conda's own cache directories, using
`platformdirs.user_cache_dir("conda")`.

## Context cache

The stat-based context cache lives alongside the manifest:

```
<cache_dir>/completion/context_cache.msgpack
```

This file maps source file paths to their parsed data (environment names,
task names, channels) along with the file's mtime and size at parse time.
On each TAB press, the completer stats each source file and only re-parses
files whose mtime or size has changed.

Deleting this file is safe. It will be rebuilt on the next TAB press at the
cost of re-parsing all project and global files on the next invocation.

## Manual regeneration

If you install a conda plugin via pip (instead of conda), the automatic
post-command hook will not trigger. Regenerate manually:

```bash
conda completion generate
```

By default, generation reuses package metadata if it is less than 24
hours old. Use `conda completion refresh` to force a fresh repodata
read, or `--no-repodata` to regenerate command and flag completions
without package metadata.

## Eval-based setup

Instead of using `conda completion install`, you can add the eval line
directly to your RC file:

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
